import aiohttp, time, hmac, hashlib
from urllib.parse import urlencode
from config import BASE_URL

async def request(method, path, params={}, account=None):
    params["timestamp"] = int(time.time() * 1000)
    query = urlencode(params)

    sig = hmac.new(account["API_SECRET"].encode(), query.encode(), hashlib.sha256).hexdigest()
    query += f"&signature={sig}"

    headers = {"X-MEXC-APIKEY": account["API_KEY"]}

    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(BASE_URL + path + "?" + query, headers=headers) as r:
                return await r.json()
        else:
            async with session.post(BASE_URL + path, data=query, headers=headers) as r:
                return await r.json()

async def get_price(symbol):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}") as r:
            return float((await r.json())["price"])

async def get_top_symbols():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v3/ticker/24hr") as r:
            data = await r.json()
            return [d['symbol'] for d in sorted(data, key=lambda x: float(x['quoteVolume']), reverse=True) if "USDT" in d['symbol']][:50]

async def get_balance(account):
    data = await request("GET", "/api/v3/account", account=account)
    for b in data.get("balances", []):
        if b["asset"] == "USDT":
            return float(b["free"])
    return 0

async def market_buy(symbol, qty, account):
    return await request("POST", "/api/v3/order", {
        "symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": qty
    }, account)

async def market_sell(symbol, qty, account):
    return await request("POST", "/api/v3/order", {
        "symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": qty
    }, account)