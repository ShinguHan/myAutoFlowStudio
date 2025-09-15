# -*- coding: utf-8 -*-
"""
이 모듈은 AutoFlow Studio 프로젝트 전체에서 사용될 로깅(Logging) 시스템을 설정합니다.
- 로그 메시지를 콘솔과 파일(`logs/autoflow.log`)에 동시에 기록합니다.
- PyQt의 시그널-슬롯 메커니즘을 이용하여, 백그라운드 스레드에서 발생한 로그도
  GUI의 로그 뷰어에 안전하게 표시할 수 있도록 커스텀 핸들러를 정의합니다.
"""
import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    """
    로그 메시지를 PyQt 시그널로 전달하는 커스텀 로깅 핸들러.
    백그라운드 스레드의 로그를 메인 GUI 스레드로 안전하게 보내는 역할을 합니다.
    """
    # 로그 메시지를 문자열로 전달하는 시그널 정의
    log_message = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        """
        로거가 메시지를 기록할 때마다 호출되는 메서드.
        포맷팅된 로그 메시지를 log_message 시그널로 발생시킵니다.
        """
        msg = self.format(record)
        self.log_message.emit(msg)

# --- 로거 설정 ---

# 1. 전역 로거 인스턴스 생성
log = logging.getLogger("autoflow_studio")
log.setLevel(logging.INFO) # INFO 레벨 이상의 로그만 처리

# 2. 로그 파일 경로 설정 및 디렉토리 생성
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "autoflow.log")

# 3. 로그 메시지 형식(Formatter) 정의
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 4. 핸들러(Handler) 생성 및 설정
# 4-1. 파일 핸들러: 로그를 파일에 기록
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)

# 4-2. 스트림 핸들러: 로그를 콘솔(터미널)에 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# 4-3. Qt 커스텀 핸들러: 로그를 GUI 로그 뷰어로 전달
qt_log_handler = QtLogHandler()
qt_log_handler.setFormatter(formatter)

# 5. 로거에 핸들러 추가 (중복 출력을 방지하기 위해 로더에 핸들러가 없는 경우에만 추가)
if not log.handlers:
    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    log.addHandler(qt_log_handler)

