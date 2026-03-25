from exchange_async import get_all_balances, request
from logger import log_info, log_error

async def sync_positions(state, symbols, account):
    try:
        balances = await get_all_balances(account)
        new_positions = {}

        for symbol in symbols:
            asset = symbol.replace("USDT", "")
            qty = balances.get(asset, 0)

            if qty <= 0:
                continue

            if symbol in state.positions:
                continue

            try:
                trades = await request("GET", "/api/v3/myTrades", {
                    "symbol": symbol,
                    "limit": 50
                }, account)

                total_qty = 0
                total_cost = 0

                for t in trades:
                    if t.get("isBuyer"):
                        q = float(t["qty"])
                        p = float(t["price"])
                        total_qty += q
                        total_cost += q * p

                if total_qty > 0:
                    entry = total_cost / total_qty
                    tp = entry * 1.01
                    sl = entry * 0.99

                    # ✅ NO API CALLS. Just create the virtual position!
                    new_positions[symbol] = {
                        "entry": entry,
                        "qty": qty,
                        "tp": tp,
                        "sl": sl,
                        "trail_price": entry,
                        "trail_percent": 0.005
                    }

            except Exception as e:
                log_error(f"Sync error {symbol}: {e}")
                continue

        if new_positions:
            state.positions.update(new_positions)
            await state.save()
            log_info("✅ Positions synced and Virtual TP/SL applied in memory")

    except Exception as e:
        log_error(f"SYNC FAILED: {e}")