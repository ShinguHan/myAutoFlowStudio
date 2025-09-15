# -*- coding: utf-8 -*-
"""
이 모듈은 여러 개의 시나리오를 동시에 실행하고 관리할 수 있는
병렬 실행 패널(ParallelRunnerPanel) UI를 정의합니다.
이 패널은 여러 개의 '실행 슬롯(RunnerSlot)'으로 구성되며, 각 슬롯은
하나의 시나리오를 독립적으로 로드하고 실행하는 역할을 합니다.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QFrame, QHBoxLayout, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
import json
import os
from utils.logger_config import log

class RunnerSlot(QFrame):
    """하나의 시나리오 실행 단위를 나타내는 UI 위젯 (슬롯)."""
    # 자신의 '실행' 버튼이 눌렸을 때, 자신의 인덱스와 시나리오 데이터를 패널로 전달하는 시그널
    run_request = pyqtSignal(int, list)

    def __init__(self, index, parent=None):
        """RunnerSlot 인스턴스를 초기화합니다."""
        super().__init__(parent)
        self.index = index
        self.scenario_data = None
        self.data_path = None
        
        self.setFrameShape(QFrame.Shape.StyledPanel)

        # --- UI 요소 생성 ---
        self.title_label = QLabel(f"Slot #{self.index + 1}")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.status_label = QLabel("대기 중")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 5px; background-color: #eee; border-radius: 3px;")
        
        self.scenario_label = QLabel("시나리오: 없음")
        self.scenario_label.setWordWrap(True)
        
        self.data_label = QLabel("데이터: 없음")
        self.data_label.setWordWrap(True)
        
        self.load_scenario_btn = QPushButton("📂 시나리오 로드")
        self.load_data_btn = QPushButton("💾 데이터 로드")
        self.run_btn = QPushButton("▶️ 실행")
        self.run_btn.setEnabled(False) # 시나리오가 로드되어야 활성화됨

        # --- 시그널-슬롯 연결 ---
        self.load_scenario_btn.clicked.connect(self.load_scenario)
        self.load_data_btn.clicked.connect(self.load_data)
        self.run_btn.clicked.connect(self.emit_run_request)

        # --- 레이아웃 설정 ---
        layout = QVBoxLayout(self)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_scenario_btn)
        button_layout.addWidget(self.load_data_btn)
        
        layout.addLayout(title_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.scenario_label)
        layout.addWidget(self.data_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.run_btn)
        self.setLayout(layout)

    def load_scenario(self):
        """'시나리오 로드' 버튼 클릭 시 파일 대화상자를 열어 .json 파일을 로드합니다."""
        file_path, _ = QFileDialog.getOpenFileName(self, "시나리오 불러오기", "./scenarios", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.scenario_data = json.load(f)
                self.scenario_label.setText(f"시나리오: {os.path.basename(file_path)}")
                self.run_btn.setEnabled(True)
                log.info(f"[Slot-{self.index+1}] Scenario loaded: {file_path}")
            except Exception as e:
                log.error(f"[Slot-{self.index+1}] Failed to load scenario: {e}")
                self.scenario_label.setText("시나리오 로드 실패")
                self.scenario_data = None
                self.run_btn.setEnabled(False)

    def load_data(self):
        """'데이터 로드' 버튼 클릭 시 파일 대화상자를 열어 .csv 파일을 로드합니다."""
        file_path, _ = QFileDialog.getOpenFileName(self, "데이터 파일 불러오기", "./data", "CSV Files (*.csv)")
        if file_path:
            self.data_path = file_path
            self.data_label.setText(f"데이터: {os.path.basename(file_path)}")
            log.info(f"[Slot-{self.index+1}] Data file loaded: {file_path}")
        else:
            self.data_path = None
            self.data_label.setText("데이터: 없음")

    def emit_run_request(self):
        """'실행' 버튼 클릭 시 run_request 시그널을 발생시킵니다."""
        if self.scenario_data:
            self.run_request.emit(self.index, self.scenario_data)

    def update_status(self, message, color):
        """메인 윈도우로부터 실행 상태를 전달받아 UI를 업데이트합니다."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"padding: 5px; background-color: #eee; border-radius: 3px; color: {color}; font-weight: bold;")


class ParallelRunnerPanel(QWidget):
    """3개의 RunnerSlot을 포함하는 메인 패널 위젯."""
    # 슬롯으로부터 받은 실행 요청을 메인 윈도우로 전달하는 시그널
    run_request_from_slot = pyqtSignal(int, list, str)

    def __init__(self, parent=None):
        """ParallelRunnerPanel 인스턴스를 초기화합니다."""
        super().__init__(parent)
        
        self.slots = []
        
        panel_groupbox = QGroupBox("병렬 실행 패널")
        main_layout = QVBoxLayout(self)
        panel_layout = QVBoxLayout()
        
        # 3개의 실행 슬롯을 생성하고 레이아웃에 추가합니다.
        for i in range(3):
            slot = RunnerSlot(i)
            slot.run_request.connect(self.forward_run_request)
            panel_layout.addWidget(slot)
            self.slots.append(slot)
        
        panel_groupbox.setLayout(panel_layout)
        main_layout.addWidget(panel_groupbox)
        self.setLayout(main_layout)

    def forward_run_request(self, slot_index, scenario_data):
        """슬롯의 실행 요청을 받아, 데이터 파일 경로를 추가하여 메인 윈도우로 전달합니다."""
        data_path = self.slots[slot_index].data_path
        self.run_request_from_slot.emit(slot_index, scenario_data, data_path)

