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
        os.makedirs(CACHE_DIR, exist_ok=True)

    def connect_to_app(self, title_re):
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
            log.info(f"Bringing window to front and building UI tree recursively (max_depth={max_depth})...")
            self.main_window.set_focus()
            
            ui_tree = self._build_tree_recursively(self.main_window, 0, max_depth)
            
            if ui_tree:
                self._save_tree_to_cache(ui_tree)
                log.info("UI tree structure has been saved to cache.")

            return ui_tree
        except Exception as e:
            log.error(f"An error occurred while building the UI tree: {e}", exc_info=True)
            return None


    def refresh_subtree(self, path, max_depth=5):
        if not self.main_window:
            log.warning("Cannot refresh subtree. No application is connected.")
            return None
        
        try:
            target_spec = self.main_window
            for props in path[1:]:
                search_criteria = {k: v for k, v in props.items() if k != 'runtime_id'}
                search_criteria = {k: v for k, v in search_criteria.items() if v}

                if not search_criteria:
                    raise ValueError(f"Invalid path segment with no valid properties: {props}")
                
                target_spec = target_spec.child_window(**search_criteria)
            
            target_element = target_spec.wrapper_object()
            
            log.info(f"Found element '{target_element.element_info.name}'. Rebuilding its subtree.")
            
            # ✅ *** 핵심 수정: .is_invokeable() -> .has_pattern('invoke') ***
            if target_element.is_pattern_supported('invoke'):
                log.debug(f"Invoking '{target_element.element_info.name}' to reveal children...")
                target_element.invoke()
                time.sleep(0.5)
            
            children_nodes = []
            for child in target_element.children():
                node = self._build_tree_recursively(child, 0, max_depth, path)
                if node:
                    children_nodes.append(node)
            
            return children_nodes

        except findwindows.ElementNotFoundError:
             log.error("Refresh failed: Target element not found via path traversal.")
             return None
        except Exception as e:
            log.error(f"An error occurred while refreshing the subtree: {e}", exc_info=True)
            return None

    def _get_cache_path(self):
        if not self.main_window:
            return None
        
        window_text = self.main_window.window_text()
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", window_text)
        title_hash = hashlib.md5(window_text.encode()).hexdigest()
        
        return os.path.join(CACHE_DIR, f"ui_tree_cache_{safe_filename[:50]}_{title_hash}.json")

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
            log.error(f"Failed to save UI tree to cache file '{cache_path}': {e}")
    
    def load_tree_from_cache(self):
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
    


    def _build_tree_recursively(self, element, current_depth, max_depth, path=None):
        if path is None: path = []
        if not element or current_depth > max_depth: return None

        element_props = self._extract_properties(element.element_info)
        current_path = path + [element_props]
        node = { "properties": element_props, "path": current_path, "children": [] }

        try:
            child_elements = element.children()
        except Exception:
            child_elements = []

        interactive_items = []
        static_items = []

        for child in child_elements:
            try:
                # ✅ *** 핵심 수정: .is_invokeable() -> .has_pattern('invoke') ***
                if child.is_pattern_supported('invoke'):
                    interactive_items.append(child)
                else:
                    static_items.append(child)
            except Exception:
                static_items.append(child)

        for child in static_items:
            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
            if child_node:
                node["children"].append(child_node)

        if interactive_items:
            log.debug(f"Interactive container found: '{element.element_info.name}'. Iterating through {len(interactive_items)} items.")
            processed_child_ids = set(c.element_info.runtime_id for c in child_elements)

            for item in interactive_items:
                try:
                    item_type = item.element_info.control_type
                    log.debug(f"Interacting with {item_type}: '{item.element_info.name}'")
                    
                    item.invoke()
                    time.sleep(0.5)

                    refreshed_children = element.children()
                    
                    for child in refreshed_children:
                        child_id = child.element_info.runtime_id
                        if child_id not in processed_child_ids:
                            processed_child_ids.add(child_id)
                            child_node = self._build_tree_recursively(child, current_depth + 1, max_depth, current_path)
                            if child_node:
                                node["children"].append(child_node)
                except Exception as e:
                    log.warning(f"Failed to process interactive item '{item.element_info.name}': {e}")
        
        return node


    def _extract_properties(self, element_info):
        return {
            "title": element_info.name,
            "class_name": element_info.class_name,
            "control_type": element_info.control_type,
            "auto_id": element_info.automation_id,
            "runtime_id": element_info.runtime_id
        }

