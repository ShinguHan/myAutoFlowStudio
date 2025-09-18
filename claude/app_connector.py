# core/app_connector.py - 개선된 버전

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
    개선된 Windows 애플리케이션 연결 클래스
    - 다중 백엔드 지원
    - 강화된 연결 안정성
    - 더 나은 오류 처리
    """
    def __init__(self):
        self.app = None
        self.main_window = None
        self.backend = None  # 성공한 백엔드 저장
        self.connection_method = None  # 성공한 연결 방법 저장
        os.makedirs(CACHE_DIR, exist_ok=True)

    def connect_to_app(self, title_re, preferred_backend="uia"):
        """
        개선된 앱 연결 메서드
        - 여러 백엔드 시도
        - 다양한 연결 방법 시도
        """
        log.info(f"Connecting to application with title_re='{title_re}'")
        
        # 1. 먼저 해당 앱의 창들을 찾아보기
        available_windows = self._find_matching_windows(title_re)
        if not available_windows:
            log.error(f"No windows found matching pattern: {title_re}")
            return False
        
        log.info(f"Found {len(available_windows)} matching windows:")
        for i, window in enumerate(available_windows):
            log.info(f"  {i+1}. '{window.name}' (Class: {window.class_name})")
        
        # 2. 다양한 방법으로 연결 시도
        connection_strategies = self._get_connection_strategies(title_re, available_windows)
        
        for strategy in connection_strategies:
            try:
                log.info(f"Trying {strategy['name']}...")
                
                self.app = Application(backend=strategy['backend']).connect(**strategy['params'])
                self.main_window = self.app.top_window()
                self.backend = strategy['backend']
                self.connection_method = strategy['name']
                
                # 연결 검증
                window_title = self.main_window.window_text()
                log.info(f"✅ Successfully connected using {strategy['name']}")
                log.info(f"   Backend: {self.backend}")
                log.info(f"   Window: '{window_title}'")
                
                return True
                
            except Exception as e:
                log.warning(f"❌ {strategy['name']} failed: {e}")
                continue
        
        log.error("All connection strategies failed")
        self.app = None
        self.main_window = None
        return False

    def _find_matching_windows(self, title_re):
        """정규식에 맞는 창들을 찾기"""
        try:
            compiled_pattern = re.compile(title_re, re.IGNORECASE)
            all_windows = findwindows.find_elements()
            
            matching_windows = []
            for window in all_windows:
                if compiled_pattern.search(window.name):
                    matching_windows.append(window)
            
            return matching_windows
        except Exception as e:
            log.error(f"Error finding windows: {e}")
            return []

    def _get_connection_strategies(self, title_re, available_windows):
        """연결 전략들을 우선순위 순으로 반환"""
        compiled_pattern = re.compile(title_re, re.IGNORECASE)
        strategies = []
        
        # 백엔드별 전략
        backends = ["uia", "win32"]
        
        for backend in backends:
            # 1. 정규식으로 연결
            strategies.append({
                "name": f"{backend} + title_re",
                "backend": backend,
                "params": {"title_re": compiled_pattern}
            })
            
            # 2. 정확한 제목으로 연결 (사용 가능한 창이 있는 경우)
            for window in available_windows[:3]:  # 최대 3개까지만
                strategies.append({
                    "name": f"{backend} + exact_title",
                    "backend": backend,
                    "params": {"title": window.name}
                })
            
            # 3. 클래스명으로 연결 (고유한 클래스명이 있는 경우)
            unique_classes = list(set([w.class_name for w in available_windows if w.class_name]))
            for class_name in unique_classes[:2]:  # 최대 2개까지
                strategies.append({
                    "name": f"{backend} + class_name",
                    "backend": backend,  
                    "params": {"class_name": class_name}
                })
        
        return strategies

    def get_ui_tree(self, max_depth=20):
        """UI 트리 구조 반환 (캐시 기능 포함)"""
        if not self.main_window:
            log.warning("Cannot get UI tree because no application is connected.")
            return None
        
        try:
            log.info(f"Building UI tree (backend: {self.backend}, max_depth: {max_depth})")
            
            # 창을 앞으로 가져오기
            try:
                self.main_window.set_focus()
                time.sleep(0.5)  # UI가 안정화될 시간 제공
            except Exception as e:
                log.warning(f"Could not set focus: {e}")
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
                log.info("✅ UI tree structure has been saved to cache.")
            
            return ui_tree
            
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None

    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        """재귀적 UI 트리 구축 (개선된 안정성)"""
        if path is None:
            path = []

        if not element or current_depth > max_depth:
            return None

        try:
            element_props = self._extract_properties(element.element_info)
        except Exception as e:
            log.warning(f"Could not extract properties at depth {current_depth}: {e}")
            return None

        current_path = path + [element_props]

        node = {
            "properties": element_props,
            "path": current_path,
            "children": []
        }

        try:
            child_elements = element.children()
        except Exception as e:
            log.debug(f"Could not get children at depth {current_depth}: {e}")
            child_elements = []

        # TabItem 처리 (개선된 로직)
        tab_items = [child for child in child_elements 
                    if hasattr(child, 'element_info') and 
                       child.element_info.control_type == 'TabItem']

        if tab_items:
            log.debug(f"Processing {len(tab_items)} TabItems")
            self._process_tab_items(element, tab_items, node, current_depth, max_depth, current_path)
        else:
            # 일반적인 자식 요소 처리
            for child in child_elements:
                try:
                    child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
                    if child_node:
                        node["children"].append(child_node)
                except Exception as e:
                    log.debug(f"Failed to process child at depth {current_depth + 1}: {e}")

        return node

    def _process_tab_items(self, parent_element, tab_items, parent_node, current_depth, max_depth, current_path):
        """TabItem 요소들을 안전하게 처리"""
        processed_child_ids = set()
        original_selected_tab = None
        
        # 현재 선택된 탭 확인
        try:
            for tab in tab_items:
                if tab.is_selected():
                    original_selected_tab = tab
                    break
        except Exception as e:
            log.debug(f"Could not determine original selected tab: {e}")

        for i, tab_item in enumerate(tab_items):
            try:
                tab_name = tab_item.element_info.name
                log.debug(f"Processing TabItem {i+1}/{len(tab_items)}: '{tab_name}'")
                
                # 탭 선택
                if not tab_item.is_selected():
                    tab_item.select()
                    time.sleep(0.3)  # 탭 전환 대기
                
                # 새로운 자식 요소들 탐색
                try:
                    refreshed_children = parent_element.children()
                    for child in refreshed_children:
                        try:
                            child_id = child.element_info.runtime_id
                            if child_id not in processed_child_ids:
                                processed_child_ids.add(child_id)
                                child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
                                if child_node:
                                    parent_node["children"].append(child_node)
                        except Exception as e:
                            log.debug(f"Failed to process tab child: {e}")
                            continue
                            
                except Exception as e:
                    log.debug(f"Failed to get refreshed children for tab '{tab_name}': {e}")
                    
            except Exception as e:
                log.warning(f"Failed to process TabItem: {e}")
                continue
        
        # 원래 선택된 탭으로 복원 시도
        if original_selected_tab:
            try:
                original_selected_tab.select()
                time.sleep(0.2)
            except Exception as e:
                log.debug(f"Could not restore original tab selection: {e}")

    def _extract_properties(self, element_info):
        """요소 속성 추출 (더 안전한 버전)"""
        props = {}
        
        try:
            props["title"] = getattr(element_info, 'name', '') or ''
        except:
            props["title"] = ''
            
        try:
            props["control_type"] = getattr(element_info, 'control_type', '') or ''
        except:
            props["control_type"] = ''
            
        try:
            props["auto_id"] = getattr(element_info, 'automation_id', '') or ''
        except:
            props["auto_id"] = ''
            
        try:
            props["runtime_id"] = getattr(element_info, 'runtime_id', '') or ''
        except:
            props["runtime_id"] = ''
        
        return props

    def _get_cache_path(self):
        """캐시 파일 경로 생성"""
        if not self.main_window:
            return None
        
        try:
            window_text = self.main_window.window_text()
            safe_filename = re.sub(r'[\\/*?:"<>|]', "", window_text)
            title_hash = hashlib.md5(window_text.encode()).hexdigest()
            backend_suffix = f"_{self.backend}" if self.backend else ""
            
            return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}{backend_suffix}.json")
        except Exception as e:
            log.error(f"Failed to generate cache path: {e}")
            return None

    def has_cache(self):
        """캐시 파일 존재 여부 확인"""
        cache_path = self._get_cache_path()
        return cache_path and os.path.exists(cache_path)

    def _save_tree_to_cache(self, ui_tree):
        """UI 트리를 캐시에 저장"""
        cache_path = self._get_cache_path()
        if not cache_path:
            return

        try:
            # 메타데이터 추가
            cache_data = {
                "metadata": {
                    "backend": self.backend,
                    "connection_method": self.connection_method,
                    "timestamp": time.time(),
                    "window_title": self.main_window.window_text() if self.main_window else "Unknown"
                },
                "ui_tree": ui_tree
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
            log.info(f"UI tree cached to: {cache_path}")
            
        except Exception as e:
            log.error(f"Failed to save UI tree to cache: {e}")

    def load_tree_from_cache(self):
        """캐시에서 UI 트리 로드"""
        if not self.has_cache():
            log.info("No cache file found")
            return None
        
        cache_path = self._get_cache_path()
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # 메타데이터 로그
            if "metadata" in cache_data:
                metadata = cache_data["metadata"]
                log.info(f"Loading cached UI tree:")
                log.info(f"  Backend: {metadata.get('backend', 'Unknown')}")
                log.info(f"  Method: {metadata.get('connection_method', 'Unknown')}")
                log.info(f"  Window: {metadata.get('window_title', 'Unknown')}")
            
            return cache_data.get("ui_tree", cache_data)  # 하위 호환성
            
        except Exception as e:
            log.error(f"Failed to load UI tree from cache: {e}")
            return None

    def get_connection_info(self):
        """연결 정보 반환"""
        if not self.main_window:
            return None
            
        return {
            "backend": self.backend,
            "connection_method": self.connection_method,
            "window_title": self.main_window.window_text(),
            "window_class": self.main_window.class_name(),
            "is_connected": self.main_window.exists()
        }