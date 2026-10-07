import pandas as pd
import numpy as np
from typing import Dict, List, Any

def calculate_technical_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candles or len(candles) < 14:
        return {
            "rsi": 50.0,
            "sma_20": 0.0,
            "sma_50": 0.0,
            "ema_9": 0.0,
            "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0},
            "bollinger": {"upper": 0.0, "middle": 0.0, "lower": 0.0},
            "trend": "NEUTRAL",
            "score": 50.0,
            "signals": ["Insufficient data for calculation"]
        }
    
    df = pd.DataFrame(candles)
    closes = df["close"]
    
    # 1. RSI (14)
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    current_rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0

    # 2. Moving Averages
    sma_20 = float(closes.rolling(window=min(20, len(closes))).mean().iloc[-1])
    sma_50 = float(closes.rolling(window=min(50, len(closes))).mean().iloc[-1])
    ema_9 = float(closes.ewm(span=min(9, len(closes)), adjust=False).mean().iloc[-1])
    ema_21 = float(closes.ewm(span=min(21, len(closes)), adjust=False).mean().iloc[-1])
    
    # 3. MACD (12, 26, 9)
    ema_12 = closes.ewm(span=min(12, len(closes)), adjust=False).mean()
    ema_26 = closes.ewm(span=min(26, len(closes)), adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=min(9, len(closes)), adjust=False).mean()
    macd_hist = macd_line - signal_line
    
    curr_macd = float(macd_line.iloc[-1])
    curr_signal = float(signal_line.iloc[-1])
    curr_hist = float(macd_hist.iloc[-1])
    
    # 4. Bollinger Bands (20, 2)
    rolling_20 = closes.rolling(window=min(20, len(closes)))
    bb_middle = rolling_20.mean().iloc[-1]
    bb_std = rolling_20.std().iloc[-1]
    bb_upper = float(bb_middle + (bb_std * 2)) if not np.isnan(bb_std) else float(bb_middle * 1.05)
    bb_lower = float(bb_middle - (bb_std * 2)) if not np.isnan(bb_std) else float(bb_middle * 0.95)
    
    current_price = float(closes.iloc[-1])
    
    # 5. Technical Score & Stance Calculation
    score = 50.0
    signals = []
    
    # RSI Signals
    if current_rsi < 30:
        score += 25
        signals.append(f"RSI is oversold at {round(current_rsi, 1)} (Strong Buy signal)")
    elif current_rsi > 70:
        score -= 25
        signals.append(f"RSI is overbought at {round(current_rsi, 1)} (Sell signal)")
    else:
        signals.append(f"RSI is neutral at {round(current_rsi, 1)}")

    # MA Signals
    if current_price > sma_20 and current_price > sma_50:
        score += 20
        signals.append("Price is trading above 20-day and 50-day Moving Averages (Bullish trend)")
    elif current_price < sma_20 and current_price < sma_50:
        score -= 20
        signals.append("Price is trading below 20-day and 50-day Moving Averages (Bearish trend)")
        
    if ema_9 > ema_21:
        score += 15
        signals.append("9 EMA crossed above 21 EMA (Short-term momentum is positive)")
    else:
        score -= 15
        signals.append("9 EMA is below 21 EMA (Short-term momentum is negative)")

    # MACD Signals
    if curr_hist > 0 and curr_macd > curr_signal:
        score += 15
        signals.append("MACD histogram is positive and line is above signal")
    elif curr_hist < 0:
        score -= 15
        signals.append("MACD histogram is negative")

    # Clamp score
    score = max(0.0, min(100.0, score))
    
    if score >= 65:
        stance = "BULLISH"
    elif score <= 35:
        stance = "BEARISH"
    else:
        stance = "NEUTRAL"
        
    return {
        "rsi": round(current_rsi, 2),
        "sma_20": round(sma_20, 2),
        "sma_50": round(sma_50, 2),
        "ema_9": round(ema_9, 2),
        "ema_21": round(ema_21, 2),
        "macd": {
            "macd": round(curr_macd, 2),
            "signal": round(curr_signal, 2),
            "histogram": round(curr_hist, 2)
        },
        "bollinger": {
            "upper": round(bb_upper, 2),
            "middle": round(float(bb_middle), 2),
            "lower": round(bb_lower, 2)
        },
        "trend": stance,
        "score": round(score, 1),
        "signals": signals
    }
