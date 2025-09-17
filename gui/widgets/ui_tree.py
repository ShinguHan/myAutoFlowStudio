# gui/widgets/ui_tree.py 최종 수정안

# -*- coding: utf-8 -*-
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QDrag
from utils.logger_config import log

class ExplorableTreeWidget(QTreeWidget):
    """컨텍스트 메뉴를 통해 하위 요소 새로고침을 요청하는 커스텀 트리 위젯."""
    # 사용자가 '새로고침'을 요청한 QTreeWidgetItem을 전달하는 시그널
    refresh_request = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

    def open_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()
        refresh_action = menu.addAction("하위 요소 새로고침 (Refresh Children)")
        action = menu.exec(self.mapToGlobal(position))

        if action == refresh_action:
            self.refresh_request.emit(item)


class UITreeView(QWidget):
    # ✅ refresh_request 시그널을 MainWindow로 전달하기 위해 클래스에 정의
    refresh_request = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ✅ ExplorableTreeWidget 사용
        self.tree_widget = ExplorableTreeWidget()
        self.tree_widget.refresh_request.connect(self.refresh_request.emit) # 시그널 전달

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)

    # 🔻 아이템의 자식만 업데이트하는 새로운 메서드 추가
    def update_item_children(self, parent_item, children_data):
        """지정된 아이템의 자식 노드를 지우고 새 데이터로 교체합니다."""
        parent_item.takeChildren() # 기존 자식 모두 삭제
        for child_node in children_data.get("children", []):
            self._add_items_recursive(parent_item, child_node)
        parent_item.setExpanded(True) # 업데이트 후 자동으로 펼치기

    def get_selected_element_properties(self):
        """현재 선택된 아이템의 속성(dict)을 반환합니다. 선택된 아이템이 없으면 None을 반환합니다."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return None
        
        item = selected_items[0]
        return item.data(0, Qt.ItemDataRole.UserRole)
    
    def populate_tree(self, tree_data):
        """
        AppConnector로부터 받은 UI 트리 데이터로 위젯의 내용을 채웁니다.
        """
        self.tree_widget.clear()
        if tree_data:
            self._add_items_recursive(self.tree_widget.invisibleRootItem(), tree_data)

    def _add_items_recursive(self, parent_item, node_data):
        """
        재귀적으로 딕셔너리 트리를 순회하며 QTreeWidgetItem을 생성하고 추가합니다.
        """
        props = node_data["properties"]
        display_text = f"{props.get('control_type', 'Unknown')}: '{props.get('title', '')}'"
        
        item = QTreeWidgetItem(parent_item, [display_text])
        item.setData(0, Qt.ItemDataRole.UserRole, props)
        
        for child_node in node_data["children"]:
            self._add_items_recursive(item, child_node)
