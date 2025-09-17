# core/app_connector.py 최종 수정안

import re
from pywinauto.application import Application
from utils.logger_config import log

class AppConnector:
    """
    Windows 애플리케이션 연결 및 UI 구조 분석을 위한 클래스.
    """
    def __init__(self):
        """AppConnector 인스턴스를 초기화합니다."""
        self.app = None
        self.main_window = None

    def connect_to_app(self, title_re):
        """
        주어진 정규식과 일치하는 창 제목을 가진 애플리케이션에 대소문자 구분 없이 연결합니다.
        """
        try:
            log.info(f"Connecting to application with title_re='{title_re}' (case-insensitive)...")
            compiled_pattern = re.compile(title_re, re.IGNORECASE)
            
            self.app = Application(backend="uia").connect(title_re=compiled_pattern, timeout=20) # 복잡한 앱을 위해 타임아웃 증가
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
        연결된 애플리케이션의 전체 UI 구조를 깊이 탐색하여 딕셔너리 트리로 반환합니다.
        """
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        
        try:
            log.info("Bringing window to front and building full UI tree...")
            self.main_window.set_focus()
            
            # descendants()가 반환하는 것은 UIAWrapper 객체의 리스트입니다.
            all_elements = self.main_window.descendants()

            # ✅ 수정: Wrapper에서 .element_info를 통해 실제 정보에 접근합니다.
            root_element_info = self.main_window.element_info 
            tree = {
                "properties": self._extract_properties(root_element_info),
                "children": []
            }
            
            node_map = {root_element_info.runtime_id: tree}

            # ✅ 수정: all_elements 리스트의 각 항목은 UIAWrapper 객체입니다.
            for wrapper in all_elements:
                element_info = wrapper.element_info
                current_id = element_info.runtime_id
                
                if current_id in node_map:
                    continue

                node = {
                    "properties": self._extract_properties(element_info),
                    "children": []
                }
                node_map[current_id] = node

                # ✅ 수정: 부모를 찾을 때도 .element_info를 거쳐야 합니다.
                parent_wrapper = wrapper.parent()
                if parent_wrapper:
                    parent_id = parent_wrapper.element_info.runtime_id
                    if parent_id in node_map:
                        node_map[parent_id]["children"].append(node)

            return tree
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None

    def _extract_properties(self, element_info):
        """pywinauto의 element_info 객체에서 필요한 속성만 추출합니다."""
        return {
            "title": element_info.name,
            "control_type": element_info.control_type,
            "auto_id": element_info.automation_id,
            "runtime_id": element_info.runtime_id
        }
