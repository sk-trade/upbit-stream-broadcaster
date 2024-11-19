from typing import List, Dict, Optional
import logging
import asyncio
import aiohttp

from myapp.common.tool_msg import mattermost_send_message

async def get_top_tickers(TOP_TICKERS, max_retries=5, delay=10) -> List[Dict[str, int]]:
    """비동기로 거래량 상위 30개 종목 가져오기 (재시도 포함)"""
    retries = 0
    while retries < max_retries:
        try:
            # 모든 시장 정보 가져오기
            url = "https://api.upbit.com/v1/market/all"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    markets = [market['market'] for market in data if market['market'].startswith('KRW-')]

            # 거래량 상위 종목 가져오기
            url = f"https://api.upbit.com/v1/ticker?markets={','.join(markets)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    tickers = sorted(
                        await response.json(),
                        key=lambda x: x['trade_price'] * x['acc_trade_volume_24h'],
                        reverse=True
                    )[:TOP_TICKERS]

            return [{"market": ticker["market"], "rank": idx + 1} for idx, ticker in enumerate(tickers)]

        except Exception as e:
            retries += 1
            logging.error(f"Top tickers API 호출 실패 (재시도 {retries}/{max_retries}): {e}")
            await asyncio.sleep(delay)

    logging.error(f"Top tickers API 호출 실패: 최대 재시도 횟수 초과")
    return []

async def rank_changes(new_tickers: List[Dict[str, int]], previous_tickers: Optional[List[Dict[str, int]]]) -> None:
    if not previous_tickers:
        logging.info("이전 상태 없음.")
        return

    rank_msg = ''

    previous_map = {ticker["market"]: ticker["rank"] for ticker in previous_tickers}
    new_map = {ticker["market"]: ticker["rank"] for ticker in new_tickers}

    for market, new_rank in new_map.items():
        old_rank = previous_map.get(market)
        if old_rank is not None and old_rank != new_rank:
            rank_msg += (f"{market}: 순위 변화 {old_rank} → {new_rank}\n")

    new_entries = set(new_map.keys()) - set(previous_map.keys())
    for market in new_entries:
        rank_msg += (f"{market} 새로 추가됨 (순위: {new_map[market]})\n")

    removed_entries = set(previous_map.keys()) - set(new_map.keys())
    for market in removed_entries:
        rank_msg += (f"{market} Top 에서 제거됨\n")

    if rank_msg:
        rank_msg += "\n전체 순위:\n"
        rank_msg += "\n".join([f"{ticker['rank']}: {ticker['market']}" for ticker in new_tickers])
        logging.info(rank_msg)
        await mattermost_send_message(rank_msg)