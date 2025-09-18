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
    UIA와 Win32 백엔드를 모두 사용하여 연결 안정성을 극대화하는
    하이브리드 앱 커넥터입니다.
    """
    def __init__(self):
        self.app = None
        self.main_window = None
        self.backend = None  # 연결에 성공한 백엔드('uia' 또는 'win32')
        os.makedirs(CACHE_DIR, exist_ok=True)

    def connect_to_app(self, title_re):
        """
        성공할 때까지 UIA와 Win32 백엔드를 순차적으로 시도하여 앱에 연결합니다.
        """
        log.info(f"Connecting to app with title_re='{title_re}' using Hybrid Strategy.")
        
        # 1순위: 최신 앱에 적합한 UIA 백엔드 먼저 시도
        try:
            log.info("--- Attempting connection with 'uia' backend ---")
            self.app = Application(backend="uia").connect(title_re=title_re, timeout=10)
            self.main_window = self.app.top_window()
            self.main_window.wait('exists', timeout=5) # 창이 실제로 존재하는지 확인
            self.backend = "uia"
            log.info(f"✅ Connection SUCCESS with 'uia' backend. Window: '{self.main_window.window_text()}'")
            return True
        except Exception as e_uia:
            log.warning(f"❌ 'uia' backend failed: {e_uia}. Falling back to 'win32' backend.")

            # 2순위: UIA 실패 시, 구형 앱에 안정적인 Win32 백엔드로 재시도
            try:
                log.info("--- Attempting connection with 'win32' backend ---")
                self.app = Application(backend="win32").connect(title_re=title_re, timeout=10)
                self.main_window = self.app.top_window()
                self.main_window.wait('exists', timeout=5)
                self.backend = "win32"
                log.info(f"✅ Connection SUCCESS with 'win32' backend. Window: '{self.main_window.window_text()}'")
                return True
            except Exception as e_win32:
                log.error(f"❌ 'win32' backend also failed: {e_win32}")

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
            time.sleep(0.5)
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
            return ui_tree
        except Exception as e:
            log.error(f"Failed to build UI tree: {e}", exc_info=True)
            return None

    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        if path is None: path = []
        if not element or current_depth > max_depth: return None

        try:
            element_props = self._extract_properties(element.element_info)
        except Exception:
            return None

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
            # 캐시 파일 이름에 백엔드 정보를 포함하여 구별
            return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}_{self.backend}.json")
        except Exception:
            return None

    # 나머지 캐시 관련 함수들은 기존과 동일
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