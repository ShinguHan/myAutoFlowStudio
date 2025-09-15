# -*- coding: utf-8 -*-
"""
이 모듈은 AutoFlow Studio에서 발생하는 기술적인 예외(Exception)들을
사용자가 이해하기 쉬운 한국어 메시지로 변환하는 '번역기' 역할을 합니다.
이를 통해 사용자는 오류의 원인을 더 직관적으로 파악할 수 있습니다.
"""
import pywinauto
from core.scenario_runner import TargetAppClosedError, VariableNotFoundError
from utils.logger_config import log

def translate_exception(e):
    """
    기술적인 예외(Exception) 객체를 사용자 친화적인 한국어 메시지로 변환합니다.

    Args:
        e (Exception): 시나리오 실행 중 발생한 예외 객체.

    Returns:
        str: 사용자가 이해하기 쉬운 오류 메시지 문자열.
    """
    # pywinauto에서 UI 요소를 찾지 못하고 타임아웃이 발생했을 때
    if isinstance(e, pywinauto.timings.TimeoutError):
        return "UI 요소를 찾는 데 시간이 초과되었습니다. 대상이 나타나지 않거나, 비활성화되었거나, 응답이 느릴 수 있습니다."
    
    # pywinauto에서 지정된 속성의 UI 요소를 찾지 못했을 때
    elif isinstance(e, pywinauto.findwindows.ElementNotFoundError):
        return "지정된 UI 요소를 찾을 수 없습니다. 창 제목이나 요소의 이름, 속성이 올바른지 확인해주세요."
    
    # 우리가 직접 정의한, 대상 앱이 닫혔을 때의 예외
    elif isinstance(e, TargetAppClosedError):
        return str(e) # 이미 친절한 메시지를 담고 있으므로 그대로 반환

    # 우리가 직접 정의한, 변수를 찾지 못했을 때의 예외
    elif isinstance(e, VariableNotFoundError):
        return str(e) # 이미 친절한 메시지를 담고 있으므로 그대로 반환
    
    # .click_input(), .set_text() 등 지원되지 않는 동작을 호출하려 할 때
    elif isinstance(e, AttributeError):
        return f"지원되지 않는 동작을 호출했거나, 대상이 해당 동작을 수행할 수 없습니다. (상세: {e})"
        
    # 앱 연결 자체에 실패했을 때
    elif isinstance(e, ConnectionError):
        return "대상 애플리케이션에 연결할 수 없습니다. 창 제목을 다시 확인하거나 앱이 실행 중인지 확인해주세요."
        
    # 위에서 처리되지 않은 모든 기타 예외
    else:
        # 사용자에겐 간단한 메시지를 보여주고,
        # 개발자가 원인을 파악할 수 있도록 상세 내용은 로그 파일에 기록합니다.
        log_message = f"알 수 없는 오류가 발생했습니다: {type(e).__name__}"
        log.error(log_message, exc_info=True)
        return log_message

