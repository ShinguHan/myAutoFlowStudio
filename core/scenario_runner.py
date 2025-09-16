# -*- coding: utf-8 -*-
"""
이 모듈은 AutoFlow Studio의 심장부(Heart)입니다.
GUI의 시나리오 편집기에서 생성된 데이터(단계 목록)를 입력받아,
이를 해석하고 pywinauto를 통해 실제 UI 조작을 수행합니다.
복잡한 중첩 제어 흐름, 동적 변수 처리, 예외 처리, 결과 리포팅 등
모든 핵심 실행 로직이 여기에 포함됩니다.
"""
import time
import datetime
import os
import csv
import re
import html # HTML 이스케이프를 위해 추가
from pywinauto.application import Application
from pywinauto.timings import TimeoutError
from utils.logger_config import log

# --- 사용자 정의 예외 클래스 ---
# 특정 상황에 맞는 명확한 예외를 정의하여 오류 처리를 용이하게 합니다.
class TargetAppClosedError(Exception):
    """대상 애플리케이션이 닫혔을 때 발생하는 예외."""
    pass

class VariableNotFoundError(Exception):
    """CSV 데이터나 동적 변수 저장소에서 변수를 찾지 못했을 때 발생하는 예외."""
    pass

class ScenarioRunner:
    """
    시나리오 데이터를 해석하고 UI 자동화를 단계별로 실행하는 클래스.
    """
    def __init__(self, app_connector):
        """
        ScenarioRunner 인스턴스를 초기화합니다.

        Args:
            app_connector (AppConnector): 이미 앱에 연결된 AppConnector 인스턴스.
        """
        self.app_connector = app_connector
        if not self.app_connector or not self.app_connector.main_window:
            raise ValueError("A connected AppConnector instance is required.")
        self.main_window = self.app_connector.main_window
        self.results = None  # 테스트 결과 리포팅 데이터를 저장할 딕셔너리
        self.runtime_variables = {}  # 'get_text' 등으로 생성된 동적 변수 저장소

    def run_scenario(self, scenario_steps, data_file_path=None):
        """
        전체 시나리오 실행을 시작하고 관리하는 메인 메서드.
        데이터 기반 테스트인 경우, CSV의 각 행에 대해 시나리오를 반복 실행합니다.

        Args:
            scenario_steps (list): FlowEditor에서 생성된 단계들의 리스트.
            data_file_path (str, optional): 데이터 기반 테스트를 위한 CSV 파일 경로.
        """
        self.runtime_variables.clear()
        self.results = {
            "summary": {
                "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": None, "duration": 0, "total_steps": 0, "passed_steps": 0,
                "failed_steps": 0, "status": "In Progress", "data_iterations": 0
            },
            "steps": []
        }
        start_time = time.time()
        
        try:
            # 데이터 파일이 제공된 경우, 데이터 기반 테스트를 수행합니다.
            if data_file_path and os.path.exists(data_file_path):
                with open(data_file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    data_rows = list(reader)
                    self.results["summary"]["data_iterations"] = len(data_rows)
                    log.info(f"Starting data-driven test with {len(data_rows)} rows from '{data_file_path}'.")
                    for i, row in enumerate(data_rows):
                        log.info(f"--- Iteration {i+1}/{len(data_rows)} with data: {row} ---")
                        self.runtime_variables.clear() # 각 반복마다 동적 변수 초기화
                        self._execute_steps(scenario_steps, data_row=row, iteration_num=i+1)
            else:
                # 단일 실행
                self.results["summary"]["data_iterations"] = 1
                log.info(f"--- Running single scenario with {len(scenario_steps)} steps ---")
                self._execute_steps(scenario_steps)
            
            self.results["summary"]["status"] = "Success"
            log.info("--- Scenario finished successfully ---")
        except Exception as e:
            self.results["summary"]["status"] = "Failure"
            log.error(f"!!! Scenario failed: {e}", exc_info=True)
            raise  # 예외를 상위로 다시 던져 Worker 스레드가 처리하도록 함
        finally:
            # 실행 시간, 결과 요약 등 최종 리포트 정보를 정리합니다.
            end_time = time.time()
            self.results["summary"]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.results["summary"]["duration"] = round(end_time - start_time, 2)
            self.results["summary"]["total_steps"] = len(self.results["steps"])
            self.results["summary"]["passed_steps"] = len([s for s in self.results["steps"] if s["status"] == "success"])
            self.results["summary"]["failed_steps"] = len([s for s in self.results["steps"] if s["status"] == "failure"])

    def _execute_steps(self, steps, data_row=None, iteration_num=1):
        """
        스택 원리를 이용하여 중첩된 제어 흐름을 해석하고 실행하는 핵심 로직.
        프로그램 카운터(pc)를 직접 제어하여 복잡한 흐름을 관리합니다.

        Args:
            steps (list): 실행할 단계 목록.
            data_row (dict, optional): 현재 데이터 기반 테스트 반복의 데이터 행.
            iteration_num (int, optional): 현재 데이터 기반 테스트 반복 횟수.
        """
        pc = 0  # Program Counter
        while pc < len(steps):
            self._check_app_is_alive()
            step = steps[pc]
            
            # --- 실제 액션(Action) 처리 ---
            if step.get("type") == "action":
                self._execute_action(step, data_row, iteration_num)
                pc += 1
                continue

            # --- 제어 흐름(Control Flow) 처리 ---
            if step.get("type") == "control":
                control_type = step.get("control_type")

                if control_type == "start_loop":
                    # 중첩을 고려하여 짝이 맞는 end_loop를 찾고, 그 사이의 body를 반복 실행
                    end_loop_index = self._find_matching_end(steps, pc, "start_loop", "end_loop")
                    loop_body = steps[pc + 1 : end_loop_index]
                    loop_count = step.get("iterations", 1)
                    for i in range(loop_count):
                        self._execute_steps(loop_body, data_row, iteration_num)
                    pc = end_loop_index + 1 # 루프가 끝나면 end_loop 다음으로 점프
                    continue
                
                elif control_type == "if_condition":
                    # 짝이 맞는 else와 end_if를 찾아 조건 결과에 따라 적절한 body를 실행
                    else_index, end_if_index = self._find_else_or_end_if(steps, pc)
                    condition_result = self._check_condition(step.get("condition", {}))
                    if condition_result:
                        if_body = steps[pc + 1 : (else_index if else_index != -1 else end_if_index)]
                        self._execute_steps(if_body, data_row, iteration_num)
                    elif else_index != -1: # else 블록이 존재하면 실행
                        else_body = steps[else_index + 1 : end_if_index]
                        self._execute_steps(else_body, data_row, iteration_num)
                    pc = end_if_index + 1 # IF 블록 전체가 끝나면 end_if 다음으로 점프
                    continue

                elif control_type == "try_catch_start":
                    # try 블록을 실행하고, 예외 발생 시에만 catch 블록을 실행
                    catch_index, end_try_index = self._find_catch_or_end_try(steps, pc)
                    try_body = steps[pc + 1 : (catch_index if catch_index != -1 else end_try_index)]
                    try:
                        log.info("Entering TRY block.")
                        self._execute_steps(try_body, data_row, iteration_num)
                        log.info("TRY block finished successfully.")
                    except Exception as e:
                        log.warning(f"Exception caught in TRY block: {e}. Executing CATCH block.")
                        if catch_index != -1:
                            catch_body = steps[catch_index + 1 : end_try_index]
                            self._execute_steps(catch_body, data_row, iteration_num)
                    pc = end_try_index + 1 # TRY-CATCH 블록이 끝나면 end_try 다음으로 점프
                    continue

                elif control_type == "wait_for_condition":
                    self._execute_wait(step, data_row, iteration_num) # wait는 단일 제어 스텝이므로 pc는 그냥 증가
            
            # 처리되지 않은 스텝(예: end_loop, else 등)은 그냥 건너뜀
            pc += 1

    # --- 이하 헬퍼 및 실제 실행 메서드들 ---

    def _execute_action(self, step, data_row, iteration_num):
        """단일 'action' 스텝을 실행합니다. 재시도, 오류 처리 로직을 포함합니다."""
        start_time = time.time()
        on_error_policy = step.get("onError", {"method": "stop"})
        attempts = on_error_policy.get("retries", 3) if on_error_policy["method"] == "retry" else 1
        
        last_exception = None
        for i in range(attempts):
            try:
                action = step.get("action")
                target = step.get("target")
                params = step.get("params", {})
                
                # 변수 치환
                resolved_target = {k: self._resolve_variables(v, data_row) for k, v in target.items() if v}

                element = self.main_window.child_window(**resolved_target)
                element.wait('exists enabled visible ready', timeout=10)
                
                if action == "click":
                    element.click_input()
                elif action == "double_click":
                    element.double_click_input()
                elif action == "set_text":
                    text_to_set = self._resolve_variables(params.get("text", ""), data_row)
                    element.set_edit_text(text_to_set)
                elif action == "get_text":
                    var_name = params.get("variable_name")
                    if not var_name: raise ValueError("Variable name not set for get_text.")
                    self.runtime_variables[var_name] = element.window_text()
                    log.info(f"Stored text '{self.runtime_variables[var_name]}' into variable '{var_name}'")

                self._record_step_result(step, start_time, "success", iteration_num)
                return
            except Exception as e:
                last_exception = e
                if i < attempts - 1:
                    log.warning(f"Action failed. Retrying ({i+1}/{attempts})... Error: {e}")
                    time.sleep(1)
        
        # 모든 재시도 실패 후
        self._record_step_result(step, start_time, "failure", iteration_num, last_exception)
        if on_error_policy["method"] == "stop":
            raise last_exception
        elif on_error_policy["method"] == "continue":
            log.warning("Error occurred but continuing scenario as per policy.")

    def _execute_wait(self, step, data_row, iteration_num):
        """'wait_for_condition' 스텝을 실행합니다."""
        start_time = time.time()
        try:
            condition = step.get("condition", {})
            target = condition.get("target")
            wait_type = condition.get("type")
            timeout = step.get("params", {}).get("timeout", 10)
            
            resolved_target = {k: self._resolve_variables(v, data_row) for k, v in target.items() if v}
            element = self.main_window.child_window(**resolved_target)

            if wait_type == "element_exists":
                element.wait('exists enabled visible ready', timeout=timeout)
            elif wait_type == "element_vanishes":
                element.wait_not('exists visible', timeout=timeout)
            
            self._record_step_result(step, start_time, "success", iteration_num)
        except Exception as e:
            self._record_step_result(step, start_time, "failure", iteration_num, e)
            raise

    def _check_condition(self, condition):
        """'if_condition'의 조건이 참인지 거짓인지 확인합니다."""
        condition_type = condition.get("type")
        target = condition.get("target")
        resolved_target = {k: self._resolve_variables(v, None) for k, v in target.items() if v}
        
        if condition_type == "element_exists":
            log.info(f"Checking condition: Element '{target.get('title')}' exists?")
            try:
                self.main_window.child_window(**resolved_target).wait('exists', timeout=5)
                log.info("Condition result: True")
                return True
            except Exception:
                log.info("Condition result: False")
                return False
        return False

    def _check_app_is_alive(self):
        """대상 앱이 여전히 활성 상태인지 확인합니다."""
        if not self.main_window or not self.main_window.exists():
            raise TargetAppClosedError("대상 애플리케이션이 닫혔거나 응답하지 않습니다.")

    def _resolve_variables(self, text, data_row):
        """동적 변수와 CSV 변수를 사용하여 텍스트 내 플레이스홀더를 치환합니다."""
        if (data_row is None and not self.runtime_variables) or not isinstance(text, str):
            return text

        def replacer(match):
            key = match.group(1).strip()
            if key in self.runtime_variables:
                return str(self.runtime_variables[key])
            if data_row and key in data_row:
                return str(data_row[key])
            raise VariableNotFoundError(f"동적 변수 또는 CSV 데이터에 '{key}' 변수가 존재하지 않습니다.")

        return re.sub(r"\{\{\s*(.*?)\s*\}\}", replacer, text)

    def _find_matching_end(self, steps, start_index, start_kw, end_kw):
        """중첩을 고려하여 제어 블록의 짝이 맞는 끝을 찾습니다."""
        depth = 1
        for i in range(start_index + 1, len(steps)):
            step = steps[i]
            if step.get("type") == "control":
                control_type = step.get("control_type")
                if control_type == start_kw:
                    depth += 1
                elif control_type == end_kw:
                    depth -= 1
                if depth == 0:
                    return i
        raise SyntaxError(f"Mismatched control block: No matching '{end_kw}' found for '{start_kw}' at index {start_index}")
    
    def _find_else_or_end_if(self, steps, start_index):
        """IF 블록의 ELSE 또는 END IF를 찾습니다."""
        depth = 1
        for i in range(start_index + 1, len(steps)):
            step = steps[i]
            if step.get("type") == "control":
                control_type = step.get("control_type")
                if control_type == "if_condition":
                    depth += 1
                elif control_type == "end_if":
                    depth -= 1
                if depth == 0: return -1, i
                if depth == 1 and control_type == "else":
                    _, end_if_index = self._find_else_or_end_if(steps, i)
                    return i, end_if_index
        raise SyntaxError(f"Mismatched control block: No matching 'end_if' found for 'if_condition' at index {start_index}")

    def _find_catch_or_end_try(self, steps, start_index):
        """TRY 블록의 CATCH 또는 END TRY를 찾습니다."""
        depth = 1
        for i in range(start_index + 1, len(steps)):
            step = steps[i]
            if step.get("type") == "control":
                control_type = step.get("control_type")
                if control_type == "try_catch_start":
                    depth += 1
                elif control_type == "try_catch_end":
                    depth -= 1
                if depth == 0: return -1, i
                if depth == 1 and control_type == "catch_separator":
                    _, end_try_index = self._find_catch_or_end_try(steps, i)
                    return i, end_try_index
        raise SyntaxError(f"Mismatched control block: No matching 'try_catch_end' found for 'try_catch_start' at index {start_index}")

    def _get_step_description(self, step_data):
        """리포팅을 위해 시나리오 데이터로부터 사람이 읽기 쉬운 설명을 생성합니다."""
        description = "Unknown Step"
        step_type = step_data.get("type")
        params = step_data.get("params", {})
        
        if step_type == "action":
            action = step_data.get('action', 'N/A').upper()
            target_title = step_data.get('target', {}).get('title', 'Unknown')
            if action == "SET_TEXT":
                description = f"SET TEXT on '{target_title}' with: \"{params.get('text', '')}\""
            elif action == "GET_TEXT":
                var_name = params.get('variable_name', 'N/A')
                description = f"GET TEXT from '{target_title}' and store in [{var_name}]"
            else:
                description = f"{action}: '{target_title}'"

        elif step_type == "control":
            control = step_data.get("control_type")
            if control == "wait_for_condition":
                 cond = step_data.get("condition", {})
                 target = cond.get("target", {}).get("title", "N/A")
                 wait_type = "appears" if cond.get("type") == "element_exists" else "vanishes"
                 timeout = params.get("timeout", 10)
                 description = f"WAIT for '{target}' to {wait_type} (Timeout: {timeout}s)"
            else: # IF, LOOP, TRY 등은 단순 표시
                description = f"CONTROL: {control.upper()}"
        return description


    def _record_step_result(self, step, start_time, status, iteration_num, details=""):
        """실행 결과를 리포트용 데이터 구조에 기록합니다."""
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        description = self._get_step_description(step)

        self.results["steps"].append({
            "id": step.get("id"),
            "iteration": iteration_num,
            "description": html.escape(description),
            "status": status, 
            "duration": duration, 
            "details": html.escape(str(details))
        })
    
    def generate_html_report(self, report_dir="reports"):
        """HTML 결과 보고서를 생성합니다."""
        if not self.results:
            return None
        
        os.makedirs(report_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"report_{timestamp}.html")

        summary = self.results["summary"]
        status_color = "green" if summary["status"] == "Success" else "red"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>AutoFlow Studio - Test Automation Report</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 40px; background-color: #f9f9f9; color: #333; }}
                    .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 8px; }}
                    h1, h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                    h1 {{ font-size: 2em; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #f2f2f2; font-weight: 600; }}
                    .summary {{ background-color: #f8f8f8; padding: 20px; border-radius: 5px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; }}
                    .summary p {{ margin: 5px 0; }}
                    .status-success {{ color: #28a745; font-weight: bold; }}
                    .status-failure {{ color: #dc3545; font-weight: bold; }}
                    .status-inprogress {{ color: #007bff; font-weight: bold; }}
                    .details-col {{ white-space: pre-wrap; word-wrap: break-word; max-width: 400px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Test Automation Report</h1>
                    <div class="summary">
                        <p><strong>Start Time:</strong> {summary['start_time']}</p>
                        <p><strong>Total Steps Executed:</strong> {summary['total_steps']}</p>
                        <p><strong>Duration:</strong> {summary['duration']}s</p>
                        <p><strong>Passed / Failed:</strong> {summary['passed_steps']} / {summary['failed_steps']}</p>
                        <p><strong>Data Iterations:</strong> {summary['data_iterations']}</p>
                        <p><strong>Overall Status:</strong> <span class="status-{summary['status'].lower()}">{summary['status']}</span></p>
                    </div>
                    <h2>Details</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Iteration</th>
                                <th>Description</th>
                                <th>Status</th>
                                <th>Duration (s)</th>
                                <th class="details-col">Details</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for i, step in enumerate(self.results["steps"]):
            html_content += f"""
                            <tr>
                                <td>{i+1}</td>
                                <td>{step['iteration']}</td>
                                <td>{step['description']}</td>
                                <td><span class="status-{step['status'].lower()}">{step['status']}</span></td>
                                <td>{step['duration']}</td>
                                <td class="details-col">{step['details']}</td>
                            </tr>
            """
        html_content += """
                        </tbody>
                    </table>
                </div>
            </body>
        </html>
        """
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            log.info(f"HTML report generated at: {report_path}")
            return os.path.abspath(report_path)
        except Exception as e:
            log.error(f"Failed to generate HTML report: {e}")
            return None

