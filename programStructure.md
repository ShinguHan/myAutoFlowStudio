프로젝트 전체 파일 구조
AutoFlow_Studio/
│
├── core/ # 🎯 핵심 로직 모듈 (백엔드)
│ ├── **init**.py
│ ├── app_connector.py # pywinauto 연결 및 UI 구조 분석 담당
│ ├── log_monitor.py # 로그 파일 감시 및 시나리오 트리거 담당
│ └── scenario_runner.py # 시나리오 해석 및 단계별 실행 엔진
│
├── data/ # 💾 데이터 기반 테스트용 CSV 파일 저장소
│
├── gui/ # 🖥️ PyQt6 UI 관련 파일 (프론트엔드)
│ ├── **init**.py
│ ├── main_window.py # 메인 애플리케이션 윈도우
│ └── widgets/ # GUI 구성을 위한 커스텀 위젯
│ ├── **init**.py
│ ├── custom_tree_widget.py # 드래그 UX가 개선된 트리 위젯
│ ├── flow_editor.py # 시나리오 편집기 위젯
│ ├── parallel_runner.py # 병렬 실행 패널 위젯
│ └── ui_tree.py # UI 요소 트리뷰 위젯
│
├── logs/ # 📝 실행 로그 파일 저장소
│
├── reports/ # 📊 HTML 테스트 결과 보고서 저장소
│
├── scenarios/ # 📜 시나리오(.json) 파일 저장소
│
├── utils/ # 🛠️ 유틸리티 및 공통 설정 모듈
│ ├── **init**.py
│ ├── error_handler.py # 예외 메시지 변환기
│ └── logger_config.py # 전역 로깅 설정
│
├── main.py # 🚀 애플리케이션 시작점
├── README.md # 📖 프로젝트 종합 안내서
└── requirements.txt # 📦 의존성 패키지 목록
