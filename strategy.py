import pandas as pd
import ta

def add_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['ema_fast'] = ta.trend.EMAIndicator(df['close'], 9).ema_indicator()
    df['ema_mid'] = ta.trend.EMAIndicator(df['close'], 21).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(df['close'], 50).ema_indicator()
    df['vol_avg'] = df['volume'].rolling(14).mean()
    df['prev_close'] = df['close'].shift(1)
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], 14).average_true_range()
    return df

def score_trade(df):
    last = df.iloc[-1]
    score = 0
    if last['ema_fast'] > last['ema_mid'] > last['ema_slow']: score += 1
    if last['rsi'] > 45: score += 1
    if last['volume'] > 1.3 * last['vol_avg']: score += 1
    if last['close'] > last['prev_close']: score += 1
    if last['atr'] > 0: score += 1
    return score

def decide_buy(df):
    return score_trade(df) >= 3
