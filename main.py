# -*- coding: utf-8 -*-
"""
이 파일은 AutoFlow Studio 애플리케이션의 메인 시작점(Entry Point)입니다.
- 필요한 폴더(scenarios, logs 등)를 생성합니다.
- PyQt6 애플리케이션 인스턴스를 생성합니다.
- 메인 윈도우(MainWindow)를 생성하고 화면에 표시합니다.
- 애플리케이션의 이벤트 루프를 시작합니다.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """
    애플리케이션을 초기화하고 실행하는 메인 함수.
    """
    # 1. 애플리케이션 실행에 필요한 디렉토리들이 존재하는지 확인하고, 없으면 생성합니다.
    #    이는 프로그램 첫 실행 시 발생할 수 있는 오류를 방지합니다.
    required_dirs = ["scenarios", "logs", "reports", "data"]
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

    # 2. PyQt 애플리케이션 인스턴스를 생성합니다.
    #    모든 GUI 애플리케이션은 반드시 하나의 QApplication 인스턴스를 가져야 합니다.
    app = QApplication(sys.argv)

    # 3. 메인 윈도우 인스턴스를 생성합니다.
    #    이 클래스가 우리가 만든 프로그램의 모든 UI와 기능을 담고 있습니다.
    main_window = MainWindow()

    # 4. 메인 윈도우를 화면에 표시합니다.
    main_window.show()

    # 5. 애플리케이션의 이벤트 루프를 시작합니다.
    #    이 코드가 실행되면, 프로그램은 사용자의 입력(클릭, 키보드 등)을 기다리는
    #    상태가 되며, 창을 닫을 때까지 종료되지 않습니다.
    #    sys.exit()로 감싸주어, 앱이 종료될 때 프로세스가 깔끔하게 정리되도록 합니다.
    sys.exit(app.exec())

if __name__ == "__main__":
    # 이 스크립트가 직접 실행되었을 때만 main() 함수를 호출합니다.
    # (다른 파일에서 이 파일을 import할 경우에는 호출되지 않습니다.)
    main()

