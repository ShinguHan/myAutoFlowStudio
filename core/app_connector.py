# core/app_connector.py

import re
import time
import os
import json
import hashlib
from pywinauto.application import Application
# ✅ findwindows 임포트 추가
from pywinauto.timings import wait_until_passes
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
        # ... (기존 연결 로직은 그대로 사용) ...
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
        # ... (기존과 동일) ...
        try:
            windows = Desktop(backend="uia").windows()
            window_titles = sorted(list(set([
                w.window_text() for w in windows if w.window_text() and w.is_visible()
            ])))
            return window_titles
        except Exception as e:
            log.error(f"Failed to get list of connectable windows: {e}")
            return []

    def get_ui_tree(self, max_depth=15):
        """
        ✅ [핵심 수정] 1단계: 빠른 '표면 탐색'.
        이제 이 함수는 UI와 상호작용하지 않고 보이는 요소만 빠르게 스캔합니다.
        """
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        try:
            log.info(f"🚀 Starting FAST Surface Scan (max_depth={max_depth})...")
            self.main_window.set_focus()
            
            # ✅ 'interactive' 파라미터를 False로 전달하여 상호작용 비활성화
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth, interactive=False)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
                log.info("✅ Fast Scan complete. UI tree has been cached.")
            return ui_tree
        except Exception as e:
            log.error(f"An error occurred during the surface scan: {e}", exc_info=True)
            return None



    def refresh_subtree(self, path, max_depth=5):
        """
        TabItem 같은 경우는 직접 children()을 가지지 않으므로,
        선택(select) 후 TabControl 내부의 Pane/Group 컨텐츠를 찾아 children을 가져오도록 수정.
        """
        if not self.main_window or not path:
            return None
        try:
            # 1. "Best Match" 로직으로 최초의 요소를 찾습니다.
            target_props = path[-1]
            search_criteria = {}
            if target_props.get("title"):
                search_criteria["title"] = target_props.get("title")
            if target_props.get("control_type"):
                search_criteria["control_type"] = target_props.get("control_type")

            initial_candidates = self.main_window.descendants(**search_criteria)
            if not initial_candidates:
                raise findwindows.ElementNotFoundError(f"No elements found for {search_criteria}")

            wrapper = self._find_best_match(initial_candidates, path)
            log.info(f"Uniquely identified element for interaction: '{self._get_element_name(wrapper)}'")

            # 2. 요소와 상호작용을 시도합니다.
            try:
                wrapper.select()
            except Exception:
                try:
                    wrapper.expand()
                except Exception:
                    try:
                        wrapper.invoke()
                    except Exception:
                        log.debug(f"No interactive patterns supported by '{self._get_element_name(wrapper)}'.")

            # 3. TabItem 특별 처리: children() 대신 탭 컨텐츠 Pane/Group 탐색
            if wrapper.element_info.control_type == "TabItem":
                log.debug(f"'{self._get_element_name(wrapper)}' is a TabItem, checking for tab page content...")
                parent = wrapper.parent()
                tab_pages = [c for c in parent.children()
                             if c.element_info.control_type in ("Pane", "Group")]
                if tab_pages:
                    children_list = tab_pages[0].children()
                    log.info(f"Using TabPage from TabItem '{self._get_element_name(wrapper)}' with {len(children_list)} children.")
                else:
                    children_list = []
                    log.warning(f"No TabPage Pane/Group found for TabItem '{self._get_element_name(wrapper)}'.")
            else:
                # 기본 동작
                wait_until_passes(3, 0.5, lambda: wrapper.children() is not None)
                children_list = wrapper.children()
                log.debug(f"Call to wrapper.children() returned {len(children_list)} items.")

            # 4. 자식 요소 상세 로그
            for i, child in enumerate(children_list):
                log.debug(f"  - Child {i+1}: '{self._get_element_name(child)}' ({child.element_info.control_type})")

            # 5. 최신 상태의 wrapper에서 자식 요소를 탐색합니다.
            children_nodes = []
            new_base_path = self._reconstruct_path_from_element(wrapper)
            for child in children_list:
                node = self._build_tree_recursively(child, 0, max_depth, new_base_path)
                if node:
                    children_nodes.append(node)

            log.info(f"✅ Deep Scan found {len(children_nodes)} child elements.")
            return children_nodes
        except Exception as e:
            log.error(f"An error occurred while refreshing subtree: {e}", exc_info=True)
            return None
    
    def _find_best_match(self, candidates, path):
        """
        [✅ 새로 추가된 헬퍼 함수]
        후보 요소 리스트와 목표 경로를 받아, 가장 일치하는 요소를 찾아 반환합니다.
        """
        log.debug(f"Finding best match from {len(candidates)} candidates.")
        best_match, highest_score = None, -1
        for candidate in candidates:
            candidate_path = self._reconstruct_path_from_element(candidate)
            score = 0
            # 경로의 길이와 각 단계의 속성을 비교하여 점수를 매깁니다.
            if len(candidate_path) == len(path):
                for i in range(len(path)):
                    if candidate_path[i]['title'] == path[i]['title'] and \
                       candidate_path[i]['control_type'] == path[i]['control_type']:
                        score += 1
            
            if score > highest_score:
                highest_score, best_match = score, candidate
        
        if not best_match:
            raise findwindows.ElementNotFoundError("Could not find a best match among ambiguous elements.")
        
        return best_match

    def _extract_path_from_element_info(self, element_info_path):
        """UIAElementInfo의 path 객체를 우리가 사용하는 dict 리스트로 변환"""
        new_path = []
        for info in element_info_path:
            new_path.append(self._extract_properties_uia(info))
        return new_path
    
    def _build_tree_recursively(self, element, current_depth, max_depth, path=None, interactive=False):
        """
        ✅ [핵심 수정] 재귀 탐색 함수에 'interactive' 플래그 추가.
        """
        if path is None: path = []
        if not element or current_depth > max_depth: return None

        try:
            element_props = self._extract_properties(element)
        except Exception:
            return None

        current_path = path + [element_props]
        node = { "properties": element_props, "path": current_path, "children": [] }

        # ✅ 'interactive' 플래그가 True일 때만 상호작용 시도 (현재는 refresh_subtree에서만 사용)
        if interactive:
            try:
                if hasattr(element, 'expand'): element.expand()
                elif hasattr(element, 'invoke'): element.invoke()
                time.sleep(0.2)
            except Exception:
                pass

        try:
            child_elements = element.children()
        except Exception:
            child_elements = []
            
        for child in child_elements:
            # 재귀 호출 시 interactive 플래그를 계속 전달
            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path, interactive)
            if child_node:
                node["children"].append(child_node)
        return node
    
    def _reconstruct_path_from_element(self, element):
        """
        [✅ 핵심 수정] .parent()를 이용해 역으로 올라가며 경로를 수동으로 재구성합니다.
        """
        path = []
        current = element
        while current and current != self.main_window.parent():
            try:
                props = self._extract_properties(current)
                path.insert(0, props) # 경로의 맨 앞에 추가 (역순이므로)
                current = current.parent()
            except Exception: break
        return path
        
    # --- 나머지 헬퍼 함수들은 기존과 동일 ---
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

    def _get_element_name(self, element):
        """백엔드에 상관없이 요소의 이름을 반환합니다."""
        if self.backend == 'uia':
            return element.element_info.name
        else: # win32
            return element.window_text()

    def _extract_properties(self, element):
        if self.backend == 'uia':
            # uia 백엔드는 element.element_info 로 접근해야 함
            return self._extract_properties_uia(element.element_info)
        else: # win32
            return self._extract_properties_win32(element)

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
            "auto_id": None, # win32는 auto_id를 지원하지 않음
            "runtime_id": element.handle
        }
