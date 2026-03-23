import pandas as pd

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def indicators(df):
    df['ema'] = df['c'].ewm(span=20).mean()
    df['rsi'] = rsi(df['c'])
    return df

def ai_signal_multi(df1, df5, df15):
    def score(df):
        return (df['rsi'].iloc[-1] > 50) + (df['c'].iloc[-1] > df['ema'].iloc[-1])
    return score(df1) + score(df5) + score(df15) >= 4