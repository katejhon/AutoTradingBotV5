import aiohttp, time, hmac, hashlib, asyncio
import math
from urllib.parse import urlencode
from config import BASE_URL
from logger import log_error

session = None

# ================= PRECISION & FORMATTING =================
SYMBOL_PRECISIONS = {}

async def load_precisions():
    try:
        session = await get_session()
        async with session.get(f"{BASE_URL}/api/v3/exchangeInfo") as r:
            data = await r.json()
            for s in data.get("symbols",[]):
                # Save the exact allowed decimal places for every token
                SYMBOL_PRECISIONS[s["symbol"]] = s.get("baseAssetPrecision", 4)
        print("✅ Exchange Token Precisions Loaded")
    except Exception as e:
        print(f"Failed to load precisions: {e}")

def format_qty(symbol, qty):
    prec = SYMBOL_PRECISIONS.get(symbol, 4)
    if prec == 0:
        return float(math.floor(qty))
    multiplier = 10 ** prec
    truncated = math.floor(qty * multiplier) / multiplier
    return float(f"{truncated:.{prec}f}")

# ================= SESSION =================
async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session

# ================= CORE REQUEST =================
async def request(method, path, params=None, account=None):
    try:
        if params is None:
            params = {}

        # Add timestamp
        params["timestamp"] = int(time.time() * 1000)

        # Build query string for signature (MEXC requires sorted parameters)
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            account["API_SECRET"].encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Everything goes into the URL
        full_url = f"{BASE_URL}{path}?{query_string}&signature={signature}"
        session = await get_session()

        headers = {
            "X-MEXC-APIKEY": account["API_KEY"],
            "Content-Type": "application/json"
        }

        if method.upper() in ["POST", "DELETE"]:
            # FIX: Send an empty JSON body to satisfy MEXC's firewall
            async with session.request(method, full_url, headers=headers, json={}) as r:
                data = await r.json()
        else:
            # GET requests don't need a body
            async with session.request(method, full_url, headers=headers) as r:
                data = await r.json()

        # Check for API error (Accepts code 0 or 200 as success)
        if isinstance(data, dict) and data.get("code") not in (None, 0, 200):
            log_error(f"API ERROR: {data}")
            raise Exception(data)

        return data

    except Exception as e:
        log_error(f"REQUEST ERROR: {e}")
        raise

# ================= MARKET DATA =================
async def get_price(symbol):
    s = await get_session()
    async with s.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}") as r:
        return float((await r.json())["price"])

async def get_top_symbols():
    s = await get_session()
    async with s.get(f"{BASE_URL}/api/v3/ticker/24hr") as r:
        data = await r.json()
        return [
            d["symbol"]
            for d in sorted(data, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
            if "USDT" in d["symbol"] and "(" not in d["symbol"]
        ][:20]

# ================= ACCOUNT =================
async def get_balance(account, asset="USDT"):
    data = await request("GET", "/api/v3/account", account=account)
    for b in data.get("balances", []):
        if b["asset"] == asset:
            return float(b["free"])
    return 0

async def get_all_balances(account):
    data = await request("GET", "/api/v3/account", account=account)
    balances = {}
    for b in data.get("balances", []):
        total = float(b.get("free", 0)) + float(b.get("locked", 0))
        if total > 0:
            balances[b["asset"]] = total
    return balances

# ================= TRADING =================
async def market_buy(symbol, qty, account):
    order = await request("POST", "/api/v3/order", {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quantity": qty
    }, account)

    order_id = order.get("orderId")
    if not order_id:
        raise Exception(f"Buy order failed: {order}")

    for _ in range(5):
        status = await get_order(symbol, order_id, account)
        if status.get("status") == "FILLED":
            return order
        await asyncio.sleep(0.5)
    raise Exception("BUY not filled")

async def market_sell(symbol, qty, account):
    order = await request("POST", "/api/v3/order", {
        "symbol": symbol,
        "side": "SELL",
        "type": "MARKET",
        "quantity": qty
    }, account)

    order_id = order.get("orderId")
    if not order_id:
        raise Exception(f"Sell order failed: {order}")

    for _ in range(5):
        status = await get_order(symbol, order_id, account)
        if status.get("status") == "FILLED":
            return order
        await asyncio.sleep(0.5)
    raise Exception("SELL not filled")

async def cancel_order(symbol, order_id, account):
    return await request("DELETE", "/api/v3/order", {
        "symbol": symbol,
        "orderId": order_id
    }, account)

async def get_order(symbol, order_id, account):
    return await request("GET", "/api/v3/order", {
        "symbol": symbol,
        "orderId": order_id
    }, account)

async def is_order_filled(symbol, order_id, account):
    try:
        order = await get_order(symbol, order_id, account)
        return order.get("status") in ["FILLED", "PARTIALLY_FILLED"]
    except:
        return False

async def place_tp_sl(symbol, qty, tp, sl, account):
    return await request("POST", "/api/v3/order/oco", {
        "symbol": symbol,
        "side": "SELL", # <-- THIS WAS MISSING
        "quantity": qty,
        "price": f"{tp:.6f}",
        "stopPrice": f"{sl:.6f}",
        "stopLimitPrice": f"{sl:.6f}",
        "stopLimitTimeInForce": "GTC"
    }, account)

async def get_trades(symbol, account):
    return await request("GET", "/api/v3/myTrades", {
        "symbol": symbol,
        "limit": 50
    }, account)