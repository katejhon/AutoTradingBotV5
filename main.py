import asyncio
from telegram import Bot
from positions import load_positions, add_position, remove_position
from config import TELEGRAM_TOKEN, MIN_TRADE
from strategy import decide_buy, add_indicators
from orders import place_market, place_oco, get_price
from report import report_loop
import pandas as pd
from utils import request

async def trade_loop(bot):
    load_positions()
    await bot.send_message(chat_id=bot.chat_id, text="♻️ Bot restarted (ULTRA MODE)")
    while True:
        try:
            pairs = ["BTCUSDT","ETHUSDT","SOLUSDT"]  # replace with dynamic symbols if needed
            for symbol in pairs:
                price = get_price(symbol)
                if price <= 0: continue
                df = pd.DataFrame(request(f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"),
                                  columns=["open_time","open","high","low","close","volume","ct","qav","trades","tb","tq","ignore"])
                df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
                df = add_indicators(df)
                if symbol not in positions and decide_buy(df):
                    trade_usdt = max(MIN_TRADE, MIN_TRADE)
                    qty = trade_usdt / price
                    res = place_market(symbol, qty, "BUY", bot)
                    if "orderId" in res:
                        tp_price = price*1.01
                        sl_price = price*0.97
                        oco_id = place_oco(symbol, qty, tp_price, sl_price)
                        add_position(symbol, price, qty, tp_price, sl_price, oco_id)
                        await bot.send_message(chat_id=bot.chat_id,
                            text=f"✅ BUY\nToken: {symbol}\nPrice: {price}\nQty: {qty}\nTP: {tp_price}\nSL: {sl_price}")
        except Exception as e:
            await bot.send_message(chat_id=bot.chat_id,text=f"⚠️ ERROR: {e}")
        await asyncio.sleep(1)

async def main_runner():
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.chat_id = TELEGRAM_TOKEN
    asyncio.create_task(report_loop(bot))
    await trade_loop(bot)

if __name__=="__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(main_runner())
    else:
        asyncio.run(main_runner())
