import asyncio
import websockets
import json
import logging
from collections import deque
from typing import List, Dict

from myapp.common.tool_msg import mattermost_send_message

class UpbitTradeWebSocket:
    def __init__(self, initial_symbols: List[str], zmq_publisher):
        self.uri = "wss://api.upbit.com/websocket/v1"
        self.current_symbols = initial_symbols
        self.processed_ids = deque(maxlen=2500)  # 중복 데이터 필터링을 위한 deque
        self.active_connection = None
        self.is_running = False
        self.reconnect_delay = 1  # 초기 재연결 딜레이
        self.max_reconnect_delay = 30  # 최대 재연결 딜레이
        self.zmq_publisher = zmq_publisher  # ZMQ Publisher 소켓
        self._connection_lock = asyncio.Lock()
        self.is_switching = False

    async def create_subscription_message(self, symbols: List[Dict[str, int]]) -> str:
        """구독 메시지 생성"""
        codes = [ticker["market"] for ticker in symbols]
        subscribe_format = [
            {"ticket": "unique_ticket"},
            {
                "type": "trade",
                "codes": codes,
                "is_only_realtime": True  # 실시간 데이터만 구독
            }
        ]
        return json.dumps(subscribe_format)

    async def connect(self):
        """WebSocket 연결 수립"""
        try:
            connection = await websockets.connect(
                self.uri,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            # 구독 메시지 전송
            subscription_message = await self.create_subscription_message(self.current_symbols)
            await connection.send(subscription_message)
            
            logging.info(f"연결 수립 및 구독 완료: {[ticker['market'] for ticker in self.current_symbols]}")
            return connection
            
        except Exception as e:
            logging.error(f"연결 수립 실패: {e}")
            return None

    async def reconnect(self):
        """재연결 로직"""
        if self.is_switching:
            return

        async with self._connection_lock:
            while True:
                connection = await self.connect()
                if connection:
                    self.active_connection = connection
                    self.reconnect_delay = 1  # 성공 시 딜레이 초기화
                    break
                
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

    async def handle_message(self, message_data: dict):
        """체결 데이터 메시지 처리 및 중복 필터링"""
        try:
            # 고유 ID를 사용한 중복 체크
            sequential_id = message_data.get("sequential_id")
            if sequential_id in self.processed_ids:
                logging.debug(f"중복 데이터 무시: {sequential_id}")
                return

            # 중복되지 않은 데이터 처리
            self.processed_ids.append(sequential_id)
            logging.debug(f"수신 데이터: {message_data}")

            # 데이터를 ZMQ로 브로드캐스트
            await self.zmq_publisher.send_json(message_data)

        except Exception as e:
            logging.error(f"메시지 처리 중 오류 발생: {e}")

    async def listen(self):
        """메시지 수신 루프"""
        self.is_running = True
        
        while self.is_running:
            try:
                if not self.active_connection or self.active_connection.closed:
                    if not self.is_switching:  # 스위칭 중이 아닐 때만 재연결
                        await self.reconnect()
                    continue

                message = await self.active_connection.recv()
                message_data = json.loads(message)
                await self.handle_message(message_data)

            except websockets.ConnectionClosed:
                if not self.is_switching:  # 스위칭 중이 아닐 때만 재연결
                    logging.error("연결이 종료되었습니다. 재연결 시도...")
                    await self.reconnect()
            except json.JSONDecodeError:
                logging.error("잘못된 JSON 형식")
            except Exception as e:
                logging.error(f"예기치 않은 오류: {e}")
                await asyncio.sleep(1)

    async def update_subscription(self, new_symbols: List[str]):
        """
        구독 목록 업데이트: 새 연결 생성 후 기존 연결 종료
        Args:
            new_symbols (List[str]): 새로 구독할 티커 목록
        """
        async with self._connection_lock:
            try:
                self.is_switching = True
                
                # 새로운 WebSocket 연결 생성
                new_connection = await websockets.connect(
                    self.uri,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                )
                
                # 새로운 구독 메시지 전송
                subscription_message = await self.create_subscription_message(new_symbols)
                await new_connection.send(subscription_message)

                # 새 연결이 정상적인지 확인
                if new_connection.closed:
                    logging.error("새 WebSocket 연결이 안정적이지 않습니다.")
                    await new_connection.close()
                    return

                logging.info(f"새로운 WebSocket 연결 생성 및 구독 완료: {[ticker['market'] for ticker in new_symbols]}")

                # 기존 연결 백업 및 새 연결 설정
                old_connection = self.active_connection
                self.active_connection = new_connection
                self.current_symbols = new_symbols
                self.processed_ids.clear()

                # 이전 연결이 있으면 안전하게 종료
                if old_connection and not old_connection.closed: 
                    try:
                        await old_connection.close()
                        logging.info("기존 WebSocket 연결 종료")
                    except Exception as e:
                        logging.error(f"기존 연결 종료 중 에러 발생: {e}")

            except Exception as e:
                logging.error(f"구독 업데이트 실패: {e}")
                if not self.active_connection or self.active_connection.closed:
                    await self.reconnect()
            finally:
                self.is_switching = False

    async def stop(self):
        """WebSocket 연결 종료"""
        self.is_running = False
        if self.active_connection:
            await self.active_connection.close()