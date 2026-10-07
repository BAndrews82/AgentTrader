import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import urllib.request
import os
import math
import random
import hashlib
import threading
import time
import sys
import subprocess
import shutil
import atexit
import signal
from datetime import datetime, timedelta, timezone

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "trading.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# Auto-load backend/.env if present
ENV_PATH = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
        print("Successfully loaded environment variables from backend/.env")
    except Exception as e:
        print(f"Notice: Could not load .env file: {e}")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cash_balance REAL DEFAULT 100000.0,
            initial_capital REAL DEFAULT 100000.0,
            currency TEXT DEFAULT 'USD',
            circuit_breaker_active BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            asset_type TEXT DEFAULT 'Stock',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            rsi_buy_threshold REAL DEFAULT 35.0,
            rsi_sell_threshold REAL DEFAULT 70.0,
            ma_fast INTEGER DEFAULT 20,
            ma_slow INTEGER DEFAULT 50,
            use_ma_cross BOOLEAN DEFAULT 1,
            use_agent_consensus BOOLEAN DEFAULT 1,
            agent_min_confidence REAL DEFAULT 70.0,
            weight_technical REAL DEFAULT 0.35,
            weight_sentiment REAL DEFAULT 0.25,
            weight_risk REAL DEFAULT 0.40,
            risk_veto_enabled BOOLEAN DEFAULT 1,
            allocation_amount REAL DEFAULT 5000.0,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            asset_type TEXT DEFAULT 'Stock',
            shares REAL NOT NULL DEFAULT 0.0,
            avg_cost REAL NOT NULL DEFAULT 0.0,
            current_price REAL NOT NULL DEFAULT 0.0,
            peak_price REAL NOT NULL DEFAULT 0.0,
            unrealized_pnl REAL DEFAULT 0.0,
            realized_pnl REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            shares REAL NOT NULL,
            price REAL NOT NULL,
            total_value REAL NOT NULL,
            order_type TEXT DEFAULT 'MARKET',
            status TEXT DEFAULT 'FILLED',
            triggered_by TEXT DEFAULT 'MANUAL',
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_equity REAL NOT NULL,
            cash_balance REAL NOT NULL,
            positions_value REAL NOT NULL,
            cumulative_pnl REAL DEFAULT 0.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            stance TEXT NOT NULL,
            confidence REAL NOT NULL,
            reasoning TEXT NOT NULL,
            target_price REAL,
            stop_loss REAL,
            take_profit REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_name TEXT DEFAULT 'WhatsApp / Discord / Telegram',
            whatsapp_number TEXT DEFAULT '',
            discord_webhook_url TEXT DEFAULT '',
            telegram_bot_token TEXT DEFAULT '',
            telegram_chat_id TEXT DEFAULT '',
            notify_on_trades BOOLEAN DEFAULT 1,
            notify_on_stoploss BOOLEAN DEFAULT 1,
            notify_on_ai_debate BOOLEAN DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight_technical REAL DEFAULT 0.35,
            weight_sentiment REAL DEFAULT 0.25,
            weight_risk REAL DEFAULT 0.40,
            risk_veto_enabled BOOLEAN DEFAULT 1,
            min_confidence REAL DEFAULT 70.0,
            prompt_technical TEXT DEFAULT 'Focus on chart setups, RSI oversold/overbought thresholds, VWAP support, and Moving Average crossovers.',
            prompt_sentiment TEXT DEFAULT 'Evaluate news headline momentum, corporate earnings catalysts, and market sentiment.',
            prompt_risk TEXT DEFAULT 'Evaluate portfolio drawdown risk, calculate 5% trailing stops, position limits, and risk-to-reward ratio.'
        )
    """)
    
    # Seed default account
    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account (cash_balance, initial_capital) VALUES (100000.0, 100000.0)")

    # Seed default webhook settings if empty
    cursor.execute("SELECT COUNT(*) FROM webhook_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO webhook_settings (channel_name) VALUES ('Default Channel Config')")

    cursor.execute("SELECT COUNT(*) FROM agent_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO agent_config (id) VALUES (1)")

    # Seed default watchlist
    cursor.execute("SELECT COUNT(*) FROM watchlist")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("AAPL", "Apple Inc.", "Stock"),
            ("NVDA", "NVIDIA Corporation", "Stock"),
            ("SPY", "SPDR S&P 500 ETF Trust", "ETF"),
            ("QQQ", "Invesco QQQ Trust", "ETF"),
            ("TSLA", "Tesla, Inc.", "Stock"),
            ("VOO", "Vanguard S&P 500 ETF", "ETF"),
            ("SCHD", "Schwab U.S. Dividend ETF", "ETF")
        ]
        cursor.executemany("INSERT OR IGNORE INTO watchlist (symbol, name, asset_type) VALUES (?, ?, ?)", defaults)

    # Seed default strategies
    cursor.execute("SELECT COUNT(*) FROM strategies")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, weight_technical, weight_sentiment, weight_risk, risk_veto_enabled, allocation_amount, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('S&P 500 Dip & Risk Veto Strategy', 'SPY', 35.0, 70.0, 20, 50, 1, 1, 70.0, 0.35, 0.25, 0.40, 1, 5000.0, 1))

        cursor.execute("""
            INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, weight_technical, weight_sentiment, weight_risk, risk_veto_enabled, allocation_amount, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Tech Growth Momentum & Risk Veto', 'NVDA', 40.0, 75.0, 9, 21, 1, 1, 75.0, 0.40, 0.20, 0.40, 1, 7500.0, 1))

    conn.commit()
    conn.close()

# --- WEBHOOK DISPATCHER (WhatsApp, Discord, Telegram) ---
def send_webhook_alert(title, message, alert_type="TRADE"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM webhook_settings LIMIT 1")
    setting = cursor.fetchone()
    conn.close()

    if not setting: return

    s = dict(setting)
    full_text = f"🚨 AgentTrader Alert [{alert_type}]\n* {title}\n{message}"

    # 1. Discord Webhook
    if s.get("discord_webhook_url"):
        try:
            req = urllib.request.Request(
                s["discord_webhook_url"],
                data=json.dumps({"content": full_text}).encode('utf-8'),
                headers={'Content-Type': 'application/json', 'User-Agent': 'AgentTrader/2.0'}
            )
            urllib.request.urlopen(req, timeout=3)
            print("Dispatched Discord Webhook Alert")
        except Exception as e:
            print("Discord webhook notice:", e)

    # 2. Telegram Bot Webhook
    if s.get("telegram_bot_token") and s.get("telegram_chat_id"):
        try:
            url = f"https://api.telegram.org/bot{s['telegram_bot_token']}/sendMessage"
            payload = {"chat_id": s["telegram_chat_id"], "text": full_text, "parse_mode": "Markdown"}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req, timeout=3)
            print("Dispatched Telegram Bot Alert")
        except Exception as e:
            print("Telegram webhook notice:", e)

# --- MARKET DATA & EXPANDED INDICATOR SUITE ---
POPULAR = {
    "AAPL": {"name": "Apple Inc.", "asset_type": "Stock", "base": 228.50},
    "NVDA": {"name": "NVIDIA Corporation", "asset_type": "Stock", "base": 122.40},
    "MSFT": {"name": "Microsoft Corporation", "asset_type": "Stock", "base": 415.20},
    "AMZN": {"name": "Amazon.com Inc.", "asset_type": "Stock", "base": 186.30},
    "GOOGL": {"name": "Alphabet Inc.", "asset_type": "Stock", "base": 165.70},
    "TSLA": {"name": "Tesla, Inc.", "asset_type": "Stock", "base": 245.10},
    "SPY": {"name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF", "base": 560.80},
    "QQQ": {"name": "Invesco QQQ Trust", "asset_type": "ETF", "base": 485.40},
    "VOO": {"name": "Vanguard S&P 500 ETF", "asset_type": "ETF", "base": 512.90},
    "IWM": {"name": "iShares Russell 2000 ETF", "asset_type": "ETF", "base": 218.60},
    "SCHD": {"name": "Schwab U.S. Dividend ETF", "asset_type": "ETF", "base": 82.30},
    "AMD": {"name": "Advanced Micro Devices", "asset_type": "Stock", "base": 154.20}
}

def _get_symbol_random(symbol, offset=0):
    hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    seed_str = f"{symbol}_{hour_key}_{offset}"
    h = int(hashlib.md5(seed_str.encode('utf-8')).hexdigest(), 16)
    return (h % 100000) / 100000.0

def get_quote(symbol):
    sym = symbol.strip().upper()
    info = POPULAR.get(sym, {"name": f"{sym} Corp", "asset_type": "Stock", "base": 150.0})
    base = info["base"]
    
    r1 = _get_symbol_random(sym, 1)
    r2 = _get_symbol_random(sym, 2)
    
    change_pct = (r1 - 0.47) * 0.025
    curr = round(base * (1 + change_pct), 2)
    prev = round(base, 2)
    chg = round(curr - prev, 2)
    pct = round((chg / prev * 100) if prev else 0.0, 2)
    vol = int(1000000 + (r2 * 8000000))
    
    return {
        "symbol": sym,
        "name": info["name"],
        "asset_type": info["asset_type"],
        "current_price": curr,
        "previous_close": prev,
        "change": chg,
        "percent_change": pct,
        "day_high": round(max(curr, prev) * 1.012, 2),
        "day_low": round(min(curr, prev) * 0.988, 2),
        "volume": vol,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

PROFILES = {
    "AAPL": {
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "description": "Apple Inc. designs, manufactures, and markets smartphones (iPhone), personal computers (Mac), tablets (iPad), wearables, and accessories, alongside digital services like Apple Music, iCloud, and Apple Pay.",
        "market_cap": 3450000000000.0,
        "pe_ratio": 33.5,
        "forward_pe": 28.4,
        "eps": 6.57,
        "dividend_yield": 0.52,
        "beta": 1.08,
        "week52_high": 237.23,
        "week52_low": 164.08,
        "volume_24h": 48200000,
        "avg_volume": 52100000,
        "related_stocks": [
            {"symbol": "MSFT", "name": "Microsoft Corporation", "asset_type": "Stock"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "asset_type": "Stock"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "Stock"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_type": "Stock"}
        ]
    },
    "NVDA": {
        "sector": "Technology",
        "industry": "Semiconductors & AI Hardware",
        "description": "NVIDIA Corporation pioneers accelerated computing and GPU hardware, fueling generative AI models, data centers, autonomous vehicles, and high-performance gaming technologies worldwide.",
        "market_cap": 3120000000000.0,
        "pe_ratio": 64.2,
        "forward_pe": 38.1,
        "eps": 1.90,
        "dividend_yield": 0.03,
        "beta": 1.68,
        "week52_high": 140.76,
        "week52_low": 39.23,
        "volume_24h": 84100000,
        "avg_volume": 79400000,
        "related_stocks": [
            {"symbol": "AMD", "name": "Advanced Micro Devices", "asset_type": "Stock"},
            {"symbol": "INTC", "name": "Intel Corporation", "asset_type": "Stock"},
            {"symbol": "TSM", "name": "Taiwan Semiconductor", "asset_type": "Stock"},
            {"symbol": "AVGO", "name": "Broadcom Inc.", "asset_type": "Stock"}
        ]
    },
    "MSFT": {
        "sector": "Technology",
        "industry": "Systems Software & Cloud",
        "description": "Microsoft Corporation develops cloud computing (Azure), enterprise software (Windows, Office 365), cybersecurity, developer tools (GitHub), and consumer technology (Xbox, Surface).",
        "market_cap": 3080000000000.0,
        "pe_ratio": 34.8,
        "forward_pe": 29.1,
        "eps": 11.80,
        "dividend_yield": 0.72,
        "beta": 0.89,
        "week52_high": 468.35,
        "week52_low": 327.00,
        "volume_24h": 21500000,
        "avg_volume": 23000000,
        "related_stocks": [
            {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "Stock"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "asset_type": "Stock"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_type": "Stock"},
            {"symbol": "ORCL", "name": "Oracle Corporation", "asset_type": "Stock"}
        ]
    },
    "SPY": {
        "sector": "Financial / Broad Market",
        "industry": "Index ETF (S&P 500)",
        "description": "The SPDR S&P 500 ETF Trust seeks to provide investment results that correspond generally to the price and yield performance of the S&P 500 Index, representing 500 leading U.S. large-cap companies.",
        "market_cap": 560000000000.0,
        "pe_ratio": 27.2,
        "forward_pe": 22.1,
        "eps": 21.40,
        "dividend_yield": 1.25,
        "beta": 1.00,
        "week52_high": 565.16,
        "week52_low": 410.00,
        "volume_24h": 62400000,
        "avg_volume": 65000000,
        "related_stocks": [
            {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "asset_type": "ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_type": "ETF"},
            {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "asset_type": "ETF"},
            {"symbol": "SCHD", "name": "Schwab U.S. Dividend ETF", "asset_type": "ETF"}
        ]
    },
    "QQQ": {
        "sector": "Financial / Tech Index",
        "industry": "Index ETF (Nasdaq 100)",
        "description": "Invesco QQQ Trust is an exchange-traded fund that tracks the Nasdaq-100 Index, holding top non-financial innovative technology leaders including Apple, Microsoft, NVIDIA, Amazon, and Alphabet.",
        "market_cap": 285000000000.0,
        "pe_ratio": 31.4,
        "forward_pe": 26.8,
        "eps": 15.20,
        "dividend_yield": 0.58,
        "beta": 1.18,
        "week52_high": 503.52,
        "week52_low": 350.00,
        "volume_24h": 38100000,
        "avg_volume": 42000000,
        "related_stocks": [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF"},
            {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "asset_type": "ETF"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "Stock"},
            {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "Stock"}
        ]
    },
    "TSLA": {
        "sector": "Consumer Cyclical",
        "industry": "Electric Vehicles & Clean Energy",
        "description": "Tesla, Inc. designs, manufactures, sells, and leases electric vehicles (Model S 3 X Y, Cybertruck), stationary energy storage systems (Powerwall, Megapack), and solar energy solutions.",
        "market_cap": 780000000000.0,
        "pe_ratio": 72.4,
        "forward_pe": 55.0,
        "eps": 3.40,
        "dividend_yield": 0.00,
        "beta": 2.34,
        "week52_high": 271.00,
        "week52_low": 138.80,
        "volume_24h": 72000000,
        "avg_volume": 85000000,
        "related_stocks": [
            {"symbol": "RIVN", "name": "Rivian Automotive", "asset_type": "Stock"},
            {"symbol": "LCID", "name": "Lucid Group", "asset_type": "Stock"},
            {"symbol": "F", "name": "Ford Motor Company", "asset_type": "Stock"},
            {"symbol": "GM", "name": "General Motors", "asset_type": "Stock"}
        ]
    },
    "SCHD": {
        "sector": "Financial / Dividend",
        "industry": "Dividend ETF",
        "description": "Schwab U.S. Dividend Equity ETF tracks the Dow Jones U.S. Dividend 100 Index, focusing on high dividend yield fundamentals, strong cash flow, and dividend growth history.",
        "market_cap": 58000000000.0,
        "pe_ratio": 16.4,
        "forward_pe": 14.8,
        "eps": 5.02,
        "dividend_yield": 3.42,
        "beta": 0.78,
        "week52_high": 84.50,
        "week52_low": 68.20,
        "volume_24h": 3200000,
        "avg_volume": 3800000,
        "related_stocks": [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF"},
            {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "asset_type": "ETF"},
            {"symbol": "VYM", "name": "Vanguard High Dividend Yield", "asset_type": "ETF"},
            {"symbol": "DGRO", "name": "iShares Core Dividend Growth", "asset_type": "ETF"}
        ]
    }
}

def get_stock_profile(symbol):
    sym = symbol.strip().upper()
    quote = get_quote(sym)
    prof = PROFILES.get(sym, {
        "sector": "Equity / Capital Markets",
        "industry": f"{quote['asset_type']} Asset Class",
        "description": f"{quote['name']} ({sym}) is an active publicly traded asset. Its price trends are monitored real-time by AgentTrader Gemini 3.8 Flash technical and risk consensus agents.",
        "market_cap": round(quote["current_price"] * 1250000000.0, 2),
        "pe_ratio": 24.8,
        "forward_pe": 20.5,
        "eps": round(quote["current_price"] / 24.8, 2),
        "dividend_yield": 1.15 if quote["asset_type"] == "ETF" else 0.65,
        "beta": 1.05,
        "week52_high": round(quote["current_price"] * 1.18, 2),
        "week52_low": round(quote["current_price"] * 0.82, 2),
        "volume_24h": quote["volume"],
        "avg_volume": int(quote["volume"] * 1.1),
        "related_stocks": [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_type": "ETF"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "Stock"},
            {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "Stock"}
        ]
    })
    
    return {**quote, **prof}

def get_candles(symbol, days=90):
    sym = symbol.strip().upper()
    base = POPULAR.get(sym, {}).get("base", 150.0)
    
    candles = []
    curr = base * 0.88
    now = datetime.now()
    
    for i in range(days, -1, -1):
        dt = now - timedelta(days=i)
        if dt.weekday() >= 5:
            continue
        
        seed_str = f"{sym}_{dt.strftime('%Y-%m-%d')}"
        h_val = int(hashlib.md5(seed_str.encode('utf-8')).hexdigest(), 16)
        r_ret = ((h_val % 1000) / 1000.0 - 0.485) * 0.035
        r_high = (((h_val >> 4) % 1000) / 1000.0) * 0.015
        r_low = (((h_val >> 8) % 1000) / 1000.0) * 0.015
        r_vol = 1500000 + (((h_val >> 12) % 10000) * 750)
        
        open_p = curr
        close_p = open_p * (1 + r_ret)
        high_p = max(open_p, close_p) * (1 + r_high)
        low_p = min(open_p, close_p) * (1 - r_low)
        vol = int(r_vol)
        curr = close_p
        
        candles.append({
            "time": dt.strftime("%Y-%m-%d"),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": vol
        })
    return candles

def calculate_indicators(candles):
    if not candles or len(candles) < 14:
        return {
            "rsi": 50.0, "sma_20": 0.0, "sma_50": 0.0, "ema_9": 0.0, "ema_21": 0.0,
            "vwap": 0.0, "stochastic": {"k": 50.0, "d": 50.0}, "atr": 2.5,
            "fibonacci": {"level_236": 0.0, "level_382": 0.0, "level_500": 0.0, "level_618": 0.0},
            "score": 50.0, "trend": "NEUTRAL", "signals": ["Insufficient candle data"]
        }
        
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    vols = [c["volume"] for c in candles]
    length = len(closes)
    curr_price = closes[-1]
    
    # 1. RSI (14)
    gains, losses = 0.0, 0.0
    for i in range(length - 14, length):
        diff = closes[i] - closes[i-1]
        if diff >= 0: gains += diff
        else: losses += abs(diff)
    avg_gain = gains / 14
    avg_loss = losses / 14
    rs = (avg_gain / avg_loss) if avg_loss > 0 else 100.0
    rsi = round(100.0 - (100.0 / (1.0 + rs)), 2)

    # 2. Moving Averages
    sma_20 = round(sum(closes[-20:]) / min(20, length), 2)
    sma_50 = round(sum(closes[-50:]) / min(50, length), 2)

    def calc_ema(span):
        k = 2 / (span + 1)
        val = closes[0]
        for c in closes[1:]:
            val = (c * k) + (val * (1 - k))
        return round(val, 2)

    ema_9 = calc_ema(9)
    ema_21 = calc_ema(21)
    ema_12 = calc_ema(12)
    ema_26 = calc_ema(26)

    # 3. MACD
    macd_line = round(ema_12 - ema_26, 2)
    signal_line = round(macd_line * 0.8, 2)
    macd_hist = round(macd_line - signal_line, 2)

    # 4. Bollinger Bands
    mean_20 = sma_20
    var = sum((x - mean_20)**2 for x in closes[-20:]) / min(20, length)
    std = math.sqrt(var)
    bb_upper = round(mean_20 + (std * 2), 2)
    bb_lower = round(mean_20 - (std * 2), 2)

    # 5. VWAP (Volume-Weighted Average Price)
    cum_vol = sum(vols[-20:])
    cum_pv = sum((highs[i] + lows[i] + closes[i]) / 3.0 * vols[i] for i in range(length - 20, length))
    vwap = round(cum_pv / cum_vol, 2) if cum_vol > 0 else curr_price

    # 6. Stochastic Oscillator (14, 3)
    highest_14 = max(highs[-14:])
    lowest_14 = min(lows[-14:])
    range_hl = (highest_14 - lowest_14) if (highest_14 - lowest_14) > 0 else 1.0
    stoch_k = round(((curr_price - lowest_14) / range_hl) * 100.0, 2)
    stoch_d = round(stoch_k * 0.85, 2)

    # 7. ATR (Average True Range 14)
    tr_sum = sum(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(length - 14, length))
    atr = round(tr_sum / 14.0, 2)

    # 8. Fibonacci Retracements (from 90-day High & Low)
    max_90 = max(highs)
    min_90 = min(lows)
    diff_90 = max_90 - min_90
    fib_236 = round(max_90 - (diff_90 * 0.236), 2)
    fib_382 = round(max_90 - (diff_90 * 0.382), 2)
    fib_500 = round(max_90 - (diff_90 * 0.500), 2)
    fib_618 = round(max_90 - (diff_90 * 0.618), 2)

    score = 50.0
    signals = []

    if rsi <= 35:
        score += 25
        signals.append(f"RSI is oversold at {rsi} (Buy signal)")
    elif rsi >= 68:
        score -= 25
        signals.append(f"RSI is overbought at {rsi} (Sell signal)")
    else:
        signals.append(f"RSI is neutral at {rsi}")

    if curr_price > vwap:
        score += 15
        signals.append(f"Price is trading above VWAP (${vwap}) - Buyers in control")
    else:
        score -= 15
        signals.append(f"Price is trading below VWAP (${vwap}) - Sellers in control")

    if curr_price > sma_20 and curr_price > sma_50:
        score += 15
        signals.append("Trading above 20-day and 50-day SMAs (Bullish trend)")
    elif curr_price < sma_20 and curr_price < sma_50:
        score -= 15
        signals.append("Trading below 20-day and 50-day SMAs (Bearish trend)")

    if stoch_k < 20:
        score += 10
        signals.append(f"Stochastic Oscillator is oversold (%K: {stoch_k})")
    elif stoch_k > 80:
        score -= 10
        signals.append(f"Stochastic Oscillator is overbought (%K: {stoch_k})")

    score = max(0.0, min(100.0, round(score, 1)))
    trend = "BULLISH" if score >= 65 else ("BEARISH" if score <= 35 else "NEUTRAL")

    return {
        "rsi": rsi,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "ema_9": ema_9,
        "ema_21": ema_21,
        "macd": {"macd": macd_line, "signal": signal_line, "histogram": macd_hist},
        "bollinger": {"upper": bb_upper, "middle": mean_20, "lower": bb_lower},
        "vwap": vwap,
        "stochastic": {"k": stoch_k, "d": stoch_d},
        "atr": atr,
        "fibonacci": {"level_236": fib_236, "level_382": fib_382, "level_500": fib_500, "level_618": fib_618},
        "trend": trend,
        "score": score,
        "signals": signals
    }

AGENT_ANALYSIS_CACHE = {}

def call_gemini_flash(prompt, system_instruction="You are a Financial Analyst AI Agent."):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None, None, None
    
    models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-pro-latest"]
    for m in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            st_time = time.time()
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            res = urllib.request.urlopen(req, timeout=4)
            lat = round((time.time() - st_time) * 1000, 1)
            data = json.loads(res.read().decode('utf-8'))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text), m, lat
        except Exception as e:
            print(f"Gemini API model {m} notice: {e}")
    return None, None, None

def call_ollama_qwen(prompt, system_instruction="You are a Financial Analyst AI Agent."):
    models = ["qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5-coder", "llama3"]
    url = "http://127.0.0.1:11434/api/generate"

    for m in models:
        payload = {
            "model": m,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "format": "json"
        }
        try:
            st_time = time.time()
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            res = urllib.request.urlopen(req, timeout=35)
            lat = round((time.time() - st_time) * 1000, 1)
            data = json.loads(res.read().decode('utf-8'))
            text = data.get("response", "")
            if text:
                return json.loads(text), f"ollama/{m}", lat
        except Exception as e:
            pass
    return None, None, None

# --- MULTI-AGENT SYNTHESIS WITH RISK MANAGER VETO POWER ---
def analyze_symbol_agents(symbol, weights=None, veto_enabled=True, force_fresh=False):
    sym = symbol.strip().upper()
    now_ts = time.time()
    
    cache_key = f"{sym}_{veto_enabled}"
    if not force_fresh and cache_key in AGENT_ANALYSIS_CACHE:
        cached_ts, cached_res = AGENT_ANALYSIS_CACHE[cache_key]
        if now_ts - cached_ts < 60:
            res_copy = dict(cached_res)
            res_copy["is_cached"] = True
            res_copy["cache_age_seconds"] = round(now_ts - cached_ts, 1)
            res_copy["execution_source"] = f"CACHE_HIT (Age: {round(now_ts - cached_ts, 1)}s)"
            return res_copy

    start_time = time.time()
    quote = get_quote(sym)
    candles = get_candles(sym, 90)
    ind = calculate_indicators(candles)
    price = quote["current_price"]
    score = ind["score"]

    prompt_text = f"""
    Analyze stock/ETF '{sym}' priced at ${price} (24h Change: {quote['percent_change']}%).
    Technical Data: RSI={ind['rsi']}, VWAP=${ind['vwap']}, SMA20=${ind['sma_20']}, SMA50=${ind['sma_50']}, Stochastic %K={ind['stochastic']['k']}.
    Output JSON object with exact keys:
    "technical_reasoning": string,
    "sentiment_reasoning": string,
    "risk_reasoning": string
    """
    
    ai_out, model_used, api_latency = call_gemini_flash(prompt_text, "You are a Senior Quantitative AI Trading Agent.")
    if not ai_out:
        ai_out, model_used, api_latency = call_ollama_qwen(prompt_text, "You are a Senior Quantitative AI Trading Agent.")
    
    latency_ms = round((time.time() - start_time) * 1000, 1) if api_latency is None else api_latency

    if score >= 65:
        action = "BUY"
        tech_st = "BULLISH"
        sent_st = "BULLISH"
        risk_st = "NEUTRAL"
        conf = min(95.0, score + 12.0)
    elif score <= 35:
        action = "SELL"
        tech_st = "BEARISH"
        sent_st = "BEARISH"
        risk_st = "BEARISH"
        conf = min(95.0, (100 - score) + 8.0)
    else:
        action = "HOLD"
        tech_st = "NEUTRAL"
        sent_st = "BULLISH" if quote["percent_change"] >= 0 else "NEUTRAL"
        risk_st = "NEUTRAL"
        conf = 65.0

    is_vetoed = False
    veto_reasoning = ""
    if action == "BUY" and veto_enabled:
        if ind["rsi"] > 65 or quote["percent_change"] < -2.5 or ind["stochastic"]["k"] > 85:
            action = "HOLD"
            risk_st = "BEARISH"
            is_vetoed = True
            veto_reasoning = f"RISK MANAGER VETO: High volatility/overbought stochastic (%K: {ind['stochastic']['k']}) detected. BUY signal overridden to HOLD for account safety."

    exec_summary = veto_reasoning if is_vetoed else f"Multi-Agent Team reaches {action} consensus on {sym} with {round(conf, 1)}% confidence based on technical indicator suite score ({score}/100) and risk synthesis."

    tech_reasoning = ai_out.get("technical_reasoning") if (ai_out and isinstance(ai_out, dict)) else f"Indicator score {score}/100 with RSI at {ind['rsi']} and VWAP at ${ind['vwap']}. Signals: {'; '.join(ind['signals'])}."
    sent_reasoning = ai_out.get("sentiment_reasoning") if (ai_out and isinstance(ai_out, dict)) else f"Headline volume is net positive with intraday price movement of {quote['percent_change']}%. Momentum remains supportive."
    risk_reasoning = ai_out.get("risk_reasoning") if (ai_out and isinstance(ai_out, dict)) else (veto_reasoning if is_vetoed else f"Entry price ${price}. Recommended 5% Trailing Stop at ${round(price * 0.95, 2)} (-5%), profit target at ${round(price * 1.10, 2)} (+10%). Position size capped at 5% cash.")

    if model_used and "ollama" in model_used:
        source_label = f"LOCAL_OLLAMA_AI ({model_used.split('/')[-1]})"
    elif ai_out:
        source_label = f"LIVE_GEMINI_API ({model_used or 'gemini-flash-latest'})"
    else:
        source_label = "DETERMINISTIC_INDICATOR_ENGINE"

    res = {
        "symbol": sym,
        "current_price": price,
        "consensus_action": action,
        "consensus_confidence": round(conf, 1),
        "is_vetoed": is_vetoed,
        "executive_summary": exec_summary,
        "execution_source": source_label,
        "model_used": model_used or "deterministic-engine",
        "latency_ms": latency_ms,
        "is_cached": False,
        "cache_age_seconds": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technical_agent": {
            "agent_name": "Technical Analyst",
            "stance": tech_st,
            "confidence": round(conf, 1),
            "reasoning": tech_reasoning
        },
        "sentiment_agent": {
            "agent_name": "Sentiment Analyst",
            "stance": sent_st,
            "confidence": 72.0,
            "reasoning": sent_reasoning
        },
        "risk_agent": {
            "agent_name": "Risk Manager",
            "stance": risk_st,
            "confidence": 85.0,
            "reasoning": risk_reasoning
        },
        "target_price": round(price * 1.10, 2),
        "stop_loss": round(price * 0.95, 2),
        "take_profit": round(price * 1.10, 2)
    }

    AGENT_ANALYSIS_CACHE[cache_key] = (now_ts, res)
    return res

# --- GOAL & IDEA MULTI-AGENT PORTFOLIO RECOMMENDATION ENGINE ---
GOAL_PORTFOLIO_CACHE = {}

def get_deterministic_goal_assets(goal_text, risk_tolerance):
    gt = goal_text.lower()
    if any(k in gt for k in ["ai", "chip", "semiconductor", "tech", "hardware", "cloud", "software"]):
        raw_list = [
            {"symbol": "NVDA", "asset_name": "NVIDIA Corporation", "asset_type": "Stock", "allocation_percent": 30.0},
            {"symbol": "QQQ", "asset_name": "Invesco QQQ Trust (Nasdaq 100)", "asset_type": "ETF", "allocation_percent": 25.0},
            {"symbol": "MSFT", "asset_name": "Microsoft Corporation", "asset_type": "Stock", "allocation_percent": 25.0},
            {"symbol": "AAPL", "asset_name": "Apple Inc.", "asset_type": "Stock", "allocation_percent": 20.0}
        ]
    elif any(k in gt for k in ["dividend", "income", "yield", "cash", "passive"]):
        raw_list = [
            {"symbol": "SCHD", "asset_name": "Schwab U.S. Dividend Equity ETF", "asset_type": "ETF", "allocation_percent": 35.0},
            {"symbol": "SPY", "asset_name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF", "allocation_percent": 25.0},
            {"symbol": "VOO", "asset_name": "Vanguard S&P 500 ETF", "asset_type": "ETF", "allocation_percent": 25.0},
            {"symbol": "IWM", "asset_name": "iShares Russell 2000 ETF", "asset_type": "ETF", "allocation_percent": 15.0}
        ]
    elif any(k in gt for k in ["clean", "green", "energy", "ev", "solar", "electric", "climate"]):
        raw_list = [
            {"symbol": "TSLA", "asset_name": "Tesla, Inc.", "asset_type": "Stock", "allocation_percent": 30.0},
            {"symbol": "ICLN", "asset_name": "iShares Global Clean Energy ETF", "asset_type": "ETF", "allocation_percent": 30.0},
            {"symbol": "RIVN", "asset_name": "Rivian Automotive", "asset_type": "Stock", "allocation_percent": 20.0},
            {"symbol": "QQQ", "asset_name": "Invesco QQQ Trust", "asset_type": "ETF", "allocation_percent": 20.0}
        ]
    else:
        raw_list = [
            {"symbol": "SPY", "asset_name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF", "allocation_percent": 30.0},
            {"symbol": "QQQ", "asset_name": "Invesco QQQ Trust", "asset_type": "ETF", "allocation_percent": 30.0},
            {"symbol": "NVDA", "asset_name": "NVIDIA Corporation", "asset_type": "Stock", "allocation_percent": 20.0},
            {"symbol": "SCHD", "asset_name": "Schwab U.S. Dividend Equity ETF", "asset_type": "ETF", "allocation_percent": 20.0}
        ]

    assets = []
    for item in raw_list:
        sym = item["symbol"]
        q = get_quote(sym)
        c = get_candles(sym, 30)
        ind = calculate_indicators(c)
        
        action = "BUY" if ind["score"] >= 55 else "ACCUMULATE"
        is_veto = (ind["rsi"] > 75) if risk_tolerance == "Conservative" else False
        
        assets.append({
            "symbol": sym,
            "asset_name": item["asset_name"],
            "asset_type": item["asset_type"],
            "allocation_percent": item["allocation_percent"],
            "current_price": q["current_price"],
            "percent_change": q["percent_change"],
            "consensus_action": action,
            "consensus_confidence": round(ind["score"] + 15.0, 1),
            "technical_reasoning": f"Indicator suite score {ind['score']}/100. RSI at {ind['rsi']}, VWAP at ${ind['vwap']}.",
            "sentiment_reasoning": f"Volume activity robust with intraday movement of {q['percent_change']}%. Momentum supports thesis.",
            "risk_reasoning": f"Volatility managed under {risk_tolerance} parameters. 5% trailing stop recommended.",
            "is_vetoed": is_veto
        })
    return assets

def recommend_goal_portfolio(goal_text, risk_tolerance="Moderate", horizon="Medium-Term", force_fresh=False):
    goal_clean = (goal_text or "Balanced Portfolio Growth").strip()
    cache_key = f"{goal_clean.lower()}_{risk_tolerance.lower()}_{horizon.lower()}"
    now_ts = time.time()

    if not force_fresh and cache_key in GOAL_PORTFOLIO_CACHE:
        cached_ts, cached_res = GOAL_PORTFOLIO_CACHE[cache_key]
        if now_ts - cached_ts < 60:
            res_copy = dict(cached_res)
            res_copy["is_cached"] = True
            res_copy["cache_age_seconds"] = round(now_ts - cached_ts, 1)
            res_copy["execution_source"] = f"CACHE_HIT (Age: {round(now_ts - cached_ts, 1)}s)"
            return res_copy

    start_time = time.time()

    prompt = f"""
    The user wants an investment portfolio based on this goal/thesis: '{goal_clean}'.
    User Profile: Risk Tolerance = '{risk_tolerance}', Investment Horizon = '{horizon}'.
    
    Act as a Multi-Agent Investment Committee (Technical Analyst, Sentiment Analyst, Risk Manager).
    Select 4 to 6 top relevant U.S. stocks and ETFs matching this goal.
    Assign allocation percentages that sum to EXACTLY 100%.
    
    Output JSON object with exact keys:
    "portfolio_name": string (e.g. "AI Hardware & Next-Gen Infrastructure Portfolio"),
    "overall_thesis": string (2-3 sentence strategic executive summary),
    "recommended_assets": array of objects with keys:
        "symbol": string,
        "asset_name": string,
        "asset_type": "Stock" or "ETF",
        "allocation_percent": number,
        "consensus_action": "BUY" or "ACCUMULATE" or "HOLD",
        "consensus_confidence": number,
        "technical_reasoning": string,
        "sentiment_reasoning": string,
        "risk_reasoning": string,
        "is_vetoed": boolean,
    "risk_summary": string
    """

    ai_out, model_used, api_latency = call_gemini_flash(prompt, "You are a Senior Multi-Agent Asset Allocator & Portfolio Architect.")
    if not ai_out:
        ai_out, model_used, api_latency = call_ollama_qwen(prompt, "You are a Senior Multi-Agent Asset Allocator & Portfolio Architect.")

    latency_ms = round((time.time() - start_time) * 1000, 1) if api_latency is None else api_latency

    if model_used and "ollama" in model_used:
        source_lbl = f"LOCAL_OLLAMA_AI ({model_used.split('/')[-1]})"
    elif ai_out:
        source_lbl = f"LIVE_GEMINI_API ({model_used or 'gemini-flash-latest'})"
    else:
        source_lbl = "DETERMINISTIC_INDICATOR_ENGINE"

    if ai_out and isinstance(ai_out, dict) and "recommended_assets" in ai_out and isinstance(ai_out["recommended_assets"], list):
        assets = ai_out["recommended_assets"]
        for a in assets:
            sym = a.get("symbol", "SPY").upper()
            a["symbol"] = sym
            q = get_quote(sym)
            a["current_price"] = q["current_price"]
            a["percent_change"] = q["percent_change"]

        res = {
            "goal_text": goal_clean,
            "risk_tolerance": risk_tolerance,
            "horizon": horizon,
            "portfolio_name": ai_out.get("portfolio_name", f"{goal_clean} Strategy Portfolio"),
            "overall_thesis": ai_out.get("overall_thesis", "Strategic portfolio customized for user goal and risk profile."),
            "recommended_assets": assets,
            "risk_summary": ai_out.get("risk_summary", f"Risk level tailored for {risk_tolerance} risk profile and {horizon} horizon."),
            "execution_source": source_lbl,
            "model_used": model_used or "gemini-flash-latest",
            "latency_ms": latency_ms,
            "is_cached": False,
            "cache_age_seconds": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        GOAL_PORTFOLIO_CACHE[cache_key] = (now_ts, res)
        return res

    fallback_assets = get_deterministic_goal_assets(goal_clean, risk_tolerance)
    res = {
        "goal_text": goal_clean,
        "risk_tolerance": risk_tolerance,
        "horizon": horizon,
        "portfolio_name": f"{goal_clean} Strategy Portfolio",
        "overall_thesis": f"Algorithmic portfolio allocation optimized for '{goal_clean}' under {risk_tolerance} parameters using quantitative technical indicators.",
        "recommended_assets": fallback_assets,
        "risk_summary": f"Diversified asset allocation matching {risk_tolerance} profile with stop loss risk protection.",
        "execution_source": "DETERMINISTIC_INDICATOR_ENGINE",
        "model_used": "quantitative-fallback-engine",
        "latency_ms": latency_ms,
        "is_cached": False,
        "cache_age_seconds": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    GOAL_PORTFOLIO_CACHE[cache_key] = (now_ts, res)
    return res

# --- TRAILING STOP LOSS & CIRCUIT BREAKER EVALUATOR ---
def check_trailing_stops_and_circuit_breakers(conn):
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM account LIMIT 1")
    acc = dict(cursor.fetchone())
    
    # 1. Portfolio Circuit Breaker Check (10% Max Drawdown)
    cum_pnl_pct = ((acc["cash_balance"] - acc["initial_capital"]) / acc["initial_capital"]) * 100
    if cum_pnl_pct <= -10.0 and not acc["circuit_breaker_active"]:
        cursor.execute("UPDATE account SET circuit_breaker_active = 1 WHERE id = ?", (acc["id"],))
        conn.commit()
        send_webhook_alert(
            "CIRCUIT BREAKER ACTIVATED",
            f"Portfolio max drawdown reached -10.0% (${acc['cash_balance']:.2f}). All automated trading has been HALTED.",
            alert_type="CIRCUIT_BREAKER"
        )

    # 2. Position 5% Trailing Stop Loss Check
    cursor.execute("SELECT * FROM positions WHERE shares > 0")
    positions = [dict(r) for r in cursor.fetchall()]

    for pos in positions:
        sym = pos["symbol"]
        q = get_quote(sym)
        curr_price = q["current_price"]
        peak_price = max(pos.get("peak_price") or pos["avg_cost"], curr_price)
        
        # Update peak price
        cursor.execute("UPDATE positions SET peak_price = ? WHERE id = ?", (peak_price, pos["id"]))
        
        # Check if price dropped 5% below peak
        stop_price = round(peak_price * 0.95, 2)
        if curr_price <= stop_price:
            # Trigger Trailing Stop Loss Order
            total_val = pos["shares"] * curr_price
            new_cash = acc["cash_balance"] + total_val
            realized = (curr_price - pos["avg_cost"]) * pos["shares"]
            new_real = pos["realized_pnl"] + realized
            
            cursor.execute("UPDATE account SET cash_balance = ? WHERE id = ?", (new_cash, acc["id"]))
            cursor.execute("UPDATE positions SET shares = 0, unrealized_pnl = 0, realized_pnl = ? WHERE id = ?", (new_real, pos["id"]))
            cursor.execute("""
                INSERT INTO orders (symbol, side, shares, price, total_value, order_type, status, triggered_by, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sym, "SELL", pos["shares"], curr_price, total_val, "MARKET", "FILLED", "TRAILING_STOP", f"5% Trailing Stop Loss triggered! Peak: ${peak_price:.2f}, Executed: ${curr_price:.2f}"))
            
            conn.commit()
            
            send_webhook_alert(
                f"TRAILING STOP TRIGGERED - {sym}",
                f"Closed position in {sym} ({pos['shares']} shares @ ${curr_price:.2f}). Peak price reached was ${peak_price:.2f}. Realized P&L: ${realized:.2f}.",
                alert_type="TRAILING_STOP"
            )

# --- 15-MINUTE BACKGROUND CRON SCHEDULER ---
def background_cron_loop():
    print("AgentTrader 15-Minute Market Hours Cron Scheduler Started")
    while True:
        try:
            now = datetime.now()
            # Run tick if U.S. stock market hours (9:30 AM - 4:00 PM EST, weekdays)
            # For paper trading simulation, run tick periodically
            conn = get_db()
            check_trailing_stops_and_circuit_breakers(conn)
            conn.close()
        except Exception as e:
            print("Background Cron loop notice:", e)
        time.sleep(900) # 15 minutes = 900 seconds

# Start background cron thread
cron_thread = threading.Thread(target=background_cron_loop, daemon=True)
cron_thread.start()

# --- HTTP REQUEST HANDLER ---
class RequestHandler(http.server.BaseHTTPRequestHandler):
    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def _json(self, data, status=200):
        self.send_response(status)
        self._send_cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _serve_file(self, filepath, content_type="text/html"):
        if os.path.exists(filepath):
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(filepath, "rb") as f:
                self.wfile.write(f.read())
        else:
            self._json({"error": "File not found"}, 404)

    def _body(self):
        len_str = self.headers.get("Content-Length", 0)
        if not len_str: return {}
        raw = self.rfile.read(int(len_str)).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if not path.startswith("/api/"):
            return self._serve_file(os.path.join(PUBLIC_DIR, "index.html"))

        conn = get_db()
        cursor = conn.cursor()

        try:
            if path == "/api/health":
                self._json({"status": "ok", "app": "AgentTrader Python API v2.0", "version": "2.0.0"})

            elif path == "/api/portfolio":
                check_trailing_stops_and_circuit_breakers(conn)
                cursor.execute("SELECT * FROM account LIMIT 1")
                acc = dict(cursor.fetchone())
                
                cursor.execute("SELECT * FROM positions WHERE shares > 0")
                pos_rows = [dict(r) for r in cursor.fetchall()]

                pos_val, unpnl, repnl = 0.0, 0.0, 0.0
                updated_positions = []

                for p in pos_rows:
                    q = get_quote(p["symbol"])
                    cp = q["current_price"]
                    mval = p["shares"] * cp
                    unr = (cp - p["avg_cost"]) * p["shares"]
                    peak = max(p.get("peak_price") or p["avg_cost"], cp)
                    
                    pos_val += mval
                    unpnl += unr
                    repnl += p["realized_pnl"]

                    updated_positions.append({
                        "id": p["id"],
                        "symbol": p["symbol"],
                        "name": p["name"],
                        "asset_type": p["asset_type"],
                        "shares": round(p["shares"], 4),
                        "avg_cost": round(p["avg_cost"], 2),
                        "current_price": cp,
                        "peak_price": round(peak, 2),
                        "trailing_stop_price": round(peak * 0.95, 2),
                        "market_value": round(mval, 2),
                        "unrealized_pnl": round(unr, 2),
                        "realized_pnl": round(p["realized_pnl"], 2),
                        "pnl_percent": round(((cp - p["avg_cost"]) / p["avg_cost"] * 100), 2) if p["avg_cost"] > 0 else 0.0
                    })

                tot_equity = acc["cash_balance"] + pos_val
                cum_pnl = tot_equity - acc["initial_capital"]

                self._json({
                    "cash_balance": round(acc["cash_balance"], 2),
                    "initial_capital": round(acc["initial_capital"], 2),
                    "positions_value": round(pos_val, 2),
                    "total_equity": round(tot_equity, 2),
                    "unrealized_pnl": round(unpnl, 2),
                    "realized_pnl": round(repnl, 2),
                    "cumulative_pnl": round(cum_pnl, 2),
                    "cumulative_pnl_percent": round((cum_pnl / acc["initial_capital"] * 100), 2),
                    "circuit_breaker_active": bool(acc.get("circuit_breaker_active", 0)),
                    "positions": updated_positions
                })

            elif path == "/api/webhooks":
                cursor.execute("SELECT * FROM webhook_settings LIMIT 1")
                w = cursor.fetchone()
                self._json(dict(w) if w else {})

            elif path == "/api/agents/config":
                cursor.execute("SELECT * FROM agent_config LIMIT 1")
                cfg = cursor.fetchone()
                self._json(dict(cfg) if cfg else {})

            elif path == "/api/portfolio/snapshots":
                cursor.execute("SELECT * FROM portfolio_snapshots ORDER BY timestamp ASC LIMIT 100")
                rows = [dict(r) for r in cursor.fetchall()]
                if not rows:
                    rows = [{
                        "timestamp": "Initial",
                        "total_equity": 100000.0,
                        "cash_balance": 100000.0,
                        "positions_value": 0.0,
                        "cumulative_pnl": 0.0
                    }]
                self._json(rows)

            elif path == "/api/watchlist":
                cursor.execute("SELECT * FROM watchlist")
                items = [dict(r) for r in cursor.fetchall()]
                res = []
                for item in items:
                    q = get_quote(item["symbol"])
                    res.append({**item, "quote": q})
                self._json(res)

            elif path.startswith("/api/market/search"):
                qstr = query.get("q", [""])[0]
                q_upper = qstr.strip().upper()
                res = []
                for sym, info in POPULAR.items():
                    if not q_upper or q_upper in sym or q_upper in info["name"].upper():
                        res.append({"symbol": sym, "name": info["name"], "asset_type": info["asset_type"]})
                if not res and q_upper:
                    res.append({"symbol": q_upper, "name": f"{q_upper} Corp", "asset_type": "Stock"})
                self._json(res)

            elif path.startswith("/api/market/quote/"):
                sym = path.split("/")[-1]
                self._json(get_quote(sym))

            elif path.startswith("/api/market/profile/"):
                sym = path.split("/")[-1]
                self._json(get_stock_profile(sym))

            elif path.startswith("/api/market/candles/"):
                sym = path.split("/")[-1]
                self._json(get_candles(sym, 90))

            elif path.startswith("/api/market/indicators/"):
                sym = path.split("/")[-1]
                candles = get_candles(sym, 90)
                self._json(calculate_indicators(candles))

            elif path == "/api/strategies":
                cursor.execute("SELECT * FROM strategies")
                self._json([dict(r) for r in cursor.fetchall()])

            elif path == "/api/orders":
                cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100")
                self._json([dict(r) for r in cursor.fetchall()])

            elif path == "/api/agents/logs":
                cursor.execute("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT 50")
                self._json([dict(r) for r in cursor.fetchall()])

            else:
                self._json({"error": "Endpoint not found"}, 404)

        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        body = self._body()

        conn = get_db()
        cursor = conn.cursor()

        try:
            if path == "/api/portfolio/reset":
                cursor.execute("DELETE FROM orders")
                cursor.execute("DELETE FROM positions")
                cursor.execute("DELETE FROM portfolio_snapshots")
                cursor.execute("UPDATE account SET cash_balance = 100000.0, initial_capital = 100000.0, circuit_breaker_active = 0")
                conn.commit()
                self._json({"message": "Portfolio reset to $100,000 cash balance"})

            elif path == "/api/webhooks":
                cursor.execute("""
                    UPDATE webhook_settings SET
                    whatsapp_number = ?,
                    discord_webhook_url = ?,
                    telegram_bot_token = ?,
                    telegram_chat_id = ?
                    WHERE id = 1
                """, (
                    body.get("whatsapp_number", ""),
                    body.get("discord_webhook_url", ""),
                    body.get("telegram_bot_token", ""),
                    body.get("telegram_chat_id", "")
                ))
                conn.commit()
                self._json({"message": "Webhook settings updated successfully"})

            elif path == "/api/agents/config":
                cursor.execute("""
                    UPDATE agent_config SET
                    weight_technical = ?,
                    weight_sentiment = ?,
                    weight_risk = ?,
                    risk_veto_enabled = ?,
                    min_confidence = ?,
                    prompt_technical = ?,
                    prompt_sentiment = ?,
                    prompt_risk = ?
                    WHERE id = 1
                """, (
                    float(body.get("weight_technical", 0.35)),
                    float(body.get("weight_sentiment", 0.25)),
                    float(body.get("weight_risk", 0.40)),
                    1 if body.get("risk_veto_enabled", True) else 0,
                    float(body.get("min_confidence", 70.0)),
                    body.get("prompt_technical", ""),
                    body.get("prompt_sentiment", ""),
                    body.get("prompt_risk", "")
                ))
                conn.commit()
                self._json({"message": "Agent Configuration updated successfully"})

            elif path == "/api/watchlist":
                sym = body.get("symbol", "").strip().upper()
                if not sym:
                    return self._json({"error": "Symbol required"}, 400)
                q = get_quote(sym)
                name = body.get("name") or q["name"]
                atype = body.get("asset_type") or q["asset_type"]
                cursor.execute("INSERT OR IGNORE INTO watchlist (symbol, name, asset_type) VALUES (?, ?, ?)", (sym, name, atype))
                conn.commit()
                cursor.execute("SELECT * FROM watchlist WHERE symbol = ?", (sym,))
                self._json(dict(cursor.fetchone()))

            elif path == "/api/strategies":
                cursor.execute("""
                    INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, weight_technical, weight_sentiment, weight_risk, risk_veto_enabled, allocation_amount, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    body.get("name", "Custom Strategy"),
                    body.get("symbol", "SPY").upper(),
                    body.get("rsi_buy_threshold", 35.0),
                    body.get("rsi_sell_threshold", 70.0),
                    body.get("ma_fast", 20),
                    body.get("ma_slow", 50),
                    1 if body.get("use_ma_cross", True) else 0,
                    1 if body.get("use_agent_consensus", True) else 0,
                    body.get("agent_min_confidence", 70.0),
                    body.get("weight_technical", 0.35),
                    body.get("weight_sentiment", 0.25),
                    body.get("weight_risk", 0.40),
                    1 if body.get("risk_veto_enabled", True) else 0,
                    body.get("allocation_amount", 5000.0),
                    1 if body.get("active", True) else 0
                ))
                conn.commit()
                self._json({"message": "Strategy created", "id": cursor.lastrowid})

            elif path == "/api/orders":
                sym = body.get("symbol", "").strip().upper()
                side = body.get("side", "").strip().upper()
                shares = float(body.get("shares", 0))
                
                if side not in ["BUY", "SELL"] or shares <= 0:
                    return self._json({"error": "Invalid order parameters"}, 400)

                q = get_quote(sym)
                exec_price = float(body.get("price") or q["current_price"])
                total_val = shares * exec_price

                cursor.execute("SELECT * FROM account LIMIT 1")
                acc = dict(cursor.fetchone())

                if acc.get("circuit_breaker_active"):
                    return self._json({"error": "Circuit Breaker Active (-10% Max Drawdown hit). Reset portfolio to resume trading."}, 400)

                cursor.execute("SELECT * FROM positions WHERE symbol = ?", (sym,))
                pos_row = cursor.fetchone()
                pos = dict(pos_row) if pos_row else None

                if side == "BUY":
                    if acc["cash_balance"] < total_val:
                        return self._json({"error": f"Insufficient cash (${acc['cash_balance']:.2f} available)"}, 400)
                    new_cash = acc["cash_balance"] - total_val
                    cursor.execute("UPDATE account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_cash, acc["id"]))

                    if pos:
                        tot_sh = pos["shares"] + shares
                        new_avg = ((pos["shares"] * pos["avg_cost"]) + total_val) / tot_sh
                        new_peak = max(pos.get("peak_price") or new_avg, exec_price)
                        cursor.execute("UPDATE positions SET shares = ?, avg_cost = ?, current_price = ?, peak_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (tot_sh, new_avg, exec_price, new_peak, (exec_price - new_avg) * tot_sh, pos["id"]))
                    else:
                        cursor.execute("INSERT INTO positions (symbol, name, asset_type, shares, avg_cost, current_price, peak_price) VALUES (?, ?, ?, ?, ?, ?, ?)", (sym, q["name"], q["asset_type"], shares, exec_price, exec_price, exec_price))
                
                elif side == "SELL":
                    if not pos or pos["shares"] < shares:
                        return self._json({"error": f"Insufficient shares of {sym}"}, 400)
                    new_cash = acc["cash_balance"] + total_val
                    cursor.execute("UPDATE account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_cash, acc["id"]))

                    realized = (exec_price - pos["avg_cost"]) * shares
                    rem_sh = pos["shares"] - shares
                    new_real = pos["realized_pnl"] + realized

                    if rem_sh <= 0.0001:
                        cursor.execute("UPDATE positions SET shares = 0, unrealized_pnl = 0, realized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_real, pos["id"]))
                    else:
                        cursor.execute("UPDATE positions SET shares = ?, realized_pnl = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (rem_sh, new_real, (exec_price - pos["avg_cost"]) * rem_sh, pos["id"]))

                cursor.execute("""
                    INSERT INTO orders (symbol, side, shares, price, total_value, order_type, status, triggered_by, reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sym, side, shares, exec_price, total_val, body.get("order_type", "MARKET"), "FILLED", body.get("triggered_by", "MANUAL"), body.get("reasoning", "Manual trade")))

                conn.commit()

                send_webhook_alert(
                    f"ORDER EXECUTED - {side} {shares} {sym}",
                    f"Order Type: {body.get('order_type', 'MARKET')} | Price: ${exec_price:.2f} | Total: ${total_val:.2f} | Trigger: {body.get('triggered_by', 'MANUAL')}",
                    alert_type=side
                )

                cursor.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,))
                self._json(dict(cursor.fetchone()))

            elif path.startswith("/api/agents/analyze/"):
                sym = path.split("/")[-1].strip().upper()
                force = query.get("force", ["false"])[0].lower() in ["1", "true"]
                analysis = analyze_symbol_agents(sym, veto_enabled=True, force_fresh=force)
                for k in ["technical_agent", "sentiment_agent", "risk_agent"]:
                    adata = analysis.get(k)
                    if adata:
                        cursor.execute("""
                            INSERT INTO agent_logs (symbol, agent_name, stance, confidence, reasoning, target_price, stop_loss, take_profit)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (sym, adata["agent_name"], adata["stance"], adata["confidence"], adata["reasoning"], analysis["target_price"], analysis["stop_loss"], analysis["take_profit"]))
                conn.commit()
                self._json(analysis)

            elif path == "/api/agents/recommend_goal":
                body = self._body()
                gt = body.get("goal_text", "Balanced Portfolio Growth")
                rt = body.get("risk_tolerance", "Moderate")
                hz = body.get("horizon", "Medium-Term")
                force = query.get("force", ["false"])[0].lower() in ["1", "true"] or body.get("force_fresh", False)
                res = recommend_goal_portfolio(gt, rt, hz, force_fresh=force)
                self._json(res)

            elif path == "/api/simulation/tick":
                check_trailing_stops_and_circuit_breakers(conn)
                cursor.execute("SELECT * FROM strategies WHERE active = 1")
                strgs = [dict(r) for r in cursor.fetchall()]
                evals = []

                for s in strgs:
                    sym = s["symbol"]
                    q = get_quote(sym)
                    candles = get_candles(sym, 30)
                    ind = calculate_indicators(candles)
                    agents = analyze_symbol_agents(sym, veto_enabled=bool(s.get("risk_veto_enabled", 1)))

                    trade_msg = "No trade condition triggered"
                    if ind["rsi"] <= s["rsi_buy_threshold"] and agents["consensus_action"] == "BUY" and not agents.get("is_vetoed"):
                        sh = round(s["allocation_amount"] / q["current_price"], 4)
                        if sh > 0:
                            trade_msg = f"BUY {sh} shares of {sym} at ${q['current_price']}"
                    elif agents.get("is_vetoed"):
                        trade_msg = f"RISK VETO: BUY signal blocked by Risk Manager"
                    elif ind["rsi"] >= s["rsi_sell_threshold"]:
                        trade_msg = f"SELL signal for {sym} at ${q['current_price']}"

                    evals.append({
                        "strategy_id": s["id"],
                        "strategy_name": s["name"],
                        "symbol": sym,
                        "rsi": ind["rsi"],
                        "agent_action": agents["consensus_action"],
                        "agent_confidence": agents["consensus_confidence"],
                        "is_vetoed": agents.get("is_vetoed", False),
                        "trade_executed": trade_msg
                    })

                self._json({"status": "success", "evaluations": evals})

            else:
                self._json({"error": "Endpoint not found"}, 404)

        except Exception as ex:
            import traceback
            traceback.print_exc()
            self._json({"error": str(ex)}, 500)
        finally:
            conn.close()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        conn = get_db()
        cursor = conn.cursor()
        try:
            if path.startswith("/api/strategies/") and path.endswith("/toggle"):
                sid = path.split("/")[3]
                cursor.execute("SELECT active FROM strategies WHERE id = ?", (sid,))
                row = cursor.fetchone()
                if row:
                    new_act = 0 if row[0] else 1
                    cursor.execute("UPDATE strategies SET active = ? WHERE id = ?", (new_act, sid))
                    conn.commit()
                    self._json({"id": int(sid), "active": bool(new_act)})
                else:
                    self._json({"error": "Not found"}, 404)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        conn = get_db()
        cursor = conn.cursor()
        try:
            if path.startswith("/api/watchlist/"):
                sym = path.split("/")[-1].upper()
                cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (sym,))
                conn.commit()
                self._json({"message": f"Removed {sym}"})
            elif path.startswith("/api/strategies/"):
                sid = path.split("/")[-1]
                cursor.execute("DELETE FROM strategies WHERE id = ?", (sid,))
                conn.commit()
                self._json({"message": "Strategy deleted"})
        finally:
            conn.close()

OLLAMA_SUBPROCESS = None

def start_ollama_process():
    global OLLAMA_SUBPROCESS
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                print("Local Ollama AI service is active on http://127.0.0.1:11434")
                return True
    except Exception:
        pass

    ollama_path = shutil.which("ollama") or "/usr/local/bin/ollama"
    if os.path.exists(ollama_path) or shutil.which("ollama"):
        try:
            print("Auto-starting local Ollama service for Qwen 2.5 Coder fallback...")
            OLLAMA_SUBPROCESS = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            for _ in range(6):
                time.sleep(0.5)
                try:
                    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                    with urllib.request.urlopen(req, timeout=1.0) as res:
                        if res.status == 200:
                            print(f"Started Ollama background server (PID: {OLLAMA_SUBPROCESS.pid}) for Qwen 2.5 Coder")
                            return True
                except Exception:
                    pass
        except Exception as e:
            print(f"Could not auto-start Ollama: {e}")
    return False

def stop_ollama_process():
    global OLLAMA_SUBPROCESS
    if OLLAMA_SUBPROCESS and OLLAMA_SUBPROCESS.poll() is None:
        print(f"\nShutting down local Ollama background process (PID: {OLLAMA_SUBPROCESS.pid})...")
        try:
            OLLAMA_SUBPROCESS.terminate()
            OLLAMA_SUBPROCESS.wait(timeout=3)
        except Exception:
            OLLAMA_SUBPROCESS.kill()
        print("Ollama process stopped cleanly.")
        OLLAMA_SUBPROCESS = None

atexit.register(stop_ollama_process)

def run():
    init_db()
    start_ollama_process()
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"AgentTrader v2.0 running on http://localhost:{PORT}")

    def handle_signal(sig, frame):
        print("\nShutdown signal received. Cleaning up...")
        stop_ollama_process()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_ollama_process()

if __name__ == "__main__":
    run()
