# simple_notepad_test.py
"""
가장 간단한 메모장 제어 테스트
문제 원인을 빠르게 파악하기 위한 최소 코드
"""

import time
import subprocess
from pywinauto.application import Application
from pywinauto import findwindows

def test_notepad_simple():
    """가장 기본적인 메모장 테스트"""
    print("🚀 간단한 메모장 테스트 시작")
    
    # 1. 메모장 실행
    print("📝 메모장 실행 중...")
    try:
        subprocess.Popen(["notepad.exe"])
        time.sleep(3)  # 실행 대기
        print("✅ 메모장 실행됨")
    except Exception as e:
        print(f"❌ 메모장 실행 실패: {e}")
        return False

    # 2. UIA 백엔드로 연결 시도
    print("\n🔗 UIA 백엔드로 연결 시도...")
    try:
        app_uia = Application(backend="uia").connect(title_re=".*메모장|.*Notepad")
        window_uia = app_uia.top_window()
        print(f"✅ UIA 연결 성공: '{window_uia.window_text()}'")
        
        # 텍스트 입력 시도
        print("📝 UIA로 텍스트 입력 시도...")
        text_elem = window_uia.child_window(control_type="Document")
        text_elem.set_text("UIA 테스트 성공!")
        print("✅ UIA 텍스트 입력 성공!")
        
        # 텍스트 읽기 시도
        current_text = text_elem.window_text()
        print(f"📖 현재 텍스트: '{current_text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ UIA 백엔드 실패: {e}")
    
    # 3. Win32 백엔드로 연결 시도
    print("\n🔗 Win32 백엔드로 연결 시도...")
    try:
        app_win32 = Application(backend="win32").connect(title_re=".*메모장|.*Notepad")
        window_win32 = app_win32.top_window()
        print(f"✅ Win32 연결 성공: '{window_win32.window_text()}'")
        
        # 텍스트 입력 시도
        print("📝 Win32로 텍스트 입력 시도...")
        text_elem = window_win32.child_window(class_name="Edit")
        text_elem.set_text("Win32 테스트 성공!")
        print("✅ Win32 텍스트 입력 성공!")
        
        # 텍스트 읽기 시도
        current_text = text_elem.window_text()
        print(f"📖 현재 텍스트: '{current_text}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Win32 백엔드도 실패: {e}")
    
    return False

def test_with_your_connector():
    """당신의 AppConnector로 테스트"""
    print("\n🧪 개선된 AppConnector로 테스트...")
    
    try:
        # 개선된 AppConnector 사용
        from core.app_connector import AppConnector  # 경로 수정 필요할 수 있음
        
        connector = AppConnector()
        
        # 메모장에 연결
        if connector.connect_to_app(r".*메모장|.*Notepad"):
            print("✅ AppConnector 연결 성공!")
            print(f"연결 정보: {connector.get_connection_info()}")
            
            # UI 트리 가져오기
            print("🌳 UI 트리 구축 중...")
            ui_tree = connector.get_ui_tree(max_depth=3)
            
            if ui_tree:
                print("✅ UI 트리 구축 성공!")
                # 트리의 일부만 출력
                print("📋 트리 구조 (일부):")
                print(f"  루트: {ui_tree['properties']}")
                if ui_tree['children']:
                    for i, child in enumerate(ui_tree['children'][:3]):
                        print(f"    자식 {i+1}: {child['properties']}")
                return True
            else:
                print("❌ UI 트리 구축 실패")
                return False
        else:
            print("❌ AppConnector 연결 실패")
            return False
            
    except ImportError:
        print("❌ AppConnector를 가져올 수 없음 - 경로 확인 필요")
        return False
    except Exception as e:
        print(f"❌ AppConnector 테스트 실패: {e}")
        return False

def main():
    """메인 실행"""
    print("=" * 50)
    print("🔧 pywinauto 메모장 제어 문제 진단")
    print("=" * 50)
    
    # 기본 테스트
    basic_success = test_notepad_simple()
    
    if basic_success:
        print(f"\n✅ 기본 테스트 성공! pywinauto는 정상 작동합니다.")
        
        # 개선된 커넥터 테스트
        connector_success = test_with_your_connector()
        
        if connector_success:
            print(f"\n🎉 모든 테스트 성공! 문제가 해결되었습니다.")
        else:
            print(f"\n⚠️ 기본 테스트는 성공했지만 AppConnector에 문제가 있습니다.")
            print("권장사항:")
            print("- core.app_connector 모듈 경로 확인")
            print("- logger_config.py 확인")
            print("- 개선된 AppConnector 코드 적용")
    else:
        print(f"\n❌ 기본 테스트 실패!")
        print("권장사항:")
        print("1. 관리자 권한으로 실행해보세요")
        print("2. pywinauto 재설치: pip uninstall pywinauto && pip install pywinauto")
        print("3. Windows 버전 및 보안 설정 확인")
        print("4. 메모장이 다른 사용자 권한으로 실행되었는지 확인")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()