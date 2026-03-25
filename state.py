import json, os
import aiofiles
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

    async def save(self):
        async with aiofiles.open("positions.json", "w") as f:
            await f.write(json.dumps(self.positions, indent=4))

        async with aiofiles.open("risk.json", "w") as f:
            await f.write(json.dumps({
                "trades_today": self.trades_today,
                "daily_pnl": self.daily_pnl
            }))

    def can_trade(self):
        return self.trades_today < MAX_TRADES_PER_DAY and self.daily_pnl > MAX_DRAWDOWN