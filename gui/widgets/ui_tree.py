# gui/widgets/ui_tree.py 최종 수정안

# -*- coding: utf-8 -*-
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt, QMimeData, QByteArray
from PyQt6.QtGui import QDrag
from utils.logger_config import log

class DraggableTreeWidget(QTreeWidget):
    """
    드래그 시작 로직을 커스터마이징한 QTreeWidget의 서브클래스.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)

    def startDrag(self, supportedActions):
        """
        드래그가 시작될 때 호출되어, 전달할 데이터를 MIME 데이터로 포장합니다.
        QTreeWidget의 메서드를 직접 오버라이드하는 가장 안정적인 방법입니다.
        """
        log.debug("--- Drag operation initiated from DraggableTreeWidget ---")
        selected_items = self.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        element_props = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not element_props:
            return

        mime_data = QMimeData()
        # 데이터를 JSON 형식으로 직렬화하여 MIME 데이터에 담습니다.
        json_data = json.dumps(element_props).encode('utf-8')
        mime_data.setData("application/json/pywinauto-element", QByteArray(json_data))
        
        # 드래그 객체를 생성하고 실행합니다.
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)


class UITreeView(QWidget):
    """
    AppConnector가 분석한 UI 구조를 표시하는 트리뷰 위젯.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ✅ 표준 QTreeWidget 대신, 우리가 만든 DraggableTreeWidget을 사용합니다.
        self.tree_widget = DraggableTreeWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)

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