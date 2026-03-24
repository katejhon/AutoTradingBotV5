import asyncio
import time

from exchange_async import get_price, get_balance, market_buy, market_sell
from notifier import buy, sell, fail
from logger import log_info, log_error
from config import *
from strategy import ai_signal_multi, indicators


class Trader:
    def __init__(self, state, symbols, account):
        self.state = state
        self.symbols = symbols
        self.account = account

    async def get_klines(self, symbol, interval="1m"):
        import aiohttp
        import pandas as pd

        url = f"{BASE_URL}/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        df = pd.DataFrame(data)
        df.columns = ["t","o","h","l","c","v","ct","q"]

        for col in ["o","h","l","c","v"]:
            df[col] = df[col].astype(float)

        return df

    async def get_multi_tf(self, symbol):
        df1 = indicators(await self.get_klines(symbol, "1m"))
        df5 = indicators(await self.get_klines(symbol, "5m"))
        df15 = indicators(await self.get_klines(symbol, "15m"))
        return df1, df5, df15

    async def trade(self, symbol):

        if symbol in self.state.last_trade:
            if time.time() - self.state.last_trade[symbol] < COOLDOWN:
                return

        print(f"🔍 Checking {symbol}")

        try:
            df1, df5, df15 = await self.get_multi_tf(symbol)
        except Exception as e:
            log_error(f"Klines error {symbol}: {e}")
            return

        signal = ai_signal_multi(df1, df5, df15)

        if not signal:
            print(f"{symbol} ❌ No signal")
            return
        else:
            print(f"{symbol} ✅ SIGNAL")

        price = self.state.price_cache.get(symbol)

        if not price:
            try:
                price = await get_price(symbol)
                print(f"{symbol} ⚠️ Fallback price used")
            except:
                return

        if not self.state.can_trade():
            print("❌ Risk limit reached")
            return

        try:
            balance = await get_balance(self.account)
        except Exception as e:
            log_error(f"Balance error: {e}")
            return

        usdt = max(MIN_TRADE, balance * RISK_PER_TRADE)

        qty = float(f"{usdt / price:.6f}")

        print(f"💰 {symbol} | USDT: {usdt:.2f} | Price: {price:.4f} | Qty: {qty}")

        try:
            res = await market_buy(symbol, qty, self.account)

            if "orderId" not in res:
                raise Exception(res)

            tp = price * 1.1
            sl = price * 0.9

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

            log_info(f"✅ BUY {symbol} @ {price}")

        except Exception as e:
            log_error(f"BUY ERROR {symbol}: {e}")
            await fail(symbol, str(e))

    async def monitor(self):
        while True:
            for symbol, pos in list(self.state.positions.items()):

                price = self.state.price_cache.get(symbol)

                if not price:
                    try:
                        price = await get_price(symbol)
                    except:
                        continue

                if price > pos["trail_price"]:
                    pos["trail_price"] = price
                    pos["sl"] = price * (1 - pos["trail_percent"])
                    self.state.save()

                if price >= pos["tp"] or price <= pos["sl"]:
                    try:
                        res = await market_sell(symbol, pos["qty"], self.account)

                        pnl = (price - pos["entry"]) / pos["entry"] * 100

                        await sell(
                            symbol,
                            pos["qty"],
                            price * pos["qty"],
                            pnl
                        )

                        del self.state.positions[symbol]
                        self.state.save()

                        log_info(f"✅ SELL {symbol} | PNL: {pnl:.2f}%")

                    except Exception as e:
                        log_error(f"SELL ERROR {symbol}: {e}")
                        await fail(symbol, str(e))

            await asyncio.sleep(2)
