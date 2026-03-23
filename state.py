import json, os
from config import *

class BotState:
    def __init__(self):
        self.positions = {}
        self.last_trade = {}
        self.price_cache = {}
        self.trades_today = 0
        self.daily_pnl = 0
        self.load()

    def load(self):
        if os.path.exists("positions.json"):
            with open("positions.json") as f:
                self.positions = json.load(f)

        if os.path.exists("risk.json"):
            with open("risk.json") as f:
                r = json.load(f)
                self.trades_today = r.get("trades_today", 0)
                self.daily_pnl = r.get("daily_pnl", 0)

    def save(self):
        with open("positions.json", "w") as f:
            json.dump(self.positions, f, indent=4)

        with open("risk.json", "w") as f:
            json.dump({
                "trades_today": self.trades_today,
                "daily_pnl": self.daily_pnl
            }, f)

    def can_trade(self):
        return self.trades_today < MAX_TRADES_PER_DAY and self.daily_pnl > MAX_DRAWDOWN