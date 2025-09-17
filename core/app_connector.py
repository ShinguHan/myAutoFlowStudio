# core/app_connector.py

import re
import time
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
            
            self.app = Application(backend="uia").connect(title_re=compiled_pattern, timeout=20)
            self.main_window = self.app.top_window()
            
            log.info(f"Successfully connected. Main window: '{self.main_window.window_text()}'")
            return True
        except Exception as e:
            log.error(f"Failed to connect to application: {e}", exc_info=True)
            self.app = None
            self.main_window = None
            return False

    def get_ui_tree(self, max_depth=20): # 더 깊은 탐색을 위해 기본 깊이 증가
        """
        연결된 애플리케이션의 UI 구조를 재귀적으로 탐색하여 딕셔너리 트리로 반환합니다.
        """
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        
        try:
            log.info(f"Bringing window to front and building UI tree recursively (max_depth={max_depth})...")
            self.main_window.set_focus()
            
            return self._build_tree_recursively(self.main_window, 0, max_depth)
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None

    def _build_tree_recursively(self, element, current_depth, max_depth):
        """
        주어진 UI 요소부터 시작하여 재귀적으로 UI 트리를 구축합니다.
        Tab 컨트롤을 만나면 모든 탭을 순회하며 동적으로 로드되는 콘텐츠까지 탐색합니다.
        """
        if not element or current_depth > max_depth:
            return None

        node = {
            "properties": self._extract_properties(element.element_info),
            "children": []
        }

        try:
            child_elements = element.children()
        except Exception:
            child_elements = []

        # ✅ 핵심 변경: 자식 중에 TabItem이 있는지 확인하여 Tab 컨테이너인지 판별
        tab_items = [child for child in child_elements if child.element_info.control_type == 'TabItem']

        if tab_items:
            # 이 요소는 Tab 컨테이너입니다. 모든 탭을 순회하며 컨텐츠를 수집합니다.
            log.debug(f"Tab container found: '{element.element_info.name}'. Iterating through {len(tab_items)} tabs.")
            
            # 중복 탐색을 방지하기 위해 이미 처리된 자식의 runtime_id를 저장
            processed_child_ids = set()

            for tab_item in tab_items:
                try:
                    log.debug(f"Selecting TabItem: '{tab_item.element_info.name}'")
                    tab_item.select()
                    time.sleep(0.5) # 콘텐츠 로딩 대기. 필요시 시간 조절

                    # 탭 선택 후 컨테이너(element)의 자식 목록을 새로고침하여
                    # 동적으로 생긴 콘텐츠(Pane 등)를 확인합니다.
                    refreshed_children = element.children()
                    
                    for child in refreshed_children:
                        child_id = child.element_info.runtime_id
                        if child_id not in processed_child_ids:
                            processed_child_ids.add(child_id)
                            # 새로 발견된 자식에 대해서만 하위 트리를 구축합니다.
                            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth)
                            if child_node:
                                node["children"].append(child_node)

                except Exception as e:
                    log.warning(f"Failed to process TabItem '{tab_item.element_info.name}': {e}")
        
        else:
            # 일반적인 컨트롤인 경우, 모든 자식에 대해 재귀 호출
            for child in child_elements:
                child_node = self._build_tree_recursively(child, current_depth + 1, max_depth)
                if child_node:
                    node["children"].append(child_node)
        
        return node

    def _extract_properties(self, element_info):
        """pywinauto의 element_info 객체에서 필요한 속성만 추출합니다."""
        return {
            "title": element_info.name,
            "control_type": element_info.control_type,
            "auto_id": element_info.automation_id,
            "runtime_id": element_info.runtime_id
        }
