# core/app_connector.py

import re
import time
import os
import json
import hashlib
from pywinauto.application import Application
from pywinauto import findwindows, Desktop
from utils.logger_config import log

CACHE_DIR = "cache"

class AppConnector:
    def __init__(self):
        self.app = None
        self.main_window = None
        self.backend = None
        os.makedirs(CACHE_DIR, exist_ok=True)



    def connect_to_app(self, title_re):
        """
        [최종 수정] '정확한 제목' 매칭을 먼저 시도하고, 실패 시 '정규식' 매칭으로
        폴백(fallback)하는 가장 안정적인 하이브리드 연결 로직입니다.
        """
        log.info(f"Connecting to app with smart strategy: '{title_re}'")
        
        # --- 1순위: UIA 백엔드 시도 ---
        try:
            log.info("--- Attempting UIA backend ---")
            # 1-1. '정확한 제목'으로 먼저 시도 (가장 안정적)
            try:
                log.debug("Step 1-1: UIA with exact title match...")
                self.app = Application(backend="uia").connect(title=title_re, timeout=10)
            # 1-2. 실패 시 '정규식'으로 재시도
            except Exception:
                log.debug("Step 1-2: UIA with regex title match...")
                self.app = Application(backend="uia").connect(title_re=title_re, timeout=10)
            
            self.main_window = self.app.top_window()
            self.main_window.wait('exists', timeout=5)
            self.backend = "uia"
            log.info(f"✅ Connection SUCCESS with 'uia' backend. Window: '{self.main_window.window_text()}'")
            return True
        except Exception as e_uia:
            log.warning(f"❌ UIA backend failed for both methods: {e_uia}. Falling back to 'win32'.")

        # --- 2순위: Win32 백엔드 시도 ---
        try:
            log.info("--- Attempting Win32 backend ---")
            # 2-1. '정확한 제목'으로 먼저 시도
            try:
                log.debug("Step 2-1: Win32 with exact title match...")
                self.app = Application(backend="win32").connect(title=title_re, timeout=10)
            # 2-2. 실패 시 '정규식'으로 재시도
            except Exception:
                log.debug("Step 2-2: Win32 with regex title match...")
                self.app = Application(backend="win32").connect(title_re=title_re, timeout=10)

            self.main_window = self.app.top_window()
            self.main_window.wait('exists', timeout=5)
            self.backend = "win32"
            log.info(f"✅ Connection SUCCESS with 'win32' backend. Window: '{self.main_window.window_text()}'")
            return True
        except Exception as e_win32:
            log.error(f"❌ Win32 backend also failed for both methods: {e_win32}")

        log.error(f"FATAL: All connection attempts failed for '{title_re}'.")
        self.app = None
        self.main_window = None
        self.backend = None
        return False

    @staticmethod
    def get_connectable_windows():
        try:
            windows = Desktop(backend="uia").windows()
            window_titles = sorted(list(set([
                w.window_text() for w in windows if w.window_text() and w.is_visible()
            ])))
            return window_titles
        except Exception as e:
            log.error(f"Failed to get list of connectable windows: {e}")
            return []


    def get_ui_tree(self, max_depth=20):
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        try:
            log.info(f"🚀 Starting Interactive Deep Scan (max_depth={max_depth}). This may take a while...")
            self.main_window.set_focus()
            
            # 탐색 중 상호작용한 요소를 기록하여 무한 루프 방지
            self.interacted_ids = set() 
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
                log.info("✅ Interactive Deep Scan complete. UI tree has been saved to cache.")
            return ui_tree
        except Exception as e:
            log.error(f"An error occurred during the deep scan: {e}", exc_info=True)
        
        

    def refresh_subtree(self, path, max_depth=5):
        if not self.main_window: return None
        try:
            # ✅ [수정] 모호성 해결을 위해 find_element 사용
            target_element = findwindows.find_element(backend=self.backend, top_level_only=False, path=path)
            wrapper = self.backend.generic_wrapper_class(target_element)

            log.info(f"Found element '{self._get_element_name(wrapper)}'. Revealing children.")
            
            if hasattr(wrapper, 'expand'): wrapper.expand()
            elif hasattr(wrapper, 'invoke'): wrapper.invoke()
            time.sleep(0.5)

            children_nodes = []
            for child in wrapper.children():
                node = self._build_tree_recursively(child, 0, max_depth, path)
                if node: children_nodes.append(node)
            return children_nodes
        except Exception as e:
            log.error(f"An error occurred while refreshing subtree: {e}", exc_info=True)
            return None

    def _get_cache_path(self):
        if not self.main_window: return None
        window_text = self.main_window.window_text()
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", window_text)
        title_hash = hashlib.md5(window_text.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}_{self.backend}.json")

    def has_cache(self):
        cache_path = self._get_cache_path()
        return cache_path and os.path.exists(cache_path)

    def _save_tree_to_cache(self, ui_tree):
        cache_path = self._get_cache_path()
        if not cache_path: return
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(ui_tree, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.error(f"Failed to save UI tree to cache: {e}")
    
    def load_tree_from_cache(self):
        cache_path = self._get_cache_path()
        if not self.has_cache(): return None
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                log.info(f"Loading UI tree from cache: {cache_path}")
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load UI tree from cache: {e}")
            return None
    
    def _get_element_id(self, element):
        """백엔드에 상관없이 요소의 고유 식별자를 반환합니다."""
        if self.backend == 'uia':
            return element.element_info.runtime_id
        else: # win32
            return element.handle

    def _get_element_name(self, element):
        """백엔드에 상관없이 요소의 이름을 반환합니다."""
        if self.backend == 'uia':
            return element.element_info.name
        else: # win32
            return element.window_text()

    def _extract_properties(self, element):
        if self.backend == 'uia':
            return self._extract_properties_uia(element.element_info)
        else: # win32
            return self._extract_properties_win32(element)
        
    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        if path is None: path = []
        if not element or current_depth > max_depth: return None

        try:
            element_props = self._extract_properties(element)
        except Exception:
            return None

        current_path = path + [element_props]
        node = { "properties": element_props, "path": current_path, "children": [] }

        element_id = self._get_element_id(element)
        if element_id not in self.interacted_ids:
            self.interacted_ids.add(element_id)
            
            # ✅ [수정] 자식 요소들에게 상호작용을 시도하는 방식으로 변경
            try:
                for child in element.children():
                    child_id = self._get_element_id(child)
                    if child_id in self.interacted_ids: continue
                    
                    if hasattr(child, 'select'):
                        log.debug(f"Selecting child: '{self._get_element_name(child)}'")
                        child.select()
                        self.interacted_ids.add(child_id)
                        time.sleep(0.2) # 탭 전환 시간
            except Exception:
                pass # 자식이 없거나 상호작용 실패 시 안전하게 무시

            # 부모 요소에 대한 상호작용 (메뉴 등)
            try:
                if hasattr(element, 'expand'):
                    element.expand()
                elif hasattr(element, 'invoke'):
                    element.invoke()
                time.sleep(0.2)
            except Exception:
                pass

        try:
            final_child_elements = element.children()
        except Exception:
            final_child_elements = []
            
        for child in final_child_elements:
            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
            if child_node:
                node["children"].append(child_node)
        return node


    def _extract_properties_uia(self, element_info):
        return {
            "title": element_info.name,
            "class_name": element_info.class_name,
            "control_type": element_info.control_type,
            "auto_id": element_info.automation_id,
            "runtime_id": element_info.runtime_id
        }

    def _extract_properties_win32(self, element):
        return {
            "title": element.window_text(),
            "class_name": element.class_name(),
            "control_type": element.friendly_class_name(),
            "auto_id": None,
            "runtime_id": element.handle
        }
