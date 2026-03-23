import asyncio, json, websockets
from logger import log_error, log_info
from notifier import alert

WS_URL = "wss://wbs.mexc.com/ws"

async def websocket_prices(symbols, cache):
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                for s in symbols:
                    await ws.send(json.dumps({
                        "method": "SUBSCRIPTION",
                        "params": [f"spot@public.deals.v3.api@{s}"],
                        "id": 1
                    }))
                log_info("WS Connected")

                while True:
                    data = json.loads(await ws.recv())
                    if "d" in data:
                        cache[data["s"]] = float(data["d"]["p"])
        except Exception as e:
            log_error(e)
            await alert(f"WS Down: {e}")
            await asyncio.sleep(5)