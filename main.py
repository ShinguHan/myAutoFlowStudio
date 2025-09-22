# -*- coding: utf-8 -*-
import sys
import os
import ctypes


# ---------------------------------------------

# 강제로 COM 초기화 (STA 모드)
ctypes.windll.ole32.OleInitialize(None)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow


def main():
    """
    애플리케이션을 초기화하고 실행하는 메인 함수.
    """
    # 1. 애플리케이션 실행에 필요한 디렉토리들이 존재하는지 확인하고, 없으면 생성합니다.
    required_dirs = ["scenarios", "logs", "reports", "data"]
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

    # ✅ 2. QApplication 생성 전에 DPI 라운딩 정책 설정
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # --- 환경 변수 설정 (QApplication 생성 전) ---
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1" 

    # 3. PyQt 애플리케이션 인스턴스를 생성합니다.
    app = QApplication(sys.argv)

    # 4. 기본 폰트 강제 지정
    app.setFont(QFont("Segoe UI", 10))

    # 5. 메인 윈도우 인스턴스를 생성합니다.
    main_window = MainWindow()

    # 6. 메인 윈도우를 화면에 표시합니다.
    main_window.show()

    # 7. 애플리케이션의 이벤트 루프를 시작합니다.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
