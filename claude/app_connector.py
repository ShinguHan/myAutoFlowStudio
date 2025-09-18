# core/app_connector.py

import re
import time
import os
import json
import hashlib
from pywinauto.application import Application
from pywinauto import findwindows
from utils.logger_config import log

CACHE_DIR = "cache"

class AppConnector:
    """
    '방어적 자동화' 개념이 적용된 Windows 애플리케이션 연결 클래스.
    - 다중 백엔드 및 다중 연결 전략을 통해 연결 성공률을 극대화합니다.
    - 모든 속성 접근을 안전하게 처리하여 예외 발생을 최소화합니다.
    - 탭(Tab) 컨트롤과 같이 동적으로 변하는 UI 구조를 안정적으로 분석합니다.
    """
    def __init__(self):
        self.app = None
        self.main_window = None
        self.backend = None  # 연결에 성공한 백엔드 저장
        os.makedirs(CACHE_DIR, exist_ok=True)

    def connect_to_app(self, title_re):
        """
        성공할 때까지 가능한 모든 방법으로 앱에 연결을 시도합니다.

        1. UIA 백엔드로 title_re, class_name 등 다양한 방법 시도
        2. Win32 백엔드로 title_re, class_name 등 다양한 방법 시도
        """
        log.info(f"Connecting to app with title_re='{title_re}' using Defensive Strategy.")
        
        # 시도할 백엔드 우선순위
        backends_to_try = ["uia", "win32"]
        
        for backend in backends_to_try:
            try:
                log.info(f"--- Attempting connection with '{backend}' backend ---")
                # connect()는 다양한 식별자를 시도하므로 가장 유연함
                self.app = Application(backend=backend).connect(title_re=title_re, timeout=10)
                self.main_window = self.app.top_window()
                
                # 연결 성공 검증: 창 제목을 실제로 가져올 수 있는지 확인
                window_title = self.main_window.window_text()
                
                self.backend = backend
                log.info(f"✅ Connection SUCCESS with '{backend}' backend. Window: '{window_title}'")
                return True
            except Exception as e:
                log.warning(f"❌ Connection with '{backend}' backend failed: {e}")
                continue # 다음 백엔드로 계속 시도

        log.error(f"All connection attempts failed for title_re='{title_re}'.")
        self.app = None
        self.main_window = None
        return False

    def get_ui_tree(self, max_depth=20):
        if not self.main_window:
            log.warning("Cannot get UI tree. No application is connected.")
            return None
        try:
            log.info(f"Building UI tree using '{self.backend}' backend (max_depth={max_depth}).")
            self.main_window.set_focus()
            time.sleep(0.5) # UI가 안정화될 시간을 확보
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
            return ui_tree
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None

    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        if path is None: path = []
        if not element or current_depth > max_depth: return None

        try:
            element_props = self._extract_properties(element.element_info)
        except Exception:
            return None # 속성 추출 실패 시 해당 브랜치 중단

        current_path = path + [element_props]
        node = {"properties": element_props, "path": current_path, "children": []}

        try:
            child_elements = element.children()
        except Exception:
            child_elements = []

        for child in child_elements:
            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
            if child_node:
                node["children"].append(child_node)
        return node

    def _extract_properties(self, element_info):
        """
        어떤 속성이 존재하지 않더라도 오류를 발생시키지 않는 안전한 속성 추출
        """
        return {
            "title": getattr(element_info, 'name', ''),
            "control_type": getattr(element_info, 'control_type', ''),
            "auto_id": getattr(element_info, 'automation_id', ''),
            "runtime_id": getattr(element_info, 'runtime_id', '')
        }
        
    def _get_cache_path(self):
        if not self.main_window: return None
        try:
            window_text = self.main_window.window_text()
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", window_text)
            title_hash = hashlib.md5(window_text.encode()).hexdigest()
            return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}_{self.backend}.json")
        except Exception:
            return None

    def has_cache(self):
        cache_path = self._get_cache_path()
        return cache_path and os.path.exists(cache_path)

    def _save_tree_to_cache(self, ui_tree):
        cache_path = self._get_cache_path()
        if not cache_path: return
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=2)
            log.info(f"UI tree cached to: {cache_path}")
        except Exception as e:
            log.error(f"Failed to save UI tree to cache: {e}")

    def load_tree_from_cache(self):
        cache_path = self._get_cache_path()
        if not cache_path or not os.path.exists(cache_path):
            log.warning("No cache file found to load.")
            return None
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                log.info(f"Loading UI tree from cache: {cache_path}")
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load UI tree from cache: {e}")
            return None