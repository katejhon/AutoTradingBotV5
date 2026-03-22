import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MEXC_API_KEY")
API_SECRET = os.getenv("MEXC_SECRET_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://api.mexc.com"
WS_URL = "wss://wbs.mexc.com/ws"

MIN_TRADE = 5          # minimum per trade in USDT
ADJUST_STEP = 0.5      # auto-adjust step for failed trade
REPORT_INTERVAL = 300  # 5-min report
POSITIONS_FILE = "positions.json"
MAX_OPEN_TRADES = 20
