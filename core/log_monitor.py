# -*- coding: utf-8 -*-
"""
이 모듈은 지정된 로그 파일을 실시간으로 감시(monitoring)하고,
특정 정규식 패턴이 감지되면 시그널을 발생시켜 다른 동작(시나리오 실행 등)을
트리거(trigger)하는 역할을 합니다.
GUI의 멈춤 현상을 방지하기 위해 별도의 스레드(QThread)로 동작합니다.
"""
import re
import time
from PyQt6.QtCore import QThread, pyqtSignal
from utils.logger_config import log

class LogMonitor(QThread):
    """
    파일을 실시간으로 감시하여 특정 패턴을 찾는 스레드 클래스.
    """
    # 패턴이 발견되었을 때 감지된 라인을 전달하는 시그널
    pattern_found = pyqtSignal(str)
    # 스레드 작업이 완료되었을 때 발생하는 시그널
    finished = pyqtSignal()

    def __init__(self, file_path, pattern):
        """
        LogMonitor 인스턴스를 초기화합니다.

        Args:
            file_path (str): 감시할 로그 파일의 전체 경로.
            pattern (str): 찾을 정규식 패턴.
        """
        super().__init__()
        self.file_path = file_path
        self.pattern = re.compile(pattern)
        self._is_running = True # 스레드의 실행/중지 상태를 제어하는 플래그

    def run(self):
        """QThread의 메인 실행 메서드. 스레드가 시작되면 자동으로 호출됩니다."""
        log.info(f"Log monitor started for file: {self.file_path}, pattern: '{self.pattern.pattern}'")
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 파일의 가장 마지막으로 이동하여, 모니터링 시작 이후의 로그만 읽습니다.
                f.seek(0, 2)
                
                while self._is_running:
                    line = f.readline()
                    # 새로운 로그 라인이 없으면 잠시 대기 후 다시 시도합니다.
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # 현재 라인이 정규식 패턴과 일치하는지 확인합니다.
                    if self.pattern.search(line):
                        log.info(f"Pattern found in log: {line.strip()}")
                        # 패턴을 찾았음을 메인 스레드(GUI)에 알립니다.
                        self.pattern_found.emit(line.strip())
                        
        except FileNotFoundError:
            log.error(f"Log file not found: {self.file_path}")
        except Exception as e:
            log.error(f"An error occurred in log monitor: {e}", exc_info=True)
        finally:
            log.info("Log monitor stopped.")
            # 작업이 정상적으로 또는 오류로 인해 종료되었음을 알립니다.
            self.finished.emit()

    def stop(self):
        """외부에서 스레드를 안전하게 중지시키기 위한 메서드."""
        log.info("Stopping log monitor...")
        self._is_running = False

