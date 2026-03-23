import asyncio
from exchange_async import get_all_balances, get_price
from notifier import bot
from config import CHAT_ID
from state import BotState

async def report(state: BotState):
    balances = await get_all_balances()
    total_balance = 0
    data = []

    active_assets = set(balances.keys())
    for symbol in list(state.positions.keys()):
        asset = symbol.replace("USDT", "")
        if asset not in active_assets:
            del state.positions[symbol]

    state.save_positions()

    for asset, qty in balances.items():
        if qty <= 0: continue
        if asset == "USDT":
            total_balance += qty
            continue

        symbol = asset + "USDT"
        try:
            price = await get_price(symbol)
            value = price * qty
            total_balance += value
            if symbol in state.positions:
                entry = state.positions[symbol]['entry']
                pnl = (price - entry) / entry * 100
            else:
                pnl = 0
            data.append({"symbol": symbol, "price": price, "qty": qty, "value": value, "pnl": pnl})
        except:
            continue

    data.sort(key=lambda x: x["pnl"], reverse=True)
    total_pnl = sum(d["pnl"] for d in data) if data else 0

    msg = f"""📊 5-MIN REPORT
💰 Balance: {total_balance:.2f} USDT
📈 PNL: {total_pnl:.2f}%"""
    for d in data:
        msg += f"""
{d['symbol']}
Token Price: {d['price']}
Qty: {d['qty']}
Value: {d['value']:.2f} USDT
PNL: {d['pnl']:.2f}%"""
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def loop(state: BotState):
    while True:
        try:
            await report(state)
        except Exception as e:
            print("Report error:", e)
        await asyncio.sleep(300)