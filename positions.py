import json
from config import POSITIONS_FILE

class Position:
    def __init__(self, symbol, entry, qty, tp_price, sl_price, oco_id=None):
        self.symbol = symbol
        self.entry = entry
        self.qty = qty
        self.tp_price = tp_price
        self.sl_price = sl_price
        self.oco_id = oco_id
        self.executed_qty = 0

positions = {}

def add_position(symbol, entry, qty, tp_price, sl_price, oco_id=None):
    positions[symbol] = Position(symbol, entry, qty, tp_price, sl_price, oco_id)
    save_positions()

def remove_position(symbol):
    if symbol in positions:
        del positions[symbol]
        save_positions()

def save_positions():
    data = {k: vars(v) for k,v in positions.items()}
    with open(POSITIONS_FILE, "w") as f:
        json.dump(data, f)

def load_positions():
    global positions
    try:
        with open(POSITIONS_FILE,"r") as f:
            data = json.load(f)
        for k,v in data.items():
            positions[k] = Position(**v)
    except FileNotFoundError:
        positions = {}
