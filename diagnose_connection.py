# diagnose_connection.py
import pywinauto
from pywinauto import Desktop
import time

def diagnose():
    """pywinauto 연결 문제를 체계적으로 진단하는 스크립트"""
    print("=" * 60)
    print("Pywinauto 연결 문제 진단 도구를 시작합니다.")
    print("=" * 60)
    print("⚠️ 'SIMULATOR_KIM - [Simulator]' 프로그램을 반드시 실행한 상태여야 합니다.")
    input("준비되었으면 Enter 키를 누르세요...")

    # 1단계: 현재 시스템의 모든 창 제목을 스캔하여 보여줍니다.
    print("\n[1단계] 시스템의 모든 창 제목을 스캔합니다...")
    try:
        windows = Desktop(backend="uia").windows()
        visible_windows = sorted([w.window_text() for w in windows if w.window_text() and w.is_visible()])
        
        print(f"\n✅ 총 {len(visible_windows)}개의 창을 찾았습니다:")
        for title in visible_windows:
            print(f"  - '{title}'")
        
        print("\n👉 [확인 필요] 위 목록에 시뮬레이터의 정확한 창 제목이 있는지 확인해주십시오.")
        print("   만약 제목이 다르다면, 아래 2단계의 target_title 변수를 복사한 제목으로 수정해야 합니다.")

    except Exception as e:
        print(f"  [오류] 창 목록을 가져오는 데 실패했습니다: {e}")

    # 2단계: 다양한 방법으로 연결을 시도합니다.
    print("\n" + "=" * 60)
    print("[2단계] 30초의 여유 시간으로 연결을 시도합니다...")

    # 📌 검증할 창 제목 (만약 1단계에서 제목이 달랐다면 이 부분을 수정하세요)
    target_title = "SIMULATOR_KIM - [Simulator]"
    
    # 시도 1: 가장 기본적인 방법 (정확한 제목)
    print(f"\n--- [시도 1] 정확한 제목으로 연결: '{target_title}'")
    try:
        pywinauto.Application(backend="uia").connect(title=target_title, timeout=30)
        print("  [성공] 'uia' 백엔드로 연결에 성공했습니다! 창 제목이 정확합니다.")
        print("="*60 + "\n진단 완료: 창 제목 불일치 또는 권한 문제가 아니었습니다. AutoFlow Studio 코드 자체를 다시 점검해야 합니다.")
        return
    except Exception:
        print("  [실패] 'uia' 백엔드 연결 실패.")
    try:
        pywinauto.Application(backend="win32").connect(title=target_title, timeout=30)
        print("  [성공] 'win32' 백엔드로 연결에 성공했습니다! 창 제목이 정확합니다.")
        print("="*60 + "\n진단 완료: 창 제목 불일치 또는 권한 문제가 아니었습니다. AutoFlow Studio 코드 자체를 다시 점검해야 합니다.")
        return
    except Exception:
        print("  [실패] 'win32' 백엔드 연결 실패.")

    # 시도 2: 정규식을 사용한 방법 (특수문자 문제 해결)
    target_regex = r"SIMULATOR_KIM - \[Simulator\]"
    print(f"\n--- [시도 2] 특수문자를 처리한 정규식으로 연결: '{target_regex}'")
    try:
        pywinauto.Application(backend="uia").connect(title_re=target_regex, timeout=30)
        print("  [성공] 'uia' 백엔드로 연결에 성공했습니다! 원인은 창 제목의 특수문자였습니다.")
        print("="*60 + "\n해결책: AutoFlow Studio의 앱 연결 입력창에 위 정규식을 사용하십시오.")
        return
    except Exception:
        print("  [실패] 'uia' 백엔드 연결 실패.")

    print("\n" + "="*60)
    print("진단 결론: 모든 자동 연결 시도에 실패했습니다.")
    print("가장 유력한 원인은 보안 프로그램(Antivirus) 또는 외부 환경 문제입니다.")
    print("="*60)

if __name__ == '__main__':
    diagnose()
