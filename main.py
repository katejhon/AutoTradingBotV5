import asyncio
import datetime
import time               
from logger import log_info 
from state import BotState
from trader import Trader
from websocket import websocket_prices
from notifier import start
from exchange_async import get_top_symbols, load_precisions
from config import ACCOUNTS, COOLDOWN  
from report import loop as report_loop
from sync import sync_positions

symbol_last_traded = {}
last_day = datetime.date.today()


async def trade_loop(trader):
    while True:
        now = asyncio.get_event_loop().time()
        # Update symbols list every hour
        if now % 3600 == 0:  # Check if it's a new hour
            trader.symbols = (await get_top_symbols())[:20]  # Update symbols list
            log_info("🔄 Updated top 20 symbols list")  # Log the event

        for symbol in trader.symbols:
            # Check and trade each symbol
            if symbol not in symbol_last_traded or now - symbol_last_traded[symbol] >= COOLDOWN:
                await trader.trade(symbol)
                symbol_last_traded[symbol] = now

        await asyncio.sleep(1)

async def reset_daily(state):
    global last_day
    while True:
        today = datetime.date.today()
        if today != last_day:
            state.daily_pnl = 0
            state.trades_today = 0
            await state.save()
            last_day = today
        await asyncio.sleep(60)

async def main():
    state = BotState()
    await start()  # Telegram bot start notification

    # Load token precisions
    await load_precisions()

    # Initial symbol list
    symbols = (await get_top_symbols())[:20]

    # Sync positions for all accounts
    for acc in ACCOUNTS:
        await sync_positions(state, symbols, acc)

    # Start WebSocket for price updates
    asyncio.create_task(websocket_prices(symbols, state.price_cache))

    tasks = []

    # Start trader tasks for each account
    for acc in ACCOUNTS:
        trader = Trader(state, symbols, acc)
        tasks.append(asyncio.create_task(trader.monitor()))
        tasks.append(asyncio.create_task(trade_loop(trader)))

    # Start 5-minute report loop
    tasks.append(asyncio.create_task(report_loop(state)))

    # Background sync loop (every 5 minutes)
    async def sync_loop():
        while True:
            for acc in ACCOUNTS:
                await sync_positions(state, symbols, acc)
            await asyncio.sleep(300)
    tasks.append(asyncio.create_task(sync_loop()))

    # Daily reset of trades and PNL
    tasks.append(asyncio.create_task(reset_daily(state)))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())