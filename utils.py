import hmac, hashlib, requests, time
from urllib.parse import urlencode

def sign(params, secret):
    q = urlencode(params)
    sig = hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    return f"{q}&signature={sig}"

def request(url, headers=None, method="GET", data=None):
    try:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=10).json()
        else:
            return requests.post(url, headers=headers, timeout=10, data=data).json()
    except Exception as e:
        print("Request error:", e)
        return {}

def safe_div(a, b):
    return a/b if b else 0
