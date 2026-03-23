from telegram import Bot
from config import *

bot = Bot(token=TELEGRAM_TOKEN)

async def start():
    await bot.send_message(chat_id=CHAT_ID, text="🤖 Bot Started (Version 1.0.2")

async def buy(symbol, price, qty, tp, sl):
    await bot.send_message(chat_id=CHAT_ID, text=f"""✅ BUY
Token: {symbol}
Price: {price}
Qty: {qty}
TP: {tp}
SL: {sl}""")

async def sell(symbol, qty, amount, pnl):
    await bot.send_message(chat_id=CHAT_ID, text=f"""✅ Sell
Token: {symbol}
Qty: {qty}
Amount: {amount:.2f} USDT
PNL: {pnl:.2f}%""")

async def fail(symbol, reason):
    await bot.send_message(chat_id=CHAT_ID, text=f"""⚠️ Failed
Token: {symbol}
Reason: {reason}""")

async def alert(msg):
    await bot.send_message(chat_id=CHAT_ID, text=f"🚨 ALERT\n{msg}")