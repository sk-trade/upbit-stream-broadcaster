from datetime import datetime
from pytz import timezone
import logging
import asyncio

from myapp.common.tool_msg import MattermostHandler

def get_kr_time():
    return datetime.now(timezone('Asia/Seoul'))


def set_logging(log_level):
    # 로그 생성
    logger = logging.getLogger()
    # 로그 레벨 문자열을 적절한 로깅 상수로 변환
    log_level_constant = getattr(logging, log_level, logging.INFO)
    # 로그의 출력 기준 설정
    logger.setLevel(log_level_constant)
    # log 출력 형식
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # log를 console에 출력
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # log를 파일에 출력
    #file_handler = logging.FileHandler('GoogleTrendsBot.log')
    #file_handler.setFormatter(formatter)
    #logger.addHandler(file_handler)

    mattermost_handler = MattermostHandler(level=logging.ERROR)
    mattermost_handler.setFormatter(formatter)
    logger.addHandler(mattermost_handler)


async def wait_until_next_minute(interval: int = 10):
    """
    다음 정분(interval)에 맞춰 대기
    Args:
        interval (int): 대기 간격 (분 단위, 기본값: 10분)
    """
    now = datetime.now()
    # 다음 실행 시간 계산
    next_minute = (now.minute // interval + 1) * interval
    if next_minute >= 60:
        next_hour = now.hour + 1 if now.hour < 23 else 0
        next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    else:
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)

    wait_seconds = (next_time - now).total_seconds()

    # 대기 시간 출력
    #print(f"현재 시각: {now}, 다음 실행 시간: {next_time}, 대기: {wait_seconds}초")
    await asyncio.sleep(wait_seconds)