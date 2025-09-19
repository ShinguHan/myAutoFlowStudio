# core/app_connector.py

import re
import time
import os  # ✅ 추가
import json # ✅ 추가
import hashlib # ✅ 추가: 파일명 해싱을 위해
from pywinauto.application import Application
from utils.logger_config import log

# ✅ 추가: 캐시 파일을 저장할 디렉토리 경로
CACHE_DIR = "cache"

class AppConnector:
    """
    Windows 애플리케이션 연결 및 UI 구조 분석을 위한 클래스.
    UI 트리 캐싱 기능을 포함합니다.
    """
    def __init__(self):
        """AppConnector 인스턴스를 초기화합니다."""
        self.app = None
        self.main_window = None
        # ✅ 추가: 캐시 디렉토리가 없으면 생성
        os.makedirs(CACHE_DIR, exist_ok=True)

    def connect_to_app(self, title_re):
        # ... (기존과 동일) ...
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

    def get_ui_tree(self, max_depth=20):
        """
        연결된 애플리케이션의 UI 구조를 재귀적으로 탐색하여 딕셔너리 트리로 반환합니다.
        성공적으로 탐색된 결과는 캐시 파일로 저장됩니다.
        """
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        
        try:
            log.info(f"Bringing window to front and building UI tree recursively (max_depth={max_depth})...")
            self.main_window.set_focus()
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            # ✅ 추가: 탐색 성공 시 결과를 캐시에 저장
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
                log.info("UI tree structure has been saved to cache.")

            return ui_tree
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None

    # --- 🔻🔻🔻 아래 4개의 메서드를 클래스 내에 새로 추가합니다. 🔻🔻🔻 ---

    def _get_cache_path(self):
        """현재 연결된 앱의 창 제목을 기반으로 고유한 캐시 파일 경로를 생성합니다."""
        if not self.main_window:
            return None
        
        # 파일명에 부적합한 문자를 제거하고, 해시를 사용하여 고유성을 보장합니다.
        window_text = self.main_window.window_text()
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", window_text)
        # 파일명이 너무 길어지는 것을 방지하기 위해 해시값을 사용
        title_hash = hashlib.md5(window_text.encode()).hexdigest()
        
        return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}.json")

    def has_cache(self):
        """현재 앱에 대한 유효한 캐시 파일이 존재하는지 확인합니다."""
        cache_path = self._get_cache_path()
        return cache_path and os.path.exists(cache_path)

    def _save_tree_to_cache(self, ui_tree):
        """UI 트리 딕셔너리를 JSON 파일로 저장합니다."""
        cache_path = self._get_cache_path()
        if not cache_path: return

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.error(f"Failed to save UI tree to cache file '{cache_path}': {e}")
    
    def load_tree_from_cache(self):
        """캐시된 JSON 파일에서 UI 트리를 불러옵니다."""
        if not self.has_cache():
            log.warning("No cache file found to load.")
            return None
        
        cache_path = self._get_cache_path()
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                log.info(f"Loading UI tree from cache: {cache_path}")
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load UI tree from cache file '{cache_path}': {e}")
            return None
    
    # ✅ 수정: 'path' 인자를 추가하여 부모 경로를 추적합니다.
    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        """
        주어진 UI 요소부터 시작하여 재귀적으로 UI 트리를 구축합니다.
        각 노드에 자신의 전체 경로(path) 정보를 추가합니다.
        """
        if path is None:
            path = []

        if not element or current_depth > max_depth:
            return None

        element_props = self._extract_properties(element.element_info)
        
        # ✅ 추가: 현재 요소의 식별자를 경로에 추가
        current_path = path + [element_props]

        node = {
            "properties": element_props,
            # ✅ 추가: 완성된 경로를 노드에 저장
            "path": current_path,
            "children": []
        }

        try:
            child_elements = element.children()
        except Exception:
            child_elements = []

        tab_items = [child for child in child_elements if child.element_info.control_type == 'TabItem']

        if tab_items:
            log.debug(f"Tab container found: '{element.element_info.name}'. Iterating through {len(tab_items)} tabs.")
            processed_child_ids = set()

            for tab_item in tab_items:
                try:
                    log.debug(f"Selecting TabItem: '{tab_item.element_info.name}'")
                    if not tab_item.is_selected():
                        tab_item.select()
                        time.sleep(0.5)

                    refreshed_children = element.children()
                    
                    for child in refreshed_children:
                        child_id = child.element_info.runtime_id
                        if child_id not in processed_child_ids:
                            processed_child_ids.add(child_id)
                            # ✅ 수정: 자식에게 현재 경로(current_path)를 넘겨줍니다.
                            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
                            if child_node:
                                node["children"].append(child_node)
                except Exception as e:
                    log.warning(f"Failed to process TabItem '{tab_item.element_info.name}': {e}")
        else:
            for child in child_elements:
                # ✅ 수정: 자식에게 현재 경로(current_path)를 넘겨줍니다.
                child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
                if child_node:
                    node["children"].append(child_node)
        
        return node

    def _extract_properties(self, element_info):
        """pywinauto의 element_info 객체에서 필요한 속성만 추출합니다."""
        # ✅ *** 핵심 수정: class_name을 추가로 추출합니다 ***
        return {
            "title": element_info.name,
            "class_name": element_info.class_name, # 이 라인을 추가
            "control_type": element_info.control_type,
            "auto_id": element_info.automation_id,
            "runtime_id": element_info.runtime_id
        }
