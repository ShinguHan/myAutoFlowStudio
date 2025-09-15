# -*- coding: utf-8 -*-
"""
이 모듈은 pywinauto를 사용하여 Windows 애플리케이션에 연결하고,
해당 앱의 UI 구조를 분석하여 트리(Tree) 형태로 반환하는 역할을 담당합니다.
GUI와 실제 자동화 로직 사이의 핵심적인 다리 역할을 합니다.
"""
from pywinauto.application import Application
from utils.logger_config import log

class AppConnector:
    """
    Windows 애플리케이션 연결 및 UI 구조 분석을 위한 클래스.
    하나의 인스턴스가 하나의 애플리케이션 연결을 관리합니다.
    """
    def __init__(self):
        """AppConnector 인스턴스를 초기화합니다."""
        self.app = None
        self.main_window = None

    def connect_to_app(self, title_re):
        """
        주어진 정규식과 일치하는 창 제목을 가진 애플리케이션에 연결합니다.

        Args:
            title_re (str): 연결할 창 제목의 정규식 패턴.

        Returns:
            bool: 연결 성공 여부.
        """
        try:
            log.info(f"Connecting to application with title_re='{title_re}'...")
            # 'uia' 백엔드를 사용하여 최신 Windows 애플리케이션(UWP 포함)과 호환성을 높입니다.
            self.app = Application(backend="uia").connect(title_re=title_re, timeout=10)
            # 가장 상위 윈도우를 메인 윈도우로 지정합니다.
            self.main_window = self.app.top_window()
            log.info(f"Successfully connected. Main window: '{self.main_window.window_text()}'")
            return True
        except Exception as e:
            log.error(f"Failed to connect to application: {e}", exc_info=True)
            self.app = None
            self.main_window = None
            return False

    def get_ui_tree(self):
        """
        연결된 애플리케이션의 UI 구조를 재귀적으로 탐색하여 딕셔너리 트리로 반환합니다.

        Returns:
            dict or None: UI 구조를 나타내는 딕셔너리 트리. 연결 실패 시 None.
        """
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        
        log.info("Building UI tree...")
        return self._build_tree_recursive(self.main_window)

    def _build_tree_recursive(self, element):
        """
        주어진 UI 요소(element)부터 시작하여 하위 모든 요소를 재귀적으로 탐색하고
        트리 구조의 노드를 생성합니다.

        Args:
            element: pywinauto의 윈도우 스펙(WindowSpecification) 객체.

        Returns:
            dict: 해당 요소와 그 자식들의 정보를 담은 딕셔너리.
        """
        try:
            # 요소의 핵심 식별 정보를 추출합니다. 이 정보는 나중에 UI를 제어할 때 사용됩니다.
            element_properties = {
                "title": element.window_text(),
                "control_type": element.element_info.control_type,
                "auto_id": element.element_info.automation_id,
            }

            # 현재 요소의 정보를 포함하는 노드를 생성합니다.
            node = {
                "properties": element_properties,
                "children": []
            }

            # 현재 요소의 모든 자식(children)을 순회하며 재귀적으로 함수를 호출합니다.
            for child in element.children():
                child_node = self._build_tree_recursive(child)
                if child_node:
                    node["children"].append(child_node)
            
            return node
        except Exception as e:
            # 간혹 접근 권한이 없거나 사라지는 UI 요소에 대한 오류를 방지합니다.
            log.debug(f"Could not process element: {element}. Error: {e}")
            return None

