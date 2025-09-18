# -*- coding: utf-8 -*-
"""
수정된 ScenarioRunner - pywinauto 안정성 문제 해결
"""
import time
import datetime
import os
import csv
import re
import html
from pywinauto.application import Application
from pywinauto import findwindows
from pywinauto.timings import TimeoutError
from pywinauto.findwindows import ElementNotFoundError
from utils.logger_config import log

class ScenarioRunner:
    def __init__(self, app_connector):
        self.app_connector = app_connector
        if not self.app_connector or not self.app_connector.main_window:
            raise ValueError("A connected AppConnector instance is required.")
        self.main_window = self.app_connector.main_window
        self.results = None
        self.runtime_variables = {}

    def _find_element_dynamically(self, path):
        """
        개선된 동적 요소 찾기 메서드
        - 더 강력한 예외 처리
        - 백엔드별 다른 접근 방식
        - 재시도 로직 추가
        """
        log.debug(f"Starting dynamic element search with path of length {len(path)}")
        current_element = self.main_window
        
        # 앱이 여전히 살아있는지 확인
        if not current_element.exists():
            raise Exception("Main window no longer exists")

        # 경로의 마지막 요소를 제외한 부모 요소들을 먼저 순회
        for i, parent_props in enumerate(path[:-1]):
            current_element = self._find_single_element(current_element, parent_props, f"parent_{i}")

        # 최종 타겟 요소 찾기
        final_target_props = path[-1]
        return self._find_single_element(current_element, final_target_props, "target")

    def _find_single_element(self, parent_element, props, element_type="element"):
        """
        단일 요소를 찾는 헬퍼 메서드 (재시도 로직 포함)
        """
        search_criteria = self._build_search_criteria(props)
        
        if not search_criteria:
            raise ValueError(f"{element_type} has no valid identifiers: {props}")

        # 여러 방법으로 요소 찾기 시도
        methods = [
            lambda: self._find_with_criteria(parent_element, search_criteria),
            lambda: self._find_with_fallback_criteria(parent_element, props),
            lambda: self._find_with_index_fallback(parent_element, props)
        ]

        last_exception = None
        for i, method in enumerate(methods):
            try:
                log.debug(f"Attempting method {i+1} for {element_type}: {search_criteria}")
                element = method()
                
                # TabItem인 경우 선택
                if props.get("control_type") == "TabItem" and hasattr(element, 'is_selected'):
                    if not element.is_selected():
                        log.info(f"Selecting TabItem '{props.get('title')}'")
                        element.select()
                        time.sleep(0.5)
                
                return element
                
            except Exception as e:
                last_exception = e
                log.debug(f"Method {i+1} failed for {element_type}: {e}")
                continue

        # 모든 방법이 실패한 경우
        log.error(f"Could not find {element_type} with properties: {props}")
        raise last_exception or ElementNotFoundError(f"Element not found: {props}")

    def _build_search_criteria(self, props):
        """검색 조건 구성"""
        search_criteria = {}
        
        # 우선순위: auto_id > control_type + title > title > control_type
        auto_id = props.get("auto_id")
        control_type = props.get("control_type")  
        title = props.get("title")

        if auto_id and auto_id.strip():
            search_criteria["auto_id"] = auto_id.strip()
        
        if control_type and control_type.strip():
            search_criteria["control_type"] = control_type.strip()
            
        if title and title.strip():
            search_criteria["title"] = title.strip()

        return search_criteria

    def _find_with_criteria(self, parent_element, criteria):
        """기본 검색 조건으로 요소 찾기"""
        element = parent_element.child_window(**criteria)
        element.wait('exists', timeout=10)
        return element

    def _find_with_fallback_criteria(self, parent_element, props):
        """대안 검색 조건으로 요소 찾기"""
        title = props.get("title", "").strip()
        control_type = props.get("control_type", "").strip()
        
        if not title:
            raise ElementNotFoundError("No fallback criteria available")
            
        # title만으로 시도
        fallback_criteria = {"title": title}
        element = parent_element.child_window(**fallback_criteria)
        element.wait('exists', timeout=5)
        return element

    def _find_with_index_fallback(self, parent_element, props):
        """인덱스 기반 폴백 (마지막 수단)"""
        control_type = props.get("control_type", "").strip()
        
        if not control_type:
            raise ElementNotFoundError("No control_type for index fallback")
            
        # 같은 타입의 모든 요소 찾기
        elements = parent_element.children()
        matching_elements = [
            elem for elem in elements 
            if hasattr(elem.element_info, 'control_type') and 
               elem.element_info.control_type == control_type
        ]
        
        if not matching_elements:
            raise ElementNotFoundError(f"No elements of type {control_type} found")
            
        # 첫 번째 매칭 요소 반환
        return matching_elements[0]

    def _execute_action(self, step, data_row, iteration_num):
        """개선된 액션 실행 메서드"""
        start_time = time.time()
        on_error_policy = step.get("onError", {"method": "stop"})
        attempts = on_error_policy.get("retries", 3) if on_error_policy["method"] == "retry" else 1
        
        last_exception = None
        for i in range(attempts):
            try:
                action = step.get("action")
                path = step.get("path", [])
                params = step.get("params", {})
                
                if not path:
                    raise ValueError("Element path is missing in the scenario step.")
                
                log.info(f"Executing {action} on element (attempt {i+1}/{attempts})")
                
                # 요소 찾기
                element = self._find_element_dynamically(path)
                
                # 요소가 준비될 때까지 대기 (더 관대한 조건)
                try:
                    element.wait('exists', timeout=10)
                    if hasattr(element, 'is_enabled') and callable(element.is_enabled):
                        if not element.is_enabled():
                            log.warning("Element exists but is not enabled")
                    time.sleep(0.2)  # 안정성을 위한 추가 대기
                except Exception as wait_error:
                    log.warning(f"Wait condition failed: {wait_error}")
                
                # 액션 실행
                if action == "click":
                    self._safe_click(element)
                elif action == "double_click":
                    self._safe_double_click(element)
                elif action == "set_text":
                    text_to_set = self._resolve_variables(params.get("text", ""), data_row)
                    self._safe_set_text(element, text_to_set)
                elif action == "get_text":
                    var_name = params.get("variable_name")
                    if not var_name:
                        raise ValueError("Variable name not set for get_text.")
                    text_value = self._safe_get_text(element)
                    self.runtime_variables[var_name] = text_value
                    log.info(f"Stored text '{text_value}' into variable '{var_name}'")
                else:
                    raise ValueError(f"Unsupported action: {action}")

                self._record_step_result(step, start_time, "success", iteration_num)
                return
                
            except Exception as e:
                last_exception = e
                log.warning(f"Action failed (attempt {i+1}/{attempts}): {e}")
                if i < attempts - 1:
                    time.sleep(2)  # 재시도 전 대기 시간 증가
        
        # 모든 재시도 실패
        self._record_step_result(step, start_time, "failure", iteration_num, last_exception)
        if on_error_policy["method"] == "stop":
            raise last_exception
        elif on_error_policy["method"] == "continue":
            log.warning("Error occurred but continuing scenario as per policy.")

    def _safe_click(self, element):
        """안전한 클릭 실행"""
        methods = [
            ("click_input", lambda: element.click_input()),
            ("click", lambda: element.click()),
            ("left_click", lambda: element.left_click()),
        ]
        
        for method_name, method_func in methods:
            try:
                log.debug(f"Trying click method: {method_name}")
                method_func()
                log.debug(f"Click successful with {method_name}")
                return
            except Exception as e:
                log.debug(f"Click method {method_name} failed: {e}")
                continue
        
        raise Exception("All click methods failed")

    def _safe_double_click(self, element):
        """안전한 더블클릭 실행"""
        methods = [
            ("double_click_input", lambda: element.double_click_input()),
            ("double_click", lambda: element.double_click()),
        ]
        
        for method_name, method_func in methods:
            try:
                log.debug(f"Trying double-click method: {method_name}")
                method_func()
                log.debug(f"Double-click successful with {method_name}")
                return
            except Exception as e:
                log.debug(f"Double-click method {method_name} failed: {e}")
                continue
        
        raise Exception("All double-click methods failed")

    def _safe_set_text(self, element, text):
        """안전한 텍스트 입력"""
        methods = [
            ("set_edit_text", lambda: element.set_edit_text(text)),
            ("set_text", lambda: element.set_text(text)),
            ("type_keys", lambda: self._type_keys_method(element, text)),
            ("send_chars", lambda: element.send_chars(text)),
        ]
        
        for method_name, method_func in methods:
            try:
                log.debug(f"Trying text input method: {method_name}")
                method_func()
                log.debug(f"Text input successful with {method_name}")
                return
            except Exception as e:
                log.debug(f"Text input method {method_name} failed: {e}")
                continue
        
        raise Exception("All text input methods failed")

    def _type_keys_method(self, element, text):
        """type_keys를 사용한 텍스트 입력"""
        element.set_focus()
        time.sleep(0.1)
        # 기존 텍스트 선택 후 삭제
        element.type_keys("^a")  # Ctrl+A
        time.sleep(0.1)
        element.type_keys(text)

    def _safe_get_text(self, element):
        """안전한 텍스트 가져오기"""
        methods = [
            ("window_text", lambda: element.window_text()),
            ("get_value", lambda: element.get_value()),
            ("texts", lambda: " ".join(element.texts()) if element.texts() else ""),
        ]
        
        for method_name, method_func in methods:
            try:
                log.debug(f"Trying get text method: {method_name}")
                result = method_func()
                if result is not None:
                    log.debug(f"Get text successful with {method_name}: '{result}'")
                    return result
            except Exception as e:
                log.debug(f"Get text method {method_name} failed: {e}")
                continue
        
        log.warning("All get text methods failed, returning empty string")
        return ""

    def _check_app_is_alive(self):
        """앱 생존 확인 (더 강력한 검사)"""
        try:
            if not self.main_window or not self.main_window.exists():
                raise Exception("Main window no longer exists")
            
            # 추가로 창이 응답하는지 확인
            self.main_window.window_text()  # 간단한 조작으로 응답성 확인
            
        except Exception as e:
            raise Exception(f"대상 애플리케이션이 닫혔거나 응답하지 않습니다: {e}")

    def _resolve_variables(self, text, data_row):
        """변수 해결 (기존 코드와 동일)"""
        if (data_row is None and not self.runtime_variables) or not isinstance(text, str):
            return text

        def replacer(match):
            key = match.group(1).strip()
            if key in self.runtime_variables:
                return str(self.runtime_variables[key])
            if data_row and key in data_row:
                return str(data_row[key])
            raise Exception(f"변수 '{key}'를 찾을 수 없습니다.")

        return re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, text)

    # 나머지 메서드들은 기존과 동일...
    def run_scenario(self, scenario_steps, data_file_path=None):
        """기존 run_scenario 메서드와 동일"""
        # ... (기존 코드 유지)
        pass

    def _record_step_result(self, step, start_time, status, iteration_num, details=""):
        """기존 _record_step_result 메서드와 동일"""  
        # ... (기존 코드 유지)
        pass