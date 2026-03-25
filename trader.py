import asyncio
import time
import aiohttp
import pandas as pd

from exchange_async import (
    get_price, get_balance,
    market_buy, market_sell,
    format_qty
)
from notifier import buy, sell, fail
from logger import log_info, log_error
from config import *
from strategy import ai_signal_multi, indicators

class Trader:
    def __init__(self, state, symbols, account):
        self.state = state
        self.symbols = symbols
        self.account = account
        self.failed_trades = {}  # Tracks consecutive failures per symbol

    async def get_klines(self, symbol, interval="1m"):
        url = f"{BASE_URL}/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        df = pd.DataFrame(data)
        df.columns =["t","o","h","l","c","v","ct","q"]
        for col in["o","h","l","c","v"]:
            df[col] = df[col].astype(float)
        return df

    async def get_multi_tf(self, symbol):
        # Fetch data concurrently for performance
        k1, k5, k15 = await asyncio.gather(
            self.get_klines(symbol, "1m"),
            self.get_klines(symbol, "5m"),
            self.get_klines(symbol, "15m")
        )
        return indicators(k1), indicators(k5), indicators(k15)

    async def trade(self, symbol):
        if symbol in self.state.last_trade:
            if time.time() - self.state.last_trade[symbol] < COOLDOWN:
                return

        log_info(f"🔍 Checking {symbol}")
        if symbol in self.state.positions:
            log_info(f"{symbol} ⚠️ Already holding")
            return

        try:
            df1, df5, df15 = await self.get_multi_tf(symbol)
        except Exception as e:
            log_error(f"Klines error {symbol}: {e}")
            return

        signal = ai_signal_multi(df1, df5, df15)
        if not signal:
            log_info(f"{symbol} ❌ No signal")
            return

        log_info(f"{symbol} ✅ SIGNAL")
        try:
            price = self.state.price_cache.get(symbol) or await get_price(symbol)
        except Exception as e:
            log_error(f"Price error {symbol}: {e}")
            return

        if not self.state.can_trade():
            log_info("❌ Risk limit reached")
            return

        try:
            balance = await get_balance(self.account)
        except Exception as e:
            log_error(f"Balance error: {e}")
            return

        # ✅ Increase trade size by $0.50 for every consecutive failure
        consecutive_fails = self.failed_trades.get(symbol, 0)
        base_trade_size = MIN_TRADE + (consecutive_fails * 0.5)
        
        # Use whichever is higher: the calculated base trade or the risk % of total balance
        usdt = max(base_trade_size, balance * RISK_PER_TRADE)
        
        # Format the quantity using the exact exchange rules
        raw_qty = usdt / price
        qty = format_qty(symbol, raw_qty)

        log_info(f"💰 {symbol} | USDT: {usdt:.2f} | Price: {price:.4f} | Target Qty: {qty} | Fails: {consecutive_fails}")

        try:
            await market_buy(symbol, qty, self.account)
            price = await get_price(symbol)

            # Check EXACT balance received after MEXC deducts their fee
            asset = symbol.replace("USDT", "")
            actual_qty = await get_balance(self.account, asset=asset)
            if actual_qty > 0:
                qty = actual_qty # Store the true, fee-adjusted balance

            tp = price * 1.012
            sl = price * 0.992
            trail_percent = 0.005

            # Store virtually, no exchange API calls needed!
            self.state.positions[symbol] = {
                "entry": price,
                "qty": qty,
                "tp": tp,
                "sl": sl,
                "trail_price": price,
                "trail_percent": trail_percent
            }

            await buy(symbol, price, qty, tp, sl)

            self.state.last_trade[symbol] = time.time()
            self.state.trades_today += 1
            await self.state.save()
            log_info(f"✅ BUY {symbol} @ {price} (Actual Qty: {qty})")

        except Exception as e:
            log_error(f"BUY ERROR {symbol}: {e}")
            await fail(symbol, str(e))
            # ✅ Increment failure counter on buy API failure
            self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1

    async def monitor(self):
        while True:
            for symbol, pos in list(self.state.positions.items()):
                try:
                    price = self.state.price_cache.get(symbol) or await get_price(symbol)

                    # ✅ VIRTUAL TAKE PROFIT CHECK
                    if price >= pos["tp"]:
                        try:
                            await market_sell(symbol, pos["qty"], self.account)
                            pnl_percent = ((price - pos["entry"]) / pos["entry"]) * 100
                            self.state.daily_pnl += pnl_percent
                            await sell(symbol, pos["qty"], price * pos["qty"], pnl_percent)
                            del self.state.positions[symbol]
                            await self.state.save()
                            log_info(f"✅ TP HIT {symbol} at {price}")
                            
                            # ✅ Reset failure counter on successful profitable trade
                            self.failed_trades[symbol] = 0
                            continue
                        except Exception as e:
                            log_error(f"TP Sell error {symbol}: {e}")

                    # ✅ VIRTUAL STOP LOSS CHECK
                    elif price <= pos["sl"]:
                        try:
                            await market_sell(symbol, pos["qty"], self.account)
                            pnl_percent = ((price - pos["entry"]) / pos["entry"]) * 100
                            self.state.daily_pnl += pnl_percent
                            await sell(symbol, pos["qty"], price * pos["qty"], pnl_percent)
                            del self.state.positions[symbol]
                            await self.state.save()
                            log_info(f"❌ SL HIT {symbol} at {price}")
                            
                            # ✅ Increment failure counter on Stop Loss hit
                            self.failed_trades[symbol] = self.failed_trades.get(symbol, 0) + 1
                            continue
                        except Exception as e:
                            log_error(f"SL Sell error {symbol}: {e}")

                    # ✅ VIRTUAL TRAILING STOP
                    if price > pos["trail_price"]:
                        old_sl = pos["sl"]
                        pos["trail_price"] = price
                        new_sl = price * (1 - pos["trail_percent"])

                        if new_sl > old_sl:
                            log_info(f"🔄 Updating trailing SL for {symbol} to {new_sl:.4f}")
                            pos["sl"] = new_sl
                            await self.state.save()

                except Exception as e:
                    log_error(f"Monitor error {symbol}: {e}")

            await asyncio.sleep(1)