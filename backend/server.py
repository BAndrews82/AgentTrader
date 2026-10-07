import http.server
import socketserver
import json
import sqlite3
import urllib.parse
import os
import math
import random
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
            rsi_buy_threshold REAL DEFAULT 30.0,
            rsi_sell_threshold REAL DEFAULT 70.0,
            ma_fast INTEGER DEFAULT 20,
            ma_slow INTEGER DEFAULT 50,
            use_ma_cross BOOLEAN DEFAULT 1,
            use_agent_consensus BOOLEAN DEFAULT 1,
            agent_min_confidence REAL DEFAULT 70.0,
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
    
    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account (cash_balance, initial_capital) VALUES (100000.0, 100000.0)")

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

    cursor.execute("SELECT COUNT(*) FROM strategies")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('S&P 500 Dip & AI Consensus Strategy', 'SPY', 35.0, 70.0, 20, 50, 1, 1, 70.0, 5000.0, 1))

        cursor.execute("""
            INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Tech Growth Momentum Strategy', 'NVDA', 40.0, 75.0, 9, 21, 1, 1, 75.0, 7500.0, 1))

    conn.commit()
    conn.close()

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

def get_quote(symbol):
    sym = symbol.strip().upper()
    info = POPULAR.get(sym, {"name": f"{sym} Corp", "asset_type": "Stock", "base": 150.0})
    base = info["base"]
    
    change_pct = (random.random() - 0.47) * 0.025
    curr = round(base * (1 + change_pct), 2)
    prev = round(base, 2)
    chg = round(curr - prev, 2)
    pct = round((chg / prev * 100) if prev else 0.0, 2)
    
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
        "volume": random.randint(1000000, 9000000),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

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
        ret = (random.random() - 0.485) * 0.035
        open_p = curr
        close_p = open_p * (1 + ret)
        high_p = max(open_p, close_p) * (1 + random.random() * 0.015)
        low_p = min(open_p, close_p) * (1 - random.random() * 0.015)
        vol = random.randint(1500000, 9000000)
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
        return {"rsi": 50.0, "sma_20": 0.0, "sma_50": 0.0, "ema_9": 0.0, "ema_21": 0.0, "score": 50.0, "trend": "NEUTRAL", "signals": ["Insufficient candle data"]}
        
    closes = [c["close"] for c in candles]
    length = len(closes)
    curr_price = closes[-1]
    
    gains, losses = 0.0, 0.0
    for i in range(length - 14, length):
        diff = closes[i] - closes[i-1]
        if diff >= 0: gains += diff
        else: losses += abs(diff)
    avg_gain = gains / 14
    avg_loss = losses / 14
    rs = (avg_gain / avg_loss) if avg_loss > 0 else 100.0
    rsi = round(100.0 - (100.0 / (1.0 + rs)), 2)

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

    macd_line = round(ema_12 - ema_26, 2)
    signal_line = round(macd_line * 0.8, 2)
    macd_hist = round(macd_line - signal_line, 2)

    mean_20 = sma_20
    var = sum((x - mean_20)**2 for x in closes[-20:]) / min(20, length)
    std = math.sqrt(var)
    bb_upper = round(mean_20 + (std * 2), 2)
    bb_lower = round(mean_20 - (std * 2), 2)

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

    if curr_price > sma_20 and curr_price > sma_50:
        score += 20
        signals.append("Trading above 20-day and 50-day SMAs (Bullish trend)")
    elif curr_price < sma_20 and curr_price < sma_50:
        score -= 20
        signals.append("Trading below 20-day and 50-day SMAs (Bearish trend)")

    if ema_9 > ema_21:
        score += 15
        signals.append("9 EMA crossed above 21 EMA (Short-term momentum is positive)")
    else:
        score -= 15
        signals.append("9 EMA is below 21 EMA (Short-term momentum is negative)")

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
        "trend": trend,
        "score": score,
        "signals": signals
    }

def analyze_symbol_agents(symbol):
    sym = symbol.strip().upper()
    quote = get_quote(sym)
    candles = get_candles(sym, 90)
    ind = calculate_indicators(candles)
    price = quote["current_price"]
    score = ind["score"]

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

    return {
        "symbol": sym,
        "current_price": price,
        "consensus_action": action,
        "consensus_confidence": round(conf, 1),
        "executive_summary": f"Multi-Agent Team reaches {action} consensus on {sym} with {round(conf, 1)}% confidence based on technical score ({score}/100) and indicator alignment.",
        "technical_agent": {
            "agent_name": "Technical Analyst",
            "stance": tech_st,
            "confidence": round(conf, 1),
            "reasoning": f"Chart indicators yield technical score {score}/100 with RSI at {ind['rsi']}. Key triggers: {'; '.join(ind['signals'])}."
        },
        "sentiment_agent": {
            "agent_name": "Sentiment Analyst",
            "stance": sent_st,
            "confidence": 72.0,
            "reasoning": f"Market news & headline momentum is net positive with intraday price move of {quote['percent_change']}%. Catalyst drivers remain supportive."
        },
        "risk_agent": {
            "agent_name": "Risk Manager",
            "stance": risk_st,
            "confidence": 82.0,
            "reasoning": f"Entry price ${price}. Stop-loss recommended at ${round(price * 0.95, 2)} (-5%), profit target at ${round(price * 1.10, 2)} (+10%). Position size capped at 5% of account balance."
        },
        "target_price": round(price * 1.10, 2),
        "stop_loss": round(price * 0.95, 2),
        "take_profit": round(price * 1.10, 2)
    }

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
            # Serve static frontend web UI
            return self._serve_file(os.path.join(PUBLIC_DIR, "index.html"))

        conn = get_db()
        cursor = conn.cursor()

        try:
            if path == "/api/health":
                self._json({"status": "ok", "app": "AgentTrader Python API", "version": "1.0.0"})

            elif path == "/api/portfolio":
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
                    "positions": updated_positions
                })

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

            elif path.startswith("/api/market/candles/"):
                sym = path.split("/")[-1]
                self._json(get_candles(sym, 90))

            elif path.startswith("/api/market/news/"):
                sym = path.split("/")[-1]
                self._json([
                    {"title": f"{sym} reports quarterly results exceeding consensus expectations.", "publisher": "Bloomberg", "time": "1h ago"},
                    {"title": f"Quantitative strategy upgrade for {sym} as volume momentum rises.", "publisher": "Reuters", "time": "3h ago"}
                ])

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
        body = self._body()

        conn = get_db()
        cursor = conn.cursor()

        try:
            if path == "/api/portfolio/reset":
                cursor.execute("DELETE FROM orders")
                cursor.execute("DELETE FROM positions")
                cursor.execute("DELETE FROM portfolio_snapshots")
                cursor.execute("UPDATE account SET cash_balance = 100000.0, initial_capital = 100000.0")
                conn.commit()
                self._json({"message": "Portfolio reset to $100,000 cash balance"})

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
                    INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    body.get("name", "Custom Strategy"),
                    body.get("symbol", "SPY").upper(),
                    body.get("rsi_buy_threshold", 30.0),
                    body.get("rsi_sell_threshold", 70.0),
                    body.get("ma_fast", 20),
                    body.get("ma_slow", 50),
                    1 if body.get("use_ma_cross", True) else 0,
                    1 if body.get("use_agent_consensus", True) else 0,
                    body.get("agent_min_confidence", 70.0),
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
                        cursor.execute("UPDATE positions SET shares = ?, avg_cost = ?, current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (tot_sh, new_avg, exec_price, (exec_price - new_avg) * tot_sh, pos["id"]))
                    else:
                        cursor.execute("INSERT INTO positions (symbol, name, asset_type, shares, avg_cost, current_price) VALUES (?, ?, ?, ?, ?, ?)", (sym, q["name"], q["asset_type"], shares, exec_price, exec_price))
                
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
                cursor.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,))
                self._json(dict(cursor.fetchone()))

            elif path.startswith("/api/agents/analyze/"):
                sym = path.split("/")[-1].strip().upper()
                analysis = analyze_symbol_agents(sym)
                for k in ["technical_agent", "sentiment_agent", "risk_agent"]:
                    adata = analysis.get(k)
                    if adata:
                        cursor.execute("""
                            INSERT INTO agent_logs (symbol, agent_name, stance, confidence, reasoning, target_price, stop_loss, take_profit)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (sym, adata["agent_name"], adata["stance"], adata["confidence"], adata["reasoning"], analysis["target_price"], analysis["stop_loss"], analysis["take_profit"]))
                conn.commit()
                self._json(analysis)

            elif path == "/api/simulation/tick":
                cursor.execute("SELECT * FROM strategies WHERE active = 1")
                strgs = [dict(r) for r in cursor.fetchall()]
                evals = []

                for s in strgs:
                    sym = s["symbol"]
                    q = get_quote(sym)
                    candles = get_candles(sym, 30)
                    ind = calculate_indicators(candles)
                    agents = analyze_symbol_agents(sym)

                    trade_msg = "No trade condition triggered"
                    if ind["rsi"] <= s["rsi_buy_threshold"] and agents["consensus_action"] == "BUY":
                        sh = round(s["allocation_amount"] / q["current_price"], 4)
                        if sh > 0:
                            trade_msg = f"BUY {sh} shares of {sym} at ${q['current_price']}"
                    elif ind["rsi"] >= s["rsi_sell_threshold"]:
                        trade_msg = f"SELL signal for {sym} at ${q['current_price']}"

                    evals.append({
                        "strategy_id": s["id"],
                        "strategy_name": s["name"],
                        "symbol": sym,
                        "rsi": ind["rsi"],
                        "agent_action": agents["consensus_action"],
                        "agent_confidence": agents["consensus_confidence"],
                        "trade_executed": trade_msg
                    })

                self._json({"status": "success", "evaluations": evals})

            else:
                self._json({"error": "Endpoint not found"}, 404)

        except Exception as ex:
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

def run():
    init_db()
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("", PORT), RequestHandler)
    print(f"AgentTrader App running on http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
