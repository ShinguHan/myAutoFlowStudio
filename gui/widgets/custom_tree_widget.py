# -*- coding: utf-8 -*-
"""
이 모듈은 PyQt6의 QTreeWidget을 기반으로 하는 커스텀 트리 위젯을 정의합니다.
이 위젯은 시나리오 편집기(FlowEditor)의 기반 클래스로 사용되며,
드래그 앤 드롭을 통한 시나리오 단계의 재정렬과 같은
고급 상호작용을 지원하도록 설계되었습니다.

특히, 외부(UITreeView)에서의 드롭 이벤트를 감지하여 시그널을 발생시키고,
위젯 내부에서의 아이템 순서 변경(InternalMove)도 처리합니다.
"""
import json
from PyQt6.QtWidgets import QTreeWidget
from PyQt6.QtCore import pyqtSignal, Qt, QPoint

class CustomTreeWidget(QTreeWidget):
    """
    시나리오 편집을 위해 드래그 앤 드롭 및 내부 이동(InternalMove) 기능을
    지원하는 QTreeWidget의 확장 클래스입니다.
    """
    # 외부(UITreeView)에서 UI 요소가 드롭되었을 때,
    # 해당 요소의 속성(dict)을 전달하는 커스텀 시그널
    element_dropped = pyqtSignal(dict, QPoint)

    def __init__(self, parent=None):
        """CustomTreeWidget 인스턴스를 초기화합니다."""
        super().__init__(parent)
        # 드롭 이벤트를 받기 위해 acceptDrops를 True로 설정합니다.
        # 이 설정은 FlowEditor에서도 다시 한 번 수행될 수 있지만,
        # 위젯 자체의 핵심 속성이므로 여기서 정의하는 것이 명확합니다.
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """
        드래그된 아이템이 위젯 영역으로 들어왔을 때 호출됩니다.
        처리할 수 있는 데이터 형식(MIME type)인지 확인합니다.
        """
        # UITreeView에서 정의한 커스텀 MIME 타입을 가지고 있는지 확인
        if event.mimeData().hasFormat("application/json/pywinauto-element"):
            # 해당 MIME 타입이 있다면, 드롭을 허용(accept)합니다.
            event.acceptProposedAction()
        else:
            # 커스텀 MIME 타입이 없다면, QTreeWidget의 기본 동작(순서 변경 등)에 맡깁니다.
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """
        드래그된 상태로 위젯 영역 내에서 마우스가 움직일 때 호출됩니다.
        dragEnterEvent와 마찬가지로 드롭 가능 여부를 결정합니다.
        """
        if event.mimeData().hasFormat("application/json/pywinauto-element"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """
        위젯에 아이템이 드롭되었을 때 최종적으로 호출됩니다.
        데이터를 처리하고, 필요한 동작(시그널 발생 또는 순서 변경)을 수행합니다.
        """
        mime_data = event.mimeData()

        # 1. UITreeView로부터의 드롭인지 확인
        if mime_data.hasFormat("application/json/pywinauto-element"):
            # MIME 데이터에서 JSON 바이트 배열을 가져옵니다.
            json_bytes = mime_data.data("application/json/pywinauto-element")
            # 바이트 배열을 UTF-8 문자열로 디코딩하고, JSON 파싱을 통해 딕셔너리로 변환합니다.
            try:
                # element_props = json.loads(json_bytes.data().decode('utf-8'))
                # element_dropped 시그널을 발생시켜 FlowEditor에 알립니다.
                 # ✅ 수정된 부분: .data()를 제거하여 QByteArray를 올바르게 디코딩합니다.
                element_props = json.loads(json_bytes.decode('utf-8'))

                # ✅ 시그널 발생 시, 드롭된 좌표(event.position())를 함께 전달
                self.element_dropped.emit(element_props, event.position().toPoint())
                
                # 이벤트 처리가 완료되었음을 알립니다.
                event.acceptProposedAction()
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error decoding dropped data: {e}")
                event.ignore()
        else:
            # 2. 내부 아이템 순서 변경(InternalMove)인 경우
            # QTreeWidget의 기본 dropEvent를 호출하여 순서 변경이 정상적으로 처리되도록 합니다.
            super().dropEvent(event)
