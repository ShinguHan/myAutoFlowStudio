# -*- coding: utf-8 -*-
"""
이 모듈은 AutoFlow Studio의 핵심 UI 중 하나인 시나리오 편집기(FlowEditor)를 정의합니다.
사용자는 이 위젯을 통해 자동화 단계를 시각적으로 구성, 편집, 재정렬할 수 있습니다.
- CustomTreeWidget을 사용하여 중첩된 제어 흐름을 직관적으로 표시
- 드래그 앤 드롭, 더블 클릭, 컨텍스트 메뉴 등 다양한 사용자 상호작용 처리
- 시나리오 데이터를 내부 데이터 구조와 UI 표현 사이에서 변환
"""
import json
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidgetItem, QAbstractItemView, QTreeWidgetItemIterator,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QPushButton, QDialogButtonBox, QLineEdit, QMenu, QLabel, QGroupBox
)
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from utils.logger_config import log
from .custom_tree_widget import CustomTreeWidget

# --- 헬퍼 다이얼로그 클래스들 ---
# 각 액션/제어 블록의 상세 파라미터를 설정하기 위한 작은 팝업창들입니다.

class ConditionDialog(QDialog):
    """IF 문의 조건을 설정하는 다이얼로그"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("조건 설정")
        layout = QFormLayout(self)
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(["Element Exists (요소 존재)"])
        self.target_title_input = QLineEdit()
        self.target_title_input.setPlaceholderText("조건 대상의 창 제목...")
        layout.addRow("조건 타입:", self.condition_type_combo)
        layout.addRow("대상 요소 제목:", self.target_title_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def get_condition(self):
        if not self.target_title_input.text(): return None
        return {"type": "element_exists", "target": {"title": self.target_title_input.text()}}

class SetTextDialog(QDialog):
    """Set Text 액션의 파라미터를 설정하는 다이얼로그"""
    def __init__(self, current_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Text Parameters")
        layout = QVBoxLayout(self)
        self.text_input = QLineEdit(current_text)
        layout.addWidget(QLabel("입력할 텍스트 (변수 사용 가능: {{변수명}}):"))
        layout.addWidget(self.text_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_text(self):
        return self.text_input.text()

class SetOnErrorDialog(QDialog):
    """오류 처리 정책을 설정하는 다이얼로그"""
    def __init__(self, current_policy, parent=None):
        super().__init__(parent)
        self.setWindowTitle("오류 처리 설정")
        layout = QFormLayout(self)
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(["Stop (중단)", "Continue (계속)", "Retry (재시도)"])
        self.retry_count_input = QLineEdit(str(current_policy.get("retries", 3)))
        self.retry_count_input.setVisible(False)
        self.policy_combo.currentTextChanged.connect(lambda text: self.retry_count_input.setVisible(text == "Retry (재시도)"))
        if current_policy.get("method") == "continue": self.policy_combo.setCurrentIndex(1)
        elif current_policy.get("method") == "retry": self.policy_combo.setCurrentIndex(2)
        layout.addRow("정책:", self.policy_combo)
        layout.addRow("재시도 횟수:", self.retry_count_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def get_policy(self):
        policy = {}
        selected_policy = self.policy_combo.currentText()
        if "Continue" in selected_policy: policy["method"] = "continue"
        elif "Retry" in selected_policy:
            policy["method"] = "retry"
            policy["retries"] = int(self.retry_count_input.text())
        else: policy["method"] = "stop"
        return policy

class GetVariableNameDialog(QDialog):
    """Get Text 액션의 변수 이름을 설정하는 다이얼로그"""
    def __init__(self, current_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("저장할 변수 이름 설정")
        layout = QFormLayout(self)
        self.name_input = QLineEdit(current_name)
        layout.addRow("변수 이름:", self.name_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def get_name(self):
        return self.name_input.text()

class SetWaitDialog(QDialog):
    """WAIT 블록의 파라미터를 설정하는 다이얼로그"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("대기 조건 설정")
        layout = QFormLayout(self)
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(["Element Exists (요소 나타날 때까지)", "Element Vanishes (요소 사라질 때까지)"])
        self.target_title_input = QLineEdit()
        self.target_title_input.setPlaceholderText("대상 요소의 창 제목...")
        self.timeout_input = QLineEdit("10")
        layout.addRow("대기 조건:", self.condition_type_combo)
        layout.addRow("대상 요소 제목:", self.target_title_input)
        layout.addRow("최대 대기 시간(초):", self.timeout_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    def get_wait_params(self):
        if not self.target_title_input.text(): return None
        cond_type_map = {"Element Exists (요소 나타날 때까지)": "element_exists", "Element Vanishes (요소 사라질 때까지)": "element_vanishes"}
        condition = {"type": cond_type_map[self.condition_type_combo.currentText()], "target": {"title": self.target_title_input.text()}}
        params = {"timeout": int(self.timeout_input.text())}
        return condition, params

class FlowEditor(QWidget):
    """자동화 흐름을 시각적으로 편집하는 메인 위젯."""
    selectionChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.flow_tree_widget = CustomTreeWidget()
        self.flow_tree_widget.setHeaderHidden(True)
        self.flow_tree_widget.setAcceptDrops(True)
        
        # *** ✨ 여기가 수정된 부분입니다 ✨ ***
        # 외부 드롭(UI 요소 추가)과 내부 이동(순서 변경)을 모두 허용하도록 모드를 변경합니다.
        self.flow_tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        
        self.flow_tree_widget.setDragEnabled(True)
        self.flow_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.flow_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # --- 시그널과 슬롯 연결 ---
        self.flow_tree_widget.customContextMenuRequested.connect(self.open_context_menu)
        self.flow_tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.flow_tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        
        # CustomTreeWidget에서 보낸 element_dropped 신호를 _add_new_step_from_element 메서드와 연결
        self.flow_tree_widget.element_dropped.connect(self._add_new_step_from_element)
        
        main_layout = QVBoxLayout(self)
        panel_groupbox = QGroupBox("시나리오 편집기")
        panel_layout = QVBoxLayout()
        panel_layout.addWidget(self.flow_tree_widget)
        panel_groupbox.setLayout(panel_layout)
        main_layout.addWidget(panel_groupbox)
        self.setLayout(main_layout)
        
        self.parent_stack = []

    def _add_new_step_from_element(self, element_props):
        """UI 탐색기에서 드롭된 요소를 기반으로 새로운 'action' 단계를 추가합니다."""
        log.info(f"Adding new step from element: {element_props.get('title')}")
        step_data = {
            "id": str(uuid.uuid4()), "type": "action", "action": "click",
            "target": {"title": element_props.get("title"), "control_type": element_props.get("control_type"), "auto_id": element_props.get("auto_id")},
            "params": {}, "onError": {"method": "stop"}
        }
        self._add_step_item(step_data)

    def _add_step_item(self, step_data):
        """주어진 데이터로 트리 위젯에 새 아이템을 추가하고, 중첩 구조를 관리합니다."""
        parent = self.parent_stack[-1] if self.parent_stack else self.flow_tree_widget.invisibleRootItem()
        item = QTreeWidgetItem(parent)
        self.update_item_display(item, step_data)
        item.setData(0, Qt.ItemDataRole.UserRole, step_data)

        control_type = step_data.get("control_type")
        if control_type in ["start_loop", "if_condition", "group", "try_catch_start"]:
            self.parent_stack.append(item)
            self.flow_tree_widget.expandItem(item)
        elif control_type in ["end_loop", "end_if", "end_group", "try_catch_end", "else", "catch_separator"]:
            if self.parent_stack:
                if control_type not in ["else", "catch_separator"]:
                    self.parent_stack.pop()

    def get_scenario_data(self):
        """트리 구조를 순회하여 순차적인 리스트 데이터로 변환합니다."""
        steps = []
        iterator = QTreeWidgetItemIterator(self.flow_tree_widget)
        while iterator.value():
            item = iterator.value()
            steps.append(item.data(0, Qt.ItemDataRole.UserRole))
            iterator += 1
        return steps

    def populate_from_data(self, scenario_data):
        """저장된 데이터로 트리 위젯의 내용을 다시 구성합니다."""
        self.flow_tree_widget.clear()
        self.parent_stack.clear()
        for step in scenario_data:
            self._add_step_item(step)
    
    def on_item_double_clicked(self, item, column):
        """아이템 더블 클릭 시 파라미터 편집 다이얼로그를 엽니다."""
        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not step_data: return

        action = step_data.get("action")
        control_type = step_data.get("control_type")

        if action == "set_text":
            dialog = SetTextDialog(step_data.get("params", {}).get("text", ""), self)
            if dialog.exec():
                step_data["params"]["text"] = dialog.get_text()
        elif control_type == "start_loop":
            iterations, ok = QInputDialog.getInt(self, "반복 횟수 설정", "몇 번 반복할까요?", step_data.get("iterations", 1), 1, 10000)
            if ok: step_data["iterations"] = iterations
        else:
            return # 편집할 파라미터가 없는 경우 종료
        
        item.setData(0, Qt.ItemDataRole.UserRole, step_data)
        self.update_item_display(item, step_data)

    def open_context_menu(self, position):
        """아이템 우클릭 시 컨텍스트 메뉴를 엽니다."""
        item = self.flow_tree_widget.itemAt(position)
        if not item: return

        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not step_data: return

        menu = QMenu()
        
        if step_data.get("type") == "action":
            # 액션 타입 변경 메뉴
            change_action_menu = menu.addMenu("동작 변경")
            to_click = QAction("Click", self); to_click.triggered.connect(lambda: self.change_action_type(item, "click"))
            to_set_text = QAction("Set Text", self); to_set_text.triggered.connect(lambda: self.change_action_type(item, "set_text"))
            to_get_text = QAction("Get Text (변수 저장)", self); to_get_text.triggered.connect(lambda: self.change_action_type(item, "get_text"))
            change_action_menu.addActions([to_click, to_set_text, to_get_text])
            menu.addSeparator()
            
            # 오류 처리 설정
            set_on_error = QAction("오류 처리 설정...", self)
            set_on_error.triggered.connect(lambda: self.set_on_error_policy(item))
            menu.addAction(set_on_error)

        delete_action = QAction("삭제", self)
        delete_action.triggered.connect(lambda: self.delete_item(item))
        menu.addAction(delete_action)
        
        menu.exec(self.flow_tree_widget.mapToGlobal(position))

    def change_action_type(self, item, new_action):
        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        step_data["action"] = new_action
        # 액션 타입 변경 시 파라미터 초기화
        step_data["params"] = {} 
        if new_action == "set_text":
            self.on_item_double_clicked(item, 0) # 바로 텍스트 편집창 열기
        elif new_action == "get_text":
            dialog = GetVariableNameDialog("", self)
            if dialog.exec():
                step_data["params"]["variable_name"] = dialog.get_name()
        
        item.setData(0, Qt.ItemDataRole.UserRole, step_data)
        self.update_item_display(item, step_data)
    
    def set_on_error_policy(self, item):
        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        dialog = SetOnErrorDialog(step_data.get("onError", {}), self)
        if dialog.exec():
            step_data["onError"] = dialog.get_policy()
            item.setData(0, Qt.ItemDataRole.UserRole, step_data)
            self.update_item_display(item, step_data)

    def delete_item(self, item):
        (item.parent() or self.flow_tree_widget.invisibleRootItem()).removeChild(item)
        self.on_selection_changed()

    def update_item_display(self, item, step_data):
        display_text = self._get_display_text(step_data)
        item.setText(0, display_text)

    def _get_display_text(self, step_data):
        """시나리오 데이터로부터 사람이 읽기 쉬운 설명을 생성합니다."""
        display_text = "Unknown Step"
        step_type = step_data.get("type")

        if step_type == "action":
            action = step_data.get('action', 'N/A').upper()
            target_title = step_data.get('target', {}).get('title', 'Unknown')
            params = step_data.get('params', {})
            on_error = step_data.get("onError", {})
            
            if action == "SET_TEXT":
                display_text = f"▶️ SET TEXT on '{target_title}' with: \"{params.get('text', '')}\""
            elif action == "GET_TEXT":
                var_name = params.get('variable_name', 'N/A')
                display_text = f"📋 GET TEXT from '{target_title}' and store in [{var_name}]"
            else:
                display_text = f"▶️ {action}: '{target_title}'"

            if on_error.get("method") == "retry": display_text += f" (Retry: {on_error.get('retries', 3)})"
            elif on_error.get("method") == "continue": display_text += " (Continue on Error)"

        elif step_type == "control":
            control = step_data.get("control_type")
            if control == "start_loop": display_text = f"🔄 START LOOP ({step_data.get('iterations')} times)"
            elif control == "end_loop": display_text = f"🔄 END LOOP"
            elif control == "if_condition": display_text = f"❓ IF '{step_data.get('condition', {}).get('target', {}).get('title', 'N/A')}' exists"
            elif control == "else": display_text = f"  - ELSE"
            elif control == "end_if": display_text = f"❓ END IF"
            elif control == "try_catch_start": display_text = "🛡️ TRY"
            elif control == "catch_separator": display_text = "  - CATCH"
            elif control == "try_catch_end": display_text = "🛡️ END TRY"
            elif control == "group": display_text = f"📦 GROUP: '{step_data.get('group_name', 'Unnamed')}'"
            elif control == "end_group": display_text = f"📦 END GROUP"
            elif control == "wait_for_condition":
                 cond = step_data.get("condition", {})
                 target = cond.get("target", {}).get("title", "N/A")
                 wait_type = "appears" if cond.get("type") == "element_exists" else "vanishes"
                 timeout = step_data.get("params", {}).get("timeout", 10)
                 display_text = f"⏱️ WAIT for '{target}' to {wait_type} (Timeout: {timeout}s)"
        return display_text

    def on_selection_changed(self):
        count = len(self.flow_tree_widget.selectedItems())
        self.selectionChanged.emit(count)
        
    def group_selection(self):
        selected_items = self.flow_tree_widget.selectedItems()
        if len(selected_items) < 1:
            QMessageBox.warning(self, "그룹화 오류", "그룹으로 묶을 항목을 1개 이상 선택해야 합니다.")
            return

        group_name, ok = QInputDialog.getText(self, "그룹 이름 설정", "그룹의 이름을 입력하세요:", text="MyGroup")
        if not ok or not group_name: return

        first_item = selected_items[0]
        parent = first_item.parent() or self.flow_tree_widget.invisibleRootItem()
        insert_row = parent.indexOfChild(first_item)

        start_group_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "group", "group_name": group_name}
        end_group_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "end_group"}
        
        group_item = QTreeWidgetItem()
        self.update_item_display(group_item, start_group_data)
        group_item.setData(0, Qt.ItemDataRole.UserRole, start_group_data)
        
        for item in selected_items:
            parent.removeChild(item)
            group_item.addChild(item)
            
        parent.insertChild(insert_row, group_item)
        self.flow_tree_widget.expandItem(group_item)
        
    def add_loop_block(self):
        iterations, ok = QInputDialog.getInt(self, "반복 횟수 설정", "몇 번 반복할까요?", 3, 1, 10000)
        if ok:
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "start_loop", "iterations": iterations})
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "end_loop"})
    
    def add_if_block(self):
        dialog = ConditionDialog(self)
        if dialog.exec():
            condition = dialog.get_condition()
            if not condition: return
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "if_condition", "condition": condition})
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "else"})
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "end_if"})

    def add_try_catch_block(self):
        self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "try_catch_start"})
        self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "catch_separator"})
        self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "try_catch_end"})

    def add_wait_block(self):
        dialog = SetWaitDialog(self)
        if dialog.exec():
            condition, params = dialog.get_wait_params()
            if not condition: return
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "wait_for_condition", "condition": condition, "params": params})