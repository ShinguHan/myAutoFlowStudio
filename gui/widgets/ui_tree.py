# gui/widgets/ui_tree.py

import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from utils.logger_config import log

class ExplorableTreeWidget(QTreeWidget):
    refresh_request = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

    def open_context_menu(self, position):
        item = self.itemAt(position)
        if not item: return

        menu = QMenu()
        refresh_action = menu.addAction("하위 요소 새로고침 (Refresh Children)")
        action = menu.exec(self.mapToGlobal(position))

        if action == refresh_action:
            self.refresh_request.emit(item)

class UITreeView(QWidget):
    refresh_request = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.tree_widget = ExplorableTreeWidget()
        self.tree_widget.refresh_request.connect(self.refresh_request.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)

    def update_item_children(self, parent_item, children_data):
        parent_item.takeChildren()
        for child_node in children_data.get("children", []):
            self._add_items_recursive(parent_item, child_node)
        parent_item.setExpanded(True)

    # ✅ 메서드 이름을 수정하고 전체 노드 데이터를 반환합니다.
    def get_selected_node_data(self):
        """현재 선택된 아이템의 전체 데이터(속성, 경로 포함)를 반환합니다."""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(0, Qt.ItemDataRole.UserRole)
    
    def populate_tree(self, tree_data):
        self.tree_widget.clear()
        if tree_data:
            self._add_items_recursive(self.tree_widget.invisibleRootItem(), tree_data)

    def _add_items_recursive(self, parent_item, node_data):
        props = node_data.get("properties", {})
        display_text = f"{props.get('control_type', 'Unknown')}: '{props.get('title', '')}'"
        
        item = QTreeWidgetItem(parent_item, [display_text])
        
        # ✅ 핵심 수정: 속성(props)이 아닌 전체 노드 데이터(node_data)를 저장합니다.
        item.setData(0, Qt.ItemDataRole.UserRole, node_data)
        
        for child_node in node_data.get("children", []):
            self._add_items_recursive(item, child_node)

