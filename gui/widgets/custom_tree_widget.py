# -*- coding: utf-8 -*-
"""
이 모듈은 연결된 애플리케이션의 UI 구조를 시각적인 트리 형태로
표시하는 UI 탐색기(UITreeView) 위젯을 정의합니다.
사용자는 이 트리를 통해 자동화할 UI 요소를 식별하고, 시나리오 편집기로
드래그 앤 드롭할 수 있습니다.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt
import json

class UITreeView(QWidget):
    """
    AppConnector가 분석한 UI 구조를 표시하는 트리뷰 위젯.
    """
    def __init__(self, parent=None):
        """UITreeView 인스턴스를 초기화합니다."""
        super().__init__(parent)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        # 드래그 기능을 활성화합니다. 드롭은 허용하지 않습니다.
        self.tree_widget.setDragEnabled(True)
        self.tree_widget.setAcceptDrops(False)
        # 드래그 시작 시 MIME 데이터를 설정하기 위해 startDrag 메서드를 오버라이드합니다.
        self.tree_widget.startDrag = self.startDrag

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.tree_widget)
        self.setLayout(layout)

    def populate_tree(self, tree_data):
        """
        AppConnector로부터 받은 UI 트리 데이터로 위젯의 내용을 채웁니다.

        Args:
            tree_data (dict): UI 구조를 나타내는 딕셔너리 트리.
        """
        self.tree_widget.clear()
        if tree_data:
            self._add_items_recursive(self.tree_widget.invisibleRootItem(), tree_data)

    def _add_items_recursive(self, parent_item, node_data):
        """
        재귀적으로 딕셔너리 트리를 순회하며 QTreeWidgetItem을 생성하고 추가합니다.
        """
        props = node_data["properties"]
        # 화면에 표시될 텍스트를 결정합니다. (예: "Button: '저장'")
        display_text = f"{props.get('control_type', 'Unknown')}: '{props.get('title', '')}'"
        
        item = QTreeWidgetItem(parent_item, [display_text])
        # 드래그 앤 드롭 시 전달할 실제 데이터(프로퍼티)를 아이템에 저장합니다.
        item.setData(0, Qt.ItemDataRole.UserRole, props)
        
        for child_node in node_data["children"]:
            self._add_items_recursive(item, child_node)

    def startDrag(self, supportedActions):
        """
        드래그가 시작될 때 호출되어, 전달할 데이터를 MIME 데이터로 포장합니다.
        """
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        element_props = item.data(0, Qt.ItemDataRole.UserRole)
        
        # 데이터를 JSON 형식으로 직렬화하여 MIME 데이터에 담습니다.
        # 커스텀 MIME 타입을 사용하여 FlowEditor에서 이 데이터를 식별할 수 있도록 합니다.
        from PyQt6.QtCore import QMimeData, QByteArray
        mime_data = QMimeData()
        json_data = json.dumps(element_props).encode('utf-8')
        mime_data.setData("application/json/pywinauto-element", QByteArray(json_data))
        
        # 드래그 객체를 생성하고 실행합니다.
        from PyQt6.QtGui import QDrag
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

