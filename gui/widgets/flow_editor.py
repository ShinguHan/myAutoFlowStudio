# gui/widgets/flow_editor.py

import json
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidgetItem, QAbstractItemView, QTreeWidgetItemIterator,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QPushButton, QDialogButtonBox, QLineEdit, QMenu, QLabel, QGroupBox, QAbstractItemView
)
from PyQt6.QtGui import QAction, QCursor
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from utils.logger_config import log
from .custom_tree_widget import CustomTreeWidget

class ConditionDialog(QDialog):
    """
    [✅ 대폭 수정]
    실시간으로 외부(UI 탐색기)의 선택을 반영하도록 수정합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("조건 설정")
        self.element_props = None # 처음에는 비어있음

        layout = QFormLayout(self)
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(["Element Exists (요소 존재)"])
        
        self.target_display = QLabel("조건으로 사용할 요소를 UI 탐색기에서 선택해주세요.")
        self.target_display.setStyleSheet("padding: 5px; background-color: #eee; border-radius: 3px;")
        
        layout.addRow("조건 타입:", self.condition_type_combo)
        layout.addRow("조건 대상:", self.target_display)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False) # 처음에는 비활성화

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def update_target_element(self, element_props):
        """
        [✅ 새로 추가된 슬롯]
        외부에서 호출하여 조건 대상 정보를 업데이트합니다.
        """
        self.element_props = element_props
        if self.element_props:
            title = self.element_props.get('title', 'N/A')
            ctype = self.element_props.get('control_type', 'N/A')
            self.target_display.setText(f"Type: {ctype}\nTitle: '{title}'")
            self.ok_button.setEnabled(True)
        else:
            self.target_display.setText("조건으로 사용할 요소를 UI 탐색기에서 선택해주세요.")
            self.ok_button.setEnabled(False)

    def get_condition(self):
        # ... (이전과 동일)
        if not self.element_props: return None
        return {
            "type": "element_exists",
            "target": {
                "title": self.element_props.get("title"),
                "control_type": self.element_props.get("control_type"),
                "auto_id": self.element_props.get("auto_id"),
                "class_name": self.element_props.get("class_name"),
            }
        }

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
        self.setAcceptDrops(True)
        
        self.flow_tree_widget = CustomTreeWidget()
        self.flow_tree_widget.setHeaderHidden(True)
        self.flow_tree_widget.setAcceptDrops(True)
        self.flow_tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.flow_tree_widget.setDragEnabled(True)
        self.flow_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.flow_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.flow_tree_widget.customContextMenuRequested.connect(self.open_context_menu)
        self.flow_tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.flow_tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        
        # ✅ 변경된 시그널에 맞춰 슬롯 연결 수정
        self.flow_tree_widget.element_dropped.connect(self.add_new_step_at_position)
        
        main_layout = QVBoxLayout(self)
        panel_groupbox = QGroupBox("시나리오 편집기")
        panel_layout = QVBoxLayout()
        panel_layout.addWidget(self.flow_tree_widget)
        panel_groupbox.setLayout(panel_layout)
        main_layout.addWidget(panel_groupbox)
        self.setLayout(main_layout)
        
        self.parent_stack = []

        self.condition_dialog = None # 다이얼로그 인스턴스를 저장할 변수
        self.current_context_data = None # 현재 UI 탐색기 선택 정보를 저장할 변수

    def update_context(self, element_data):
        """
        [✅ 새로 추가된 슬롯]
        MainWindow로부터 UI 탐색기의 현재 선택 정보를 받습니다.
        """
        self.current_context_data = element_data
        # 만약 ConditionDialog가 열려있다면, 정보를 실시간으로 업데이트합니다.
        if self.condition_dialog and self.condition_dialog.isVisible():
            props = self.current_context_data.get('properties') if self.current_context_data else None
            self.condition_dialog.update_target_element(props)


    def add_new_step_at_position(self, element_data, position):
        """
        [🔄 수정된 함수]
        IF와 ELSE 블록의 자식으로 정확히 추가되도록 규칙을 개선합니다.
        """
        # ... (함수 앞부분의 step_data 생성 및 변수 초기화는 이전과 동일) ...
        step_data = {
            "id": str(uuid.uuid4()),
            "type": "action",
            "action": "click",
            "path": element_data.get("path", []),
            "params": {},
            "onError": {"method": "stop"}
        }

        target_item = self.flow_tree_widget.itemAt(position)
        
        if not target_item:
            # 빈 공간에 드롭: 최상위 레벨의 맨 끝에 추가
            parent_item = self.flow_tree_widget.invisibleRootItem()
            insert_index = parent_item.childCount()
        else:
            parent_item = target_item.parent() or self.flow_tree_widget.invisibleRootItem()
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
            target_control_type = target_data.get("control_type") if target_data else ""

            # 규칙 1: 컨테이너 블록 위에 직접 드롭한 경우, 해당 컨테이너의 자식으로 추가
            if self.flow_tree_widget.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.OnItem and \
               target_control_type in ["start_loop", "if_condition", "else", "try_catch_start", "catch_separator", "group"]:
                
                # IF 블록에 드롭 시, ELSE 블록 앞에 삽입
                if target_control_type == "if_condition":
                    else_index = -1
                    for i in range(target_item.childCount()):
                        child_data = target_item.child(i).data(0, Qt.ItemDataRole.UserRole)
                        if child_data and child_data.get("control_type") == "else":
                            else_index = i
                            break
                    parent_item = target_item
                    insert_index = else_index if else_index != -1 else target_item.childCount()
                else:
                    parent_item = target_item
                    insert_index = target_item.childCount()
            else:
                # 규칙 2: 아이템 사이/위/아래에 드롭한 경우, 해당 아이템의 형제로 추가
                insert_index = parent_item.indexOfChild(target_item)
                if self.flow_tree_widget.dropIndicatorPosition() == QAbstractItemView.DropIndicatorPosition.BelowItem:
                    insert_index += 1

        new_item = QTreeWidgetItem()
        self.update_item_display(new_item, step_data)
        new_item.setData(0, Qt.ItemDataRole.UserRole, step_data)
        
        parent_item.insertChild(insert_index, new_item)


    def _wrap_selection_with_blocks(self, start_data, end_data, middle_data=None):
        """
        [✅ 수정] TRY-CATCH 계층 구조 오류를 해결합니다.
        """
        selected_items = self.flow_tree_widget.selectedItems()
        
        if selected_items:
            first_item = selected_items[0]
            parent_item = first_item.parent() or self.flow_tree_widget.invisibleRootItem()
            insert_row = parent_item.indexOfChild(first_item)
        else:
            parent_item = self.flow_tree_widget.invisibleRootItem()
            insert_row = parent_item.childCount()

        start_item = QTreeWidgetItem()
        self.update_item_display(start_item, start_data)
        start_item.setData(0, Qt.ItemDataRole.UserRole, start_data)
        parent_item.insertChild(insert_row, start_item)

        for item in selected_items:
            (item.parent() or self.flow_tree_widget.invisibleRootItem()).removeChild(item)
            start_item.addChild(item)

        if middle_data:
            middle_item = QTreeWidgetItem(start_item)
            self.update_item_display(middle_item, middle_data)
            middle_item.setData(0, Qt.ItemDataRole.UserRole, middle_data)

        end_item = QTreeWidgetItem()
        self.update_item_display(end_item, end_data)
        end_item.setData(0, Qt.ItemDataRole.UserRole, end_data)
        # [핵심 수정] 끝 블록의 부모는 시작 블록의 부모와 동일해야 합니다.
        parent_item.insertChild(insert_row + 1, end_item)

        self.flow_tree_widget.expandItem(start_item)

    def add_new_step_from_element(self, element_data):
        """
        [기존 함수 유지 - Alt+Right 단축키용]
        이 함수는 이제 단축키를 통해서만 호출되며, 항상 맨 끝에 추가합니다.
        """
        element_props = element_data.get("properties", {})
        element_path = element_data.get("path", [])
        log.info(f"Adding new step from element: {element_props.get('title')}")
        
        step_data = {
            "id": str(uuid.uuid4()),
            "type": "action",
            "action": "click",
            "path": element_path, # 경로 정보 저장
            "params": {},
            "onError": {"method": "stop"}
        }
        self._add_step_item(step_data)

    def _add_step_item(self, step_data):
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
        steps = []
        iterator = QTreeWidgetItemIterator(self.flow_tree_widget)
        while iterator.value():
            item = iterator.value()
            steps.append(item.data(0, Qt.ItemDataRole.UserRole))
            iterator += 1
        return steps

    def populate_from_data(self, scenario_data):
        self.flow_tree_widget.clear()
        self.parent_stack.clear()
        for step in scenario_data:
            self._add_step_item(step)
    
    def on_item_double_clicked(self, item, column):
        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not step_data: return

        step_type = step_data.get("type")
        control_type = step_data.get("control_type")
        action = step_data.get("action")

        # [✅ 수정] 제어 블록 더블 클릭 시 파라미터 편집 기능 추가
        if control_type == "if_condition":
            # 기존 조건을 다이얼로그에 전달하여 생성
            dialog = ConditionDialog(self) # 이 부분은 ConditionDialog가 수정을 지원하도록 개선 필요
            if dialog.exec():
                condition = dialog.get_condition()
                if condition:
                    step_data["condition"] = condition
        elif control_type == "start_loop":
            iterations, ok = QInputDialog.getInt(self, "반복 횟수 설정", "몇 번 반복할까요?",
                                                 step_data.get("iterations", 1), 1, 10000)
            if ok:
                step_data["iterations"] = iterations
        elif action == "set_text":
            dialog = SetTextDialog(step_data.get("params", {}).get("text", ""), self)
            if dialog.exec():
                step_data["params"]["text"] = dialog.get_text()
        else:
            return  # 편집할 내용이 없는 경우 조용히 종료

        item.setData(0, Qt.ItemDataRole.UserRole, step_data)
        self.update_item_display(item, step_data)

    def open_context_menu(self, position):
        item = self.flow_tree_widget.itemAt(position)
        if not item: return

        step_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not step_data: return

        menu = QMenu()
        
        if step_data.get("type") == "action":
            change_action_menu = menu.addMenu("동작 변경")
            to_click = QAction("Click", self); to_click.triggered.connect(lambda: self.change_action_type(item, "click"))
            to_set_text = QAction("Set Text", self); to_set_text.triggered.connect(lambda: self.change_action_type(item, "set_text"))
            to_get_text = QAction("Get Text (변수 저장)", self); to_get_text.triggered.connect(lambda: self.change_action_type(item, "get_text"))
            change_action_menu.addActions([to_click, to_set_text, to_get_text])
            menu.addSeparator()
            
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
        step_data["params"] = {} 
        if new_action == "set_text":
            self.on_item_double_clicked(item, 0)
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

    # ✅ 핵심 수정: 이 함수를 수정하여 'path'에서 정보를 가져오도록 합니다.
    def _get_display_text(self, step_data):
        """
        [✅ 전체 코드 공유]
        시나리오 스텝 데이터를 사람이 읽기 쉬운 텍스트로 변환합니다.
        IF 조건 표시가 대폭 개선되었습니다.
        """
        display_text = "Unknown Step"
        step_type = step_data.get("type")

        if step_type == "action":
            action = step_data.get('action', 'N/A').upper()
            path = step_data.get('path', [])
            target_props = path[-1] if path else {}
            target_title = target_props.get('title', 'Unknown')
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
            if control == "start_loop": 
                display_text = f"🔄 START LOOP ({step_data.get('iterations')} times)"
            elif control == "end_loop": 
                display_text = f"🔄 END LOOP"
            elif control == "if_condition":
                condition = step_data.get('condition', {})
                target = condition.get('target', {})
                ctype = target.get('control_type', '')
                title = target.get('title', 'N/A')
                display_text = f"❓ IF ({ctype}: '{title}') exists"
            elif control == "else": 
                display_text = f"- ELSE"
            elif control == "end_if": 
                display_text = f"❓ END IF"
            elif control == "try_catch_start": 
                display_text = "🛡️ TRY"
            elif control == "catch_separator": 
                display_text = "- CATCH"
            elif control == "try_catch_end": 
                display_text = "🛡️ END TRY"
            elif control == "group": 
                display_text = f"📦 GROUP: '{step_data.get('group_name', 'Unnamed')}'"
            elif control == "end_group": 
                display_text = f"📦 END GROUP"
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
        """
        [🔄 수정된 함수]
        새로운 범용 래핑 함수를 사용하도록 수정합니다.
        """
        selected_items = self.flow_tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "그룹화 오류", "그룹으로 묶을 항목을 1개 이상 선택해야 합니다.")
            return

        group_name, ok = QInputDialog.getText(self, "그룹 이름 설정", "그룹의 이름을 입력하세요:", text="MyGroup")
        if not ok or not group_name: return

        start_group_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "group", "group_name": group_name}
        end_group_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "end_group"}
        
        self._wrap_selection_with_blocks(start_group_data, end_group_data)
        
    def add_loop_block(self):
        """
        [🔄 수정된 함수]
        '선택 항목 감싸기' 로직을 적용합니다.
        """
        iterations, ok = QInputDialog.getInt(self, "반복 횟수 설정", "몇 번 반복할까요?", 3, 1, 10000)
        if ok:
            start_loop_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "start_loop", "iterations": iterations}
            end_loop_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "end_loop"}
            self._wrap_selection_with_blocks(start_loop_data, end_loop_data)
    
    def add_if_block(self, element_data=None):
        """
        [✅ 수정] ConditionDialog를 멤버 변수로 관리하여 실시간 업데이트가 가능하도록 합니다.
        """
        self.condition_dialog = ConditionDialog(self)
        
        # 현재 컨텍스트(UI 탐색기 선택 정보)가 있다면 즉시 다이얼로그에 반영
        if self.current_context_data:
            props = self.current_context_data.get('properties')
            self.condition_dialog.update_target_element(props)

        if self.condition_dialog.exec():
            condition = self.condition_dialog.get_condition()
            if not condition: return

            start_if_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "if_condition", "condition": condition}
            else_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "else"}
            end_if_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "end_if"}
            
            self._wrap_selection_with_blocks(start_if_data, end_if_data, middle_data=else_data)
        
        self.condition_dialog = None # 다이얼로그가 닫히면 참조를 제거

    def add_try_catch_block(self):
        """
        [✅ 수정] TRY-CATCH 생성 방식을 다른 제어 블록과 통일
        """
        start_try_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "try_catch_start"}
        catch_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "catch_separator"}
        end_try_data = {"id": str(uuid.uuid4()), "type": "control", "control_type": "try_catch_end"}

        self._wrap_selection_with_blocks(start_try_data, end_try_data, middle_data=catch_data)


    def add_wait_block(self):
        dialog = SetWaitDialog(self)
        if dialog.exec():
            condition, params = dialog.get_wait_params()
            if not condition: return
            self._add_step_item({"id": str(uuid.uuid4()), "type": "control", "control_type": "wait_for_condition", "condition": condition, "params": params})
