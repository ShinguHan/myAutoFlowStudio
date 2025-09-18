# main_runner.py - 개선된 시나리오 실행
"""
개선된 메인 실행 스크립트
- 연결 안정성 향상
- 더 나은 오류 진단
- 단계별 검증
"""

import os
import sys
import time
import json
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from core.app_connector import AppConnector
    from core.scenario_runner import ScenarioRunner
    from utils.logger_config import log
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("프로젝트 구조를 확인하고 필요한 모듈들이 있는지 확인해주세요.")
    sys.exit(1)

class ImprovedMainRunner:
    """개선된 메인 실행 클래스"""
    
    def __init__(self):
        self.connector = None
        self.runner = None
    
    def run_notepad_test(self):
        """메모장으로 간단한 테스트 실행"""
        print("🚀 메모장 테스트 시나리오 시작")
        
        # 1. 메모장 실행
        if not self._launch_notepad():
            return False
        
        # 2. 앱 연결
        if not self._connect_to_notepad():
            return False
        
        # 3. 간단한 시나리오 실행
        if not self._run_simple_scenario():
            return False
        
        print("✅ 메모장 테스트 완료!")
        return True
    
    def _launch_notepad(self):
        """메모장 실행"""
        try:
            print("📝 메모장 실행 중...")
            import subprocess
            subprocess.Popen(["notepad.exe"])
            time.sleep(3)
            print("✅ 메모장 실행됨")
            return True
        except Exception as e:
            print(f"❌ 메모장 실행 실패: {e}")
            return False
    
    def _connect_to_notepad(self):
        """메모장에 연결"""
        try:
            print("🔗 메모장에 연결 중...")
            self.connector = AppConnector()
            
            if self.connector.connect_to_app(r".*메모장|.*Notepad"):
                print("✅ 메모장 연결 성공!")
                
                # 연결 정보 출력
                conn_info = self.connector.get_connection_info()
                print(f"   백엔드: {conn_info['backend']}")
                print(f"   연결방법: {conn_info['connection_method']}")
                print(f"   창 제목: '{conn_info['window_title']}'")
                
                return True
            else:
                print("❌ 메모장 연결 실패")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류: {e}")
            return False
    
    def _run_simple_scenario(self):
        """간단한 시나리오 실행"""
        try:
            print("📋 간단한 시나리오 실행 중...")
            
            # ScenarioRunner 생성
            self.runner = ScenarioRunner(self.connector)
            
            # UI 트리 구축 (캐시 확인)
            print("🌳 UI 트리 분석 중...")
            if self.connector.has_cache():
                print("💾 캐시된 UI 트리 사용")
                ui_tree = self.connector.load_tree_from_cache()
            else:
                print("🔍 새로운 UI 트리 구축")
                ui_tree = self.connector.get_ui_tree(max_depth=5)
            
            if not ui_tree:
                print("❌ UI 트리 구축 실패")
                return False
            
            # 텍스트 입력 요소 찾기
            text_element_path = self._find_text_element_path(ui_tree)
            if not text_element_path:
                print("❌ 텍스트 입력 요소를 찾을 수 없음")
                return False
            
            print(f"📝 텍스트 요소 경로 찾음: {len(text_element_path)} 단계")
            
            # 간단한 시나리오 정의
            simple_scenario = [
                {
                    "id": "step1",
                    "type": "action",
                    "action": "set_text",
                    "path": text_element_path,
                    "params": {"text": "pywinauto 테스트 성공!"},
                    "onError": {"method": "stop"}
                },
                {
                    "id": "step2", 
                    "type": "action",
                    "action": "get_text",
                    "path": text_element_path,
                    "params": {"variable_name": "result_text"},
                    "onError": {"method": "continue"}
                }
            ]
            
            # 시나리오 실행
            print("▶️ 시나리오 실행...")
            self.runner.run_scenario(simple_scenario)
            
            # 결과 확인
            if self.runner.runtime_variables.get("result_text"):
                print(f"✅ 텍스트 확인됨: '{self.runner.runtime_variables['result_text']}'")
            
            # 결과 리포트 생성
            report_path = self.runner.generate_html_report()
            if report_path:
                print(f"📊 리포트 생성됨: {report_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ 시나리오 실행 실패: {e}")
            log.error(f"Scenario execution failed: {e}", exc_info=True)
            return False
    
    def _find_text_element_path(self, ui_tree):
        """UI 트리에서 텍스트 입력 요소의 경로 찾기"""
        def search_recursive(node, current_path=[]):
            current_props = node.get("properties", {})
            control_type = current_props.get("control_type", "")
            
            # 메모장의 텍스트 영역 찾기
            if control_type in ["Document", "Edit"]:
                # 빈 제목이거나 "텍스트 편집기" 같은 경우
                title = current_props.get("title", "").strip()
                if not title or "편집" in title or "Document" in control_type:
                    return current_path + [current_props]
            
            # 자식 노드들 탐색
            for child in node.get("children", []):
                result = search_recursive(child, current_path + [current_props])
                if result:
                    return result
            
            return None
        
        return search_recursive(ui_tree)
    
    def run_custom_scenario(self, scenario_file_path, data_file_path=None):
        """사용자 정의 시나리오 실행"""
        try:
            print(f"📋 시나리오 파일 로드: {scenario_file_path}")
            
            # 시나리오 파일 로드
            with open(scenario_file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            
            scenario_steps = scenario_data.get("steps", [])
            if not scenario_steps:
                print("❌ 시나리오 단계가 없습니다.")
                return False
            
            print(f"📝 {len(scenario_steps)}개 단계를 실행합니다.")
            
            # 데이터 파일 확인
            if data_file_path and os.path.exists(data_file_path):
                print(f"📊 데이터 파일 사용: {data_file_path}")
            
            # ScenarioRunner로 실행
            if not self.runner:
                print("❌ ScenarioRunner가 초기화되지 않았습니다. 먼저 앱에 연결하세요.")
                return False
            
            self.runner.run_scenario(scenario_steps, data_file_path)
            
            # 결과 리포트 생성
            report_path = self.runner.generate_html_report()
            if report_path:
                print(f"📊 실행 결과 리포트: {report_path}")
            
            return True
            
        except FileNotFoundError:
            print(f"❌ 시나리오 파일을 찾을 수 없습니다: {scenario_file_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ 시나리오 파일 형식 오류: {e}")
            return False
        except Exception as e:
            print(f"❌ 시나리오 실행 실패: {e}")
            log.error(f"Custom scenario execution failed: {e}", exc_info=True)
            return False
    
    def connect_to_custom_app(self, title_pattern):
        """사용자 지정 애플리케이션에 연결"""
        try:
            print(f"🔗 애플리케이션 연결 시도: {title_pattern}")
            
            self.connector = AppConnector()
            
            if self.connector.connect_to_app(title_pattern):
                print("✅ 애플리케이션 연결 성공!")
                
                # 연결 정보 출력
                conn_info = self.connector.get_connection_info()
                print(f"   백엔드: {conn_info['backend']}")
                print(f"   연결방법: {conn_info['connection_method']}")
                print(f"   창 제목: '{conn_info['window_title']}'")
                
                # ScenarioRunner 초기화
                self.runner = ScenarioRunner(self.connector)
                
                return True
            else:
                print("❌ 애플리케이션 연결 실패")
                return False
                
        except Exception as e:
            print(f"❌ 연결 중 오류: {e}")
            log.error(f"Connection failed: {e}", exc_info=True)
            return False
    
    def analyze_ui_structure(self, max_depth=10):
        """UI 구조 분석 및 저장"""
        if not self.connector:
            print("❌ 먼저 애플리케이션에 연결하세요.")
            return False
        
        try:
            print("🔍 UI 구조 분석 중...")
            ui_tree = self.connector.get_ui_tree(max_depth)
            
            if ui_tree:
                # UI 구조를 파일로 저장
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = f"ui_analysis_{timestamp}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(ui_tree, f, ensure_ascii=False, indent=2)
                
                print(f"✅ UI 구조 분석 완료: {output_file}")
                
                # 간단한 통계 출력
                self._print_ui_statistics(ui_tree)
                
                return True
            else:
                print("❌ UI 구조 분석 실패")
                return False
                
        except Exception as e:
            print(f"❌ UI 분석 중 오류: {e}")
            log.error(f"UI analysis failed: {e}", exc_info=True)
            return False
    
    def _print_ui_statistics(self, ui_tree):
        """UI 트리 통계 출력"""
        def count_nodes(node):
            count = 1
            for child in node.get("children", []):
                count += count_nodes(child)
            return count
        
        def get_control_types(node, types_set):
            props = node.get("properties", {})
            control_type = props.get("control_type")
            if control_type:
                types_set.add(control_type)
            
            for child in node.get("children", []):
                get_control_types(child, types_set)
        
        total_nodes = count_nodes(ui_tree)
        control_types = set()
        get_control_types(ui_tree, control_types)
        
        print(f"📊 UI 구조 통계:")
        print(f"   총 노드 수: {total_nodes}")
        print(f"   컨트롤 타입 수: {len(control_types)}")
        print(f"   컨트롤 타입들: {', '.join(sorted(control_types))}")


def print_usage():
    """사용법 출력"""
    print("""
🔧 개선된 pywinauto 실행기 사용법

기본 명령어:
  python main_runner.py test-notepad          # 메모장으로 간단한 테스트
  python main_runner.py connect <패턴>        # 지정된 애플리케이션에 연결
  python main_runner.py analyze              # 현재 연결된 앱의 UI 구조 분석
  python main_runner.py run <시나리오.json>   # 시나리오 실행
  
예시:
  python main_runner.py test-notepad
  python main_runner.py connect ".*계산기|.*Calculator"
  python main_runner.py run scenario.json
  python main_runner.py run scenario.json --data data.csv

옵션:
  --data <파일>     데이터 주도 테스트용 CSV 파일
  --depth <숫자>    UI 분석 깊이 (기본값: 10)
""")


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    runner = ImprovedMainRunner()
    
    try:
        if command == "test-notepad":
            print("🧪 메모장 테스트 모드")
            success = runner.run_notepad_test()
            sys.exit(0 if success else 1)
        
        elif command == "connect":
            if len(sys.argv) < 3:
                print("❌ 연결할 애플리케이션 패턴을 지정하세요.")
                print("예시: python main_runner.py connect \".*메모장\"")
                sys.exit(1)
            
            pattern = sys.argv[2]
            success = runner.connect_to_custom_app(pattern)
            
            if success:
                print("✅ 연결 완료! 이제 다른 명령어를 사용할 수 있습니다.")
                # 연결 후 UI 분석 제안
                print("💡 UI 구조를 분석하려면: python main_runner.py analyze")
            
            sys.exit(0 if success else 1)
        
        elif command == "analyze":
            depth = 10
            if "--depth" in sys.argv:
                try:
                    depth_idx = sys.argv.index("--depth") + 1
                    depth = int(sys.argv[depth_idx])
                except (IndexError, ValueError):
                    print("⚠️ --depth 옵션 형식이 잘못되었습니다. 기본값 10을 사용합니다.")
            
            # 먼저 연결이 필요
            print("📱 먼저 애플리케이션에 연결해야 합니다.")
            print("어떤 애플리케이션에 연결하시겠습니까?")
            pattern = input("애플리케이션 제목 패턴 입력 (예: .*메모장): ").strip()
            
            if pattern:
                if runner.connect_to_custom_app(pattern):
                    runner.analyze_ui_structure(depth)
                else:
                    print("❌ 애플리케이션 연결 실패")
                    sys.exit(1)
            else:
                print("❌ 패턴이 입력되지 않았습니다.")
                sys.exit(1)
        
        elif command == "run":
            if len(sys.argv) < 3:
                print("❌ 실행할 시나리오 파일을 지정하세요.")
                print("예시: python main_runner.py run scenario.json")
                sys.exit(1)
            
            scenario_file = sys.argv[2]
            data_file = None
            
            # 데이터 파일 옵션 확인
            if "--data" in sys.argv:
                try:
                    data_idx = sys.argv.index("--data") + 1
                    data_file = sys.argv[data_idx]
                except IndexError:
                    print("⚠️ --data 옵션에 파일명이 지정되지 않았습니다.")
            
            # 시나리오 파일에서 앱 연결 정보 확인
            try:
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    scenario_data = json.load(f)
                
                app_pattern = scenario_data.get("target_app", {}).get("title_pattern")
                if app_pattern:
                    print(f"🎯 대상 애플리케이션: {app_pattern}")
                    if runner.connect_to_custom_app(app_pattern):
                        success = runner.run_custom_scenario(scenario_file, data_file)
                        sys.exit(0 if success else 1)
                    else:
                        print("❌ 대상 애플리케이션 연결 실패")
                        sys.exit(1)
                else:
                    print("❌ 시나리오 파일에 target_app.title_pattern이 없습니다.")
                    sys.exit(1)
                    
            except FileNotFoundError:
                print(f"❌ 시나리오 파일을 찾을 수 없습니다: {scenario_file}")
                sys.exit(1)
            except json.JSONDecodeError:
                print(f"❌ 시나리오 파일 형식이 잘못되었습니다: {scenario_file}")
                sys.exit(1)
        
        else:
            print(f"❌ 알 수 없는 명령어: {command}")
            print_usage()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"💥 예상치 못한 오류: {e}")
        log.error(f"Unexpected error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()