import pandas as pd

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def indicators(df):
    df['ema_fast'] = df['c'].ewm(span=7).mean()
    df['ema_mid'] = df['c'].ewm(span=14).mean()
    df['ema_slow'] = df['c'].ewm(span=28).mean()

    df['rsi'] = rsi(df['c'])
    df['vol_avg'] = df['v'].rolling(20).mean()
    df['momentum'] = df['c'].diff()

    return df

def trend_following(df):
    price = df['c'].iloc[-1]
    ema_mid = df['ema_mid'].iloc[-1]
    ema_slow = df['ema_slow'].iloc[-1]
    return price > ema_mid > ema_slow

def pullback_entry(df):
    price = df['c'].iloc[-1]
    ema_fast = df['ema_fast'].iloc[-1]
    rsi_v = df['rsi'].iloc[-1]
    return price < ema_fast and rsi_v > 45

def breakout_entry(df):
    price = df['c'].iloc[-1]
    high = df['c'].rolling(8).max().iloc[-2]
    return price > high

def scalp_entry(df):
    rsi_v = df['rsi'].iloc[-1]
    momentum = df['momentum'].iloc[-1]
    vol = df['v'].iloc[-1]
    vol_avg = df['vol_avg'].iloc[-1]
    return rsi_v > 48 and momentum > 0 and vol > vol_avg * 0.7

def analyze_tf(df):
    score = 0
    if trend_following(df):
        score += 2
    if pullback_entry(df):
        score += 1
    if breakout_entry(df):
        score += 2
    if scalp_entry(df):
        score += 2
    return score

def ai_signal_multi(df1, df5, df15):
    s1 = analyze_tf(df1)
    s5 = analyze_tf(df5)
    s15 = analyze_tf(df15)
    total = s1 + (s5 * 1.3) + (s15 * 1.6)
    return total >= 5