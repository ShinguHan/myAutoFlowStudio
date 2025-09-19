# gui/widgets/ui_tree.py

import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu
# ✅ QDrag 임포트 추가
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from utils.logger_config import log

class ExplorableTreeWidget(QTreeWidget):
    """
    드래그 앤 드롭과 우클릭 새로고침 기능을 지원하는 커스텀 트리 위젯.
    """
    refresh_request = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)

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

    # ✅ *** 핵심 수정: 'dnd' 오류 수정 ***
    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        node_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_data:
            return

        try:
            json_str = json.dumps(node_data)
            byte_array = json_str.encode('utf-8')

            mime_data = QMimeData()
            mime_data.setData("application/json/pywinauto-element", byte_array)

            # QDrag 객체를 직접 생성합니다.
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            # drag.exec()는 사용법이 약간 다릅니다. Qt.DropAction.CopyAction를 인자로 전달합니다.
            drag.exec(Qt.DropAction.CopyAction)

        except (TypeError, json.JSONDecodeError) as e:
            log.error(f"Failed to serialize node data for drag-and-drop: {e}")

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
        """특정 아이템의 자식 노드들을 새로운 데이터로 교체합니다."""
        parent_item.takeChildren()
        for child_node in children_data:
            self._add_items_recursive(parent_item, child_node)
        parent_item.setExpanded(True)
    
    def get_selected_node_data(self):
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
        
        item.setData(0, Qt.ItemDataRole.UserRole, node_data)
        
        for child_node in node_data.get("children", []):
            self._add_items_recursive(item, child_node)
