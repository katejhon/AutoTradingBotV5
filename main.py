import asyncio
from state import BotState
from trader import Trader
from websocket import websocket_prices
from notifier import start
from exchange_async import get_top_symbols
from config import ACCOUNTS
from report import loop as report_loop

async def main():
    state = BotState()
    await start()

    symbols = await get_top_symbols()

    asyncio.create_task(websocket_prices(symbols, state.price_cache))

    tasks = []

    for acc in ACCOUNTS:
        trader = Trader(state, symbols, acc)
        tasks.append(trader.monitor())

        async def loop():
            while True:
                await asyncio.gather(*(trader.trade(s) for s in symbols))
                
                await asyncio.sleep(0.5)

        tasks.append(loop())

    await asyncio.gather(
    report_loop(state),
    *tasks
)

if __name__ == "__main__":
    asyncio.run(main())
