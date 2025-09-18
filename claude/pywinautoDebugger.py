# -*- coding: utf-8 -*-
"""
pywinauto 메모장 제어 문제 진단 및 해결을 위한 디버깅 스크립트
"""
import time
import pywinauto
from pywinauto.application import Application
from pywinauto import findwindows
from pywinauto.timings import TimeoutError
import subprocess
import sys

class PywinautoDebugger:
    def __init__(self):
        self.app = None
        self.main_window = None
    
    def check_pywinauto_version(self):
        """pywinauto 버전 확인"""
        print(f"🔍 pywinauto 버전: {pywinauto.__version__}")
        print(f"🔍 Python 버전: {sys.version}")
    
    def launch_notepad(self):
        """메모장을 새로 실행"""
        try:
            print("📝 메모장을 실행합니다...")
            subprocess.Popen(["notepad.exe"])
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ 메모장 실행 실패: {e}")
            return False
    
    def find_notepad_windows(self):
        """시스템의 모든 메모장 창 찾기"""
        print("\n🔍 시스템의 메모장 창들을 찾습니다...")
        try:
            # 다양한 방법으로 메모장 창 찾기
            windows = findwindows.find_elements()
            notepad_windows = []
            
            for window in windows:
                if "notepad" in window.name.lower() or "메모장" in window.name:
                    notepad_windows.append(window)
                    print(f"   - 창 제목: '{window.name}' (클래스: {window.class_name})")
            
            return notepad_windows
        except Exception as e:
            print(f"❌ 창 찾기 실패: {e}")
            return []
    
    def connect_to_notepad_multiple_ways(self):
        """다양한 방법으로 메모장에 연결 시도"""
        methods = [
            # 방법 1: 제목으로 연결 (기본)
            {"method": "title", "params": {"title": "제목 없음 - 메모장"}},
            {"method": "title", "params": {"title": "Untitled - Notepad"}},
            
            # 방법 2: 클래스명으로 연결
            {"method": "class", "params": {"class_name": "Notepad"}},
            
            # 방법 3: 정규식으로 연결
            {"method": "regex", "params": {"title_re": r".*메모장|.*Notepad"}},
            
            # 방법 4: 프로세스명으로 연결
            {"method": "process", "params": {"process": "notepad.exe"}},
        ]
        
        for i, method in enumerate(methods, 1):
            print(f"\n🔄 방법 {i}: {method['method']} 방식으로 연결 시도...")
            try:
                if method["method"] == "title":
                    self.app = Application(backend="uia").connect(**method["params"])
                elif method["method"] == "class":
                    self.app = Application(backend="uia").connect(**method["params"])
                elif method["method"] == "regex":
                    self.app = Application(backend="uia").connect(**method["params"])
                elif method["method"] == "process":
                    self.app = Application(backend="uia").connect(**method["params"])
                
                self.main_window = self.app.top_window()
                print(f"✅ 연결 성공! 창 제목: '{self.main_window.window_text()}'")
                return True
                
            except Exception as e:
                print(f"❌ {method['method']} 방식 실패: {e}")
                continue
        
        print("❌ 모든 연결 방법이 실패했습니다.")
        return False
    
    def test_backend_compatibility(self):
        """다른 백엔드로 테스트"""
        backends = ["uia", "win32"]
        
        for backend in backends:
            print(f"\n🔄 {backend} 백엔드로 테스트...")
            try:
                app = Application(backend=backend).connect(title_re=r".*메모장|.*Notepad")
                window = app.top_window()
                print(f"✅ {backend} 백엔드 연결 성공: '{window.window_text()}'")
                
                # 간단한 조작 테스트
                if backend == "uia":
                    text_area = window.child_window(control_type="Document")
                else:  # win32
                    text_area = window.child_window(class_name="Edit")
                
                text_area.set_text("테스트 텍스트")
                print(f"✅ {backend} 백엔드로 텍스트 입력 성공!")
                
                return backend, app, window
                
            except Exception as e:
                print(f"❌ {backend} 백엔드 실패: {e}")
        
        return None, None, None
    
    def analyze_ui_structure(self):
        """UI 구조 상세 분석"""
        if not self.main_window:
            print("❌ 메모장 창이 연결되지 않았습니다.")
            return
        
        print(f"\n🔍 메모장 UI 구조 분석:")
        print(f"   - 창 제목: '{self.main_window.window_text()}'")
        print(f"   - 클래스명: '{self.main_window.class_name()}'")
        print(f"   - 컨트롤 타입: '{self.main_window.element_info.control_type}'")
        
        # 자식 요소들 찾기
        print("\n📋 자식 요소들:")
        try:
            children = self.main_window.children()
            for i, child in enumerate(children):
                try:
                    print(f"   {i+1}. 제목: '{child.window_text()}', "
                          f"클래스: '{child.class_name()}', "
                          f"타입: '{child.element_info.control_type}', "
                          f"AutoID: '{child.element_info.automation_id}'")
                except:
                    print(f"   {i+1}. (정보 읽기 실패)")
        except Exception as e:
            print(f"❌ 자식 요소 분석 실패: {e}")
    
    def test_text_input_methods(self):
        """다양한 텍스트 입력 방법 테스트"""
        if not self.main_window:
            print("❌ 메모장 창이 연결되지 않았습니다.")
            return
        
        test_methods = [
            {"name": "UIA Document 타입으로 찾기", "finder": lambda: self.main_window.child_window(control_type="Document")},
            {"name": "UIA Edit 타입으로 찾기", "finder": lambda: self.main_window.child_window(control_type="Edit")},
            {"name": "클래스명 Edit으로 찾기", "finder": lambda: self.main_window.child_window(class_name="Edit")},
            {"name": "첫 번째 자식 요소", "finder": lambda: self.main_window.children()[0]},
        ]
        
        for method in test_methods:
            print(f"\n🔄 {method['name']} 테스트...")
            try:
                text_element = method["finder"]()
                
                # 요소 정보 출력
                print(f"   - 요소 타입: {text_element.element_info.control_type}")
                print(f"   - 클래스명: {text_element.class_name()}")
                
                # 다양한 텍스트 입력 방법 시도
                input_methods = [
                    ("set_text", lambda: text_element.set_text("테스트1")),
                    ("set_edit_text", lambda: text_element.set_edit_text("테스트2")),
                    ("type_keys", lambda: text_element.type_keys("테스트3")),
                    ("send_chars", lambda: text_element.send_chars("테스트4")),
                ]
                
                for input_name, input_func in input_methods:
                    try:
                        # 기존 텍스트 지우기
                        text_element.set_text("")
                        time.sleep(0.5)
                        
                        # 텍스트 입력
                        input_func()
                        time.sleep(0.5)
                        
                        # 결과 확인
                        current_text = text_element.window_text()
                        print(f"   ✅ {input_name}: '{current_text}'")
                        
                    except Exception as e:
                        print(f"   ❌ {input_name} 실패: {e}")
                
                return text_element
                
            except Exception as e:
                print(f"   ❌ {method['name']} 실패: {e}")
        
        return None
    
    def test_element_finding_robustness(self):
        """요소 찾기 안정성 테스트"""
        if not self.main_window:
            return
        
        print(f"\n🔍 요소 찾기 안정성 테스트:")
        
        # 여러 번 반복해서 요소 찾기 테스트
        for i in range(5):
            try:
                print(f"   시도 {i+1}: ", end="")
                text_element = self.main_window.child_window(control_type="Document")
                text_element.wait('exists enabled visible ready', timeout=5)
                print("✅ 성공")
            except Exception as e:
                print(f"❌ 실패 - {e}")
            time.sleep(1)
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("🚀 pywinauto 메모장 제어 종합 테스트 시작\n")
        
        # 1. 버전 정보 확인
        self.check_pywinauto_version()
        
        # 2. 메모장 실행
        if not self.launch_notepad():
            return
        
        # 3. 메모장 창 찾기
        notepad_windows = self.find_notepad_windows()
        if not notepad_windows:
            print("❌ 메모장 창을 찾을 수 없습니다.")
            return
        
        # 4. 다양한 방법으로 연결 시도
        if not self.connect_to_notepad_multiple_ways():
            # 5. 다른 백엔드 시도
            backend, app, window = self.test_backend_compatibility()
            if backend:
                self.app = app
                self.main_window = window
                print(f"✅ {backend} 백엔드로 작업을 계속합니다.")
            else:
                print("❌ 모든 연결 방법이 실패했습니다.")
                return
        
        # 6. UI 구조 분석
        self.analyze_ui_structure()
        
        # 7. 텍스트 입력 테스트
        working_element = self.test_text_input_methods()
        
        # 8. 안정성 테스트
        if working_element:
            self.test_element_finding_robustness()
        
        print(f"\n✅ 테스트 완료!")
        
        # 권장사항 제시
        self.provide_recommendations()
    
    def provide_recommendations(self):
        """문제 해결을 위한 권장사항 제시"""
        print(f"\n💡 권장사항:")
        print(f"   1. pywinauto 최신 버전 사용: pip install --upgrade pywinauto")
        print(f"   2. 관리자 권한으로 실행해보기")
        print(f"   3. 백엔드를 'win32'로 변경해보기 (Application(backend='win32'))")
        print(f"   4. 요소 찾기 전에 충분한 대기 시간 추가")
        print(f"   5. try-except로 예외 처리 강화")
        print(f"   6. 실제 시나리오에서는 element.wait() 메서드 활용")

def main():
    """메인 함수"""
    debugger = PywinautoDebugger()
    debugger.run_comprehensive_test()

if __name__ == "__main__":
    main()