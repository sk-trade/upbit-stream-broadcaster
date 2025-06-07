import os
import asyncio
import logging
import zmq
import zmq.asyncio

import myapp.common.tool_util as tool_util
import myapp.common.tool_upbit as tool_upbit
from myapp.src.stream import UpbitTradeWebSocket
from myapp.common.tool_msg import send_webhook_message

async def main():
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ZMQ_PORT = os.getenv('ZMQ_PORT', '11555')
    TOP_TICKERS = int(os.getenv('TOP_TICKERS', '30'))
    MINUTE_INTERVAL = int(os.getenv('MINUTE_INTERVAL', '10'))
    VERSION = os.getenv('VERSION', '?')

    tool_util.set_logging(LOG_LEVEL)

    await send_webhook_message(f'start upbit-stream-broadcaster:{VERSION}')

    try:
        # ZMQ 초기화 및 Publisher 설정
        zmq_context = zmq.asyncio.Context()
        zmq_publisher = zmq_context.socket(zmq.PUB)
        zmq_publisher.bind(f"tcp://*:{ZMQ_PORT}")  # 내부망 브로드캐스트 주소

        # 초기 구독 종목 설정
        initial_tickers = await tool_upbit.get_top_tickers(TOP_TICKERS)
        if not initial_tickers:
            logging.error("Top 가져오기 실패.")
            return

        client = UpbitTradeWebSocket(initial_tickers, zmq_publisher)
        
        # 수신 시작
        listen_task = asyncio.create_task(client.listen())

        previous_tickers = initial_tickers

        # 10분마다 거래량 상위 30개로 구독 변경
        try:
            while True:
                await tool_util.wait_until_next_minute(MINUTE_INTERVAL)
                new_tickers = await tool_upbit.get_top_tickers(TOP_TICKERS)
                if not new_tickers:
                    logging.warning("Top 갱신 실패. 기존 구독 유지.")
                    continue

                await tool_upbit.rank_changes(new_tickers, previous_tickers)
                if {t["market"] for t in new_tickers} != {t["market"] for t in previous_tickers}:
                    await client.update_subscription(new_tickers)
                previous_tickers = new_tickers
        except KeyboardInterrupt:
            await client.stop()
        finally:
            zmq_publisher.close()
            zmq_context.term()

    except Exception as e:
        logging.error(f"메인 프로세스 중 예기치 못한 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
