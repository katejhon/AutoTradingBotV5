import time
from exchange_async import *
from notifier import *
from logger import log_info, log_error
from config import *

class Trader:
    def __init__(self, state, symbols, account):
        self.state = state
        self.symbols = symbols
        self.account = account

    async def trade(self, symbol):
        if symbol in self.state.last_trade and time.time() - self.state.last_trade[symbol] < COOLDOWN:
            return

        price = self.state.price_cache.get(symbol)
        if not price:
            return

        if not self.state.can_trade():
            return

        balance = await get_balance(self.account)
        usdt = max(MIN_TRADE, balance * RISK_PER_TRADE)
        qty = float(f"{usdt / price:.6f}")

        try:
            await market_buy(symbol, qty, self.account)

            tp = price * 1.01
            sl = price * 0.99

            self.state.positions[symbol] = {
                "entry": price,
                "qty": qty,
                "tp": tp,
                "sl": sl,
                "trail_price": price,
                "trail_percent": 0.005
            }

            self.state.save()
            await buy(symbol, price, qty, tp, sl)

            self.state.last_trade[symbol] = time.time()
            self.state.trades_today += 1
            self.state.save()

            log_info(f"BUY {symbol}")

        except Exception as e:
            log_error(e)
            await fail(symbol, str(e))

    async def monitor(self):
        while True:
            for symbol, pos in list(self.state.positions.items()):
                price = self.state.price_cache.get(symbol)
                if not price:
                    continue

                # trailing
                if price > pos["trail_price"]:
                    pos["trail_price"] = price
                    pos["sl"] = price * (1 - pos["trail_percent"])
                    self.state.save()

                if price >= pos["tp"] or price <= pos["sl"]:
                    try:
                        await market_sell(symbol, pos["qty"], self.account)

                        pnl = (price - pos["entry"]) / pos["entry"] * 100
                        await sell(symbol, pos["qty"], price * pos["qty"], pnl)

                        del self.state.positions[symbol]
                        self.state.save()

                    except Exception as e:
                        await fail(symbol, str(e))

            await asyncio.sleep(2)