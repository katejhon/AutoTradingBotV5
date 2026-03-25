import asyncio
from exchange_async import get_all_balances, get_price
from notifier import bot
from config import CHAT_ID, ACCOUNTS
from state import BotState

async def report(state: BotState):
    balances = await get_all_balances(ACCOUNTS[0])
    total_balance = 0
    data = []

    MIN_VALUE = 0.1
    active_assets = {a for a, q in balances.items() if q > 0}

    for symbol in list(state.positions.keys()):
        asset = symbol.replace("USDT", "")
        if asset not in active_assets:
            del state.positions[symbol]

    await state.save()

    for asset, qty in balances.items():
        if qty <= 0:
            continue
        if asset == "USDT":
            total_balance += qty
            continue
        symbol = asset + "USDT"
        try:
            price = await get_price(symbol)
            value = price * qty
            if value < MIN_VALUE:
                continue
            total_balance += value
            pnl = 0
            if symbol in state.positions:
                entry = state.positions[symbol]["entry"]
                pnl = (price - entry) / entry * 100
            data.append({"symbol": symbol, "price": price, "qty": qty, "value": value, "pnl": pnl})
        except:
            continue

    data.sort(key=lambda x: x["pnl"], reverse=True)

    total_value = sum(d["value"] for d in data)
    total_cost = sum(d["value"] / (1 + d["pnl"]/100) if d["pnl"] != -100 else d["value"] for d in data)
    total_pnl = ((total_value - total_cost) / total_cost * 100) if total_cost else 0

    msg = f"""📊 5-MIN REPORT
💰 Balance: {total_balance:.2f} USDT
📈 PNL: {total_pnl:.2f}%"""

    for d in data:
        msg += f"""

{d['symbol']}
Token Price: {d['price']:.2f}
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
        await asyncio.sleep(300)  # 5 minutes