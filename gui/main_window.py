# -*- coding: utf-8 -*-
"""
이 모듈은 AutoFlow Studio의 메인 윈도우(MainWindow)를 정의합니다.
애플리케이션의 전체적인 레이아웃을 구성하고, 모든 UI 위젯들을 조립하며,
사용자 액션(툴바 버튼 클릭 등)에 대한 응답을 처리하고,
핵심 로직(core)과 GUI를 연결하는 관제탑(Control Tower) 역할을 합니다.
"""
import sys
import json
import webbrowser
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSplitter, QFileDialog, QToolBar,
    QMessageBox, QTextEdit, QGroupBox
)
from PyQt6.QtGui import QAction, QTextCursor, QShortcut, QKeySequence
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from core.app_connector import AppConnector
from core.scenario_runner import ScenarioRunner
from core.log_monitor import LogMonitor
from gui.widgets.ui_tree import UITreeView
from gui.widgets.flow_editor import FlowEditor
from gui.widgets.parallel_runner import ParallelRunnerPanel
from utils.logger_config import log, qt_log_handler
from utils.error_handler import translate_exception

# --- 백그라운드 작업을 위한 Worker 스레드 클래스들 ---
# GUI의 응답성을 유지하기 위해 시간이 오래 걸리는 작업(UI 분석, 시나리오 실행)은
# 별도의 스레드에서 처리합니다.

class ConnectorWorker(QThread):
    """UI 분석을 백그라운드에서 실행하여 GUI 멈춤을 방지하는 스레드."""
    # 작업 완료 시 분석 결과를 담아 보낼 시그널
    finished = pyqtSignal(object)

    def __init__(self, title_re):
        super().__init__()
        self.title_re = title_re
        self.connector = AppConnector()

    def run(self):
        """스레드의 메인 실행 로직."""
        if self.connector.connect_to_app(title_re=self.title_re):
            ui_tree = self.connector.get_ui_tree()
            self.finished.emit(ui_tree) # 성공 시 UI 트리 데이터 전달
        else:
            self.finished.emit(None) # 실패 시 None 전달

class ScenarioWorker(QThread):
    """시나리오 실행을 백그라운드에서 처리하는 스레드."""
    # 작업 완료 시 (슬롯 인덱스, 결과 메시지, 보고서 경로)를 담아 보낼 시그널
    finished = pyqtSignal(int, str, str)

    def __init__(self, slot_index, title_re, scenario_data, data_path=None):
        super().__init__()
        self.slot_index = slot_index
        self.title_re = title_re
        self.scenario_data = scenario_data
        self.data_path = data_path

    def run(self):
        """스레드의 메인 실행 로직."""
        report_path = None
        runner = None
        try:
            log.info(f"[Slot-{self.slot_index+1}] Connecting to app '{self.title_re}'...")
            connector = AppConnector()
            if not connector.connect_to_app(title_re=self.title_re):
                raise ConnectionError(f"Failed to connect to app: {self.title_re}")
            
            runner = ScenarioRunner(connector)
            runner.run_scenario(self.scenario_data, data_file_path=self.data_path)
            report_path = runner.generate_html_report()
            self.finished.emit(self.slot_index, "성공", report_path)
        except Exception as e:
            # 예외 발생 시, 사용자 친화적인 메시지로 변환하여 전달
            friendly_message = translate_exception(e)
            log.error(f"[Slot-{self.slot_index+1}] Scenario failed with friendly message: {friendly_message}", exc_info=True)
            if runner: # 실행기 객체가 생성되었다면, 실패했더라도 리포트 생성 시도
                report_path = runner.generate_html_report()
            self.finished.emit(self.slot_index, f"실패: {friendly_message}", report_path)

class MainWindow(QMainWindow):
    """애플리케이션의 메인 윈도우 클래스."""
    def __init__(self):
        """MainWindow 인턴스를 초기화합니다."""
        super().__init__()
        self.setWindowTitle("AutoFlow Studio")
        self.setGeometry(100, 100, 1800, 1000)
        
        # Worker 스레드 인스턴스를 저장할 변수
        self.connector_worker = None
        self.running_workers = {} # {slot_index: worker} 형태로 실행 중인 시나리오 워커 관리
        self.log_monitor_worker = None

        # UI 생성, 액션 생성, 시그널 연결 순으로 초기화 진행
        self._create_actions()
        self._create_toolbars()
        self._setup_ui()
        self._connect_signals()
        self._create_shortcuts() # 🔻 단축키 설정 함수 호출 추가    

    def _setup_ui(self):
        """모든 UI 위젯을 생성하고 레이아웃을 설정합니다."""
        # --- 위젯 생성 ---
        self.ui_tree_view = UITreeView()
        self.flow_editor = FlowEditor()
        self.parallel_runner_panel = ParallelRunnerPanel()
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_monitor_panel = self._create_log_monitor_panel()
        
        # --- 레이아웃 설정 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # QSplitter를 사용하여 사용자가 패널 크기를 조절할 수 있게 함
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.ui_tree_view)
        main_splitter.addWidget(self.flow_editor)
        main_splitter.addWidget(self.parallel_runner_panel)
        main_splitter.setSizes([350, 800, 450]) # 초기 패널 크기 설정

        bottom_panel = QSplitter(Qt.Orientation.Horizontal)
        bottom_panel.addWidget(self.log_viewer)
        bottom_panel.addWidget(self.log_monitor_panel)
        bottom_panel.setSizes([1200, 600])

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(main_splitter)
        vertical_splitter.addWidget(bottom_panel)
        vertical_splitter.setSizes([750, 250])

        main_layout.addWidget(vertical_splitter)

    def _create_actions(self):
        """툴바에 들어갈 모든 액션(QAction)을 생성합니다."""
        self.connect_action = QAction("앱 연결", self)
        self.run_scenario_action = QAction("▶️ (메인) 시나리오 실행", self)
        self.add_loop_action = QAction("🔄 반복 블록 추가", self)
        self.add_if_action = QAction("❓ IF 블록 추가", self)
        self.add_try_catch_action = QAction("🛡️ TRY-CATCH 블록 추가", self)
        self.add_wait_action = QAction("⏱️ 대기 추가", self)
        self.group_selection_action = QAction("📦 그룹으로 묶기", self)
        self.group_selection_action.setEnabled(False) # 기본적으로 비활성화
        self.load_scenario_action = QAction("📂 불러오기", self)
        self.save_scenario_action = QAction("💾 저장하기", self)

    def _create_toolbars(self):
        """메인 툴바를 생성하고 액션과 위젯을 추가합니다."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        self.target_app_input = QLineEdit()
        self.target_app_input.setPlaceholderText("연결할 앱 창 제목 (정규식 가능)")
        toolbar.addWidget(QLabel("대상 앱: "))
        toolbar.addWidget(self.target_app_input)
        toolbar.addAction(self.connect_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_scenario_action)
        toolbar.addSeparator()
        toolbar.addAction(self.add_loop_action)
        toolbar.addAction(self.add_if_action)
        toolbar.addAction(self.add_try_catch_action)
        toolbar.addAction(self.add_wait_action)
        toolbar.addAction(self.group_selection_action)
        toolbar.addSeparator()
        toolbar.addAction(self.load_scenario_action)
        toolbar.addAction(self.save_scenario_action)

    def _create_log_monitor_panel(self):
        """로그 모니터 및 트리거 기능의 UI 패널을 생성합니다."""
        panel = QGroupBox("로그 모니터 및 트리거")
        layout = QVBoxLayout()
        self.log_file_input = QLineEdit(); self.log_file_input.setPlaceholderText("감시할 로그 파일 경로...")
        self.log_pattern_input = QLineEdit(); self.log_pattern_input.setPlaceholderText("감지할 정규식 패턴...")
        self.trigger_slot_input = QLineEdit("1"); self.trigger_slot_input.setFixedWidth(50)
        self.monitor_toggle_btn = QPushButton("모니터링 시작"); self.monitor_toggle_btn.setCheckable(True)
        
        layout.addWidget(QLabel("대상 로그 파일:"))
        layout.addWidget(self.log_file_input)
        layout.addWidget(QLabel("감지 패턴 (Regex):"))
        layout.addWidget(self.log_pattern_input)
        trigger_layout = QHBoxLayout(); trigger_layout.addWidget(QLabel("패턴 감지 시 실행할 슬롯:")); trigger_layout.addWidget(self.trigger_slot_input); trigger_layout.addStretch(1)
        layout.addLayout(trigger_layout)
        layout.addWidget(self.monitor_toggle_btn)
        panel.setLayout(layout)
        return panel

    def _connect_signals(self):
        """모든 위젯의 시그널과 메인 윈도우의 슬롯을 연결합니다."""
        # 툴바 액션 연결
        self.connect_action.triggered.connect(self.start_ui_analysis)
        self.run_scenario_action.triggered.connect(self.run_main_scenario)
        self.add_loop_action.triggered.connect(self.flow_editor.add_loop_block)
        self.add_if_action.triggered.connect(self.flow_editor.add_if_block)
        self.add_try_catch_action.triggered.connect(self.flow_editor.add_try_catch_block)
        self.add_wait_action.triggered.connect(self.flow_editor.add_wait_block)
        self.group_selection_action.triggered.connect(self.flow_editor.group_selection)
        self.save_scenario_action.triggered.connect(self.save_scenario)
        self.load_scenario_action.triggered.connect(self.load_scenario)
        
        # 커스텀 위젯 시그널 연결
        qt_log_handler.log_message.connect(self.update_log_viewer)
        self.parallel_runner_panel.run_request_from_slot.connect(self.run_parallel_scenario)
        self.flow_editor.selectionChanged.connect(self.update_group_action_state)
        self.monitor_toggle_btn.clicked.connect(self.toggle_log_monitor)

    # --- 이하 사용자 액션에 대한 응답을 처리하는 슬롯 메서드들 ---

    # 🔻 아래 두 개의 메서드를 MainWindow 클래스 내에 새로 추가합니다.
    def _create_shortcuts(self):
        """애플리케이션의 단축키를 설정합니다."""
        # Alt+Right 단축키가 self.ui_tree_view 위젯에 포커스가 있을 때만 동작하도록 설정
        transfer_shortcut = QShortcut(QKeySequence("Alt+Right"), self.ui_tree_view)
        transfer_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        transfer_shortcut.activated.connect(self.transfer_selected_ui_element)

    def transfer_selected_ui_element(self):
        """UITreeView에서 선택된 요소를 FlowEditor로 전달하는 슬롯 메서드."""
        log.debug("Alt+Right shortcut activated.")
        # 1. UITreeView에서 선택된 요소의 정보를 가져옵니다.
        element_props = self.ui_tree_view.get_selected_element_properties()
        
        # 2. 정보가 있다면 FlowEditor에 추가합니다.
        if element_props:
            log.info(f"Transferring element via shortcut: {element_props.get('title')}")
            self.flow_editor.add_step_from_element(element_props)
        else:
            log.debug("No element selected in UI Tree to transfer.")
    
    def start_ui_analysis(self):
        """'앱 연결' 버튼 클릭 시 UI 분석 스레드를 시작합니다."""
        target_title = self.target_app_input.text()
        if not target_title:
            QMessageBox.warning(self, "입력 오류", "대상 앱의 창 제목을 입력해주세요.")
            return
        
        self.connect_action.setEnabled(False)
        self.connector_worker = ConnectorWorker(title_re=target_title)
        self.connector_worker.finished.connect(self.on_analysis_finished)
        self.connector_worker.start()

    def on_analysis_finished(self, ui_tree):
        """UI 분석 스레드 완료 시 호출됩니다."""
        if ui_tree:
            self.ui_tree_view.populate_tree(ui_tree)
            QMessageBox.information(self, "성공", "애플리케이션에 성공적으로 연결하고 UI를 분석했습니다.")
        else:
            QMessageBox.critical(self, "연결 실패", "앱을 찾을 수 없거나 연결에 실패했습니다.")
        self.connect_action.setEnabled(True)
        
    def run_main_scenario(self):
        """메인 툴바의 실행 버튼 클릭 시, 슬롯 #1에서 현재 편집 중인 시나리오를 실행합니다."""
        main_scenario_data = self.flow_editor.get_scenario_data()
        if not main_scenario_data:
            QMessageBox.warning(self, "실행 오류", "실행할 시나리오가 비어있습니다.")
            return
        # 데이터 파일은 메인 편집기에서 설정할 수 없으므로 None으로 전달
        self.run_parallel_scenario(0, main_scenario_data, None)

    def run_parallel_scenario(self, slot_index, scenario_data, data_path):
        """병렬 실행 패널의 슬롯에서 실행 요청이 오면 시나리오 실행 스레드를 시작합니다."""
        target_title = self.target_app_input.text()
        if not target_title:
            QMessageBox.warning(self, "연결 오류", "병렬 실행을 위해 메인 툴바의 '대상 앱'을 먼저 지정해야 합니다.")
            return

        if slot_index in self.running_workers:
            QMessageBox.warning(self, "실행 중", f"슬롯 #{slot_index+1}은 이미 실행 중입니다.")
            return

        slot_widget = self.parallel_runner_panel.slots[slot_index]
        slot_widget.update_status("실행 중...", "blue")
        
        worker = ScenarioWorker(slot_index, target_title, scenario_data, data_path)
        worker.finished.connect(self.on_parallel_scenario_finished)
        self.running_workers[slot_index] = worker
        worker.start()

    def on_parallel_scenario_finished(self, slot_index, message, report_path):
        """시나리오 실행 스레드 완료 시 호출됩니다."""
        slot_widget = self.parallel_runner_panel.slots[slot_index]
        color = "green" if "성공" in message else "red"
        slot_widget.update_status(message, color)
        
        if slot_index in self.running_workers:
            del self.running_workers[slot_index]

        if report_path:
            reply = QMessageBox.question(self, '리포트 확인', 
                                         f"슬롯 #{slot_index+1}의 실행이 완료되었습니다.\n결과 리포트를 여시겠습니까?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                # 웹 브라우저에서 로컬 파일을 열기 위한 URL 형식
                webbrowser.open(f'file:///{report_path}')

    def save_scenario(self):
        """현재 시나리오 편집기의 내용을 .json 파일로 저장합니다."""
        scenario_data = self.flow_editor.get_scenario_data()
        if not scenario_data:
            QMessageBox.warning(self, "저장 오류", "저장할 시나리오 내용이 없습니다.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "시나리오 저장", "./scenarios", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(scenario_data, f, ensure_ascii=False, indent=4)
                log.info(f"Scenario saved to {file_path}")
                QMessageBox.information(self, "성공", f"시나리오를 성공적으로 저장했습니다:\n{file_path}")
            except Exception as e:
                log.error(f"Failed to save scenario: {e}")
                QMessageBox.critical(self, "저장 실패", f"파일 저장 중 오류가 발생했습니다:\n{e}")

    def load_scenario(self):
        """`.json` 파일에서 시나리오를 불러와 편집기에 표시합니다."""
        file_path, _ = QFileDialog.getOpenFileName(self, "시나리오 불러오기", "./scenarios", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    scenario_data = json.load(f)
                self.flow_editor.populate_from_data(scenario_data)
                log.info(f"Scenario loaded from {file_path}")
            except Exception as e:
                log.error(f"Failed to load scenario: {e}")
                QMessageBox.critical(self, "불러오기 실패", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")
        
    def update_log_viewer(self, message):
        """로그 핸들러로부터 메시지를 받아 로그 뷰어에 추가합니다."""
        self.log_viewer.append(message)
        self.log_viewer.moveCursor(QTextCursor.MoveOperation.End)
        
    def update_group_action_state(self, selected_count):
        """선택된 항목 수에 따라 '그룹으로 묶기' 버튼의 활성화 여부를 결정합니다."""
        self.group_selection_action.setEnabled(selected_count > 0) # 1개 이상 선택 시 활성화

    def toggle_log_monitor(self, checked):
        """'모니터링 시작/중지' 버튼 클릭 시 로그 모니터 스레드를 제어합니다."""
        if checked:
            file_path = self.log_file_input.text()
            pattern = self.log_pattern_input.text()
            if not file_path or not pattern:
                QMessageBox.warning(self, "입력 오류", "로그 파일 경로와 감지 패턴을 모두 입력해주세요.")
                self.monitor_toggle_btn.setChecked(False)
                return

            if not os.path.exists(file_path):
                QMessageBox.warning(self, "경로 오류", f"파일을 찾을 수 없습니다:\n{file_path}")
                self.monitor_toggle_btn.setChecked(False)
                return
            if not os.path.isfile(file_path):
                QMessageBox.warning(self, "경로 오류", f"지정한 경로는 파일이 아닌 폴더입니다:\n{file_path}")
                self.monitor_toggle_btn.setChecked(False)
                return
            
            self.monitor_toggle_btn.setText("모니터링 중지")
            self.log_monitor_worker = LogMonitor(file_path, pattern)
            self.log_monitor_worker.pattern_found.connect(self.on_pattern_found)
            self.log_monitor_worker.finished.connect(lambda: self.monitor_toggle_btn.setText("모니터링 시작"))
            self.log_monitor_worker.start()
        else:
            if self.log_monitor_worker:
                self.log_monitor_worker.stop()
                self.monitor_toggle_btn.setText("모니터링 시작")

    def on_pattern_found(self, log_line):
        """로그 모니터가 패턴을 감지했을 때 호출됩니다."""
        try:
            slot_index_to_run = int(self.trigger_slot_input.text()) - 1
            if not (0 <= slot_index_to_run < 3): raise ValueError("Slot index out of range.")
            
            slot_widget = self.parallel_runner_panel.slots[slot_index_to_run]
            if slot_widget.scenario_data:
                log.info(f"Trigger activated! Running scenario in slot #{slot_index_to_run + 1}.")
                self.run_parallel_scenario(slot_index_to_run, slot_widget.scenario_data, slot_widget.data_path)
            else:
                log.warning(f"Trigger activated, but no scenario loaded in slot #{slot_index_to_run + 1}.")
        except ValueError as e:
            log.error(f"Invalid trigger slot number: {e}")