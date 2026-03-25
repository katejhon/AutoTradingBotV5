import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.mexc.com"

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_SECRET_KEY")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MIN_TRADE = 5
RISK_PER_TRADE = 0.10
MAX_TRADES_PER_DAY = 100
MAX_DRAWDOWN = -5
COOLDOWN = 3600  # 1 hour

ACCOUNTS = [
    {
        "API_KEY": API_KEY,
        "API_SECRET": API_SECRET,
        "NAME": "MAIN"
    }
]