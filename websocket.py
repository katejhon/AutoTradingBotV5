import asyncio, json, websockets
from logger import log_error, log_info

WS_URL = "wss://wbs.mexc.com/ws"

async def websocket_prices(symbols, cache):
    while True:
        try:
            async with websockets.connect(
                WS_URL,
                ping_interval=20,
                ping_timeout=10
            ) as ws:

                for s in symbols:
                    await ws.send(json.dumps({
                        "method": "SUBSCRIPTION",
                        "params": [f"spot@public.ticker.v3.api@{s}"],
                        "id": 1
                    }))

                log_info("✅ WebSocket Connected")

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)

                        if isinstance(data, dict) and "d" in data:
                            try:
                                symbol = data.get("s")
                                price = float(data["d"].get("c", 0))

                                if symbol and price > 0:
                                    cache[symbol] = price

                            except Exception:
                                continue

                    except asyncio.TimeoutError:
                        await ws.ping()

        except Exception as e:
            log_error(f"WS Error: {e}")
            log_error("🔁 Reconnecting WebSocket...")
            await asyncio.sleep(5)
