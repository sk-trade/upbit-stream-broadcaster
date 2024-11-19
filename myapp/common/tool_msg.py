import os 
import requests
import json
import logging
import asyncio
import aiohttp

async def mattermost_send_message(message: str) -> bool:
    """
    비동기로 Mattermost 웹훅으로 메시지를 보내는 함수

    Args:
        message (str): 보낼 메시지

    Returns:
        bool: 성공 여부
    """
    webhook_url = os.getenv('MATTERMOST_URL')
    payload = {"text": message}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            ) as response:
                if response.status == 200:
                    logging.debug("Mattermost 메시지 전송 성공")
                    return True
                else:
                    logging.error(f"Mattermost 전송 실패: {response.status} - {await response.text()}")
                    return False
    except Exception as e:
        logging.error(f"Mattermost 전송 중 오류 발생: {e}")
        return False

class MattermostHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        """
        비동기 메시지 전송을 위해 asyncio.create_task를 사용하여 mattermost_send_message 호출
        """
        try:
            msg = self.format(record)
            asyncio.create_task(mattermost_send_message(msg))  # 비동기로 실행
        except Exception:
            self.handleError(record)