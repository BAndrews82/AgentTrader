# AgentTrader AI - Comprehensive User & Technical Guide

Welcome to **AgentTrader**, a full-stack, state-of-the-art paper trading and quantitative investment platform powered by a **Hybrid Multi-Agent AI System** (Google Gemini 3.8 Flash) and an **Algorithmic Rule Engine**.

---

## 🚀 Quick Start Guide

### 1. Launching the App Server
Open your terminal and run:
```bash
python3 /home/brad/Documents/antigravity/Trader/backend/server.py
```
> **Background Execution**: To keep the server running continuously in the background:
> ```bash
> nohup python3 /home/brad/Documents/antigravity/Trader/backend/server.py > /dev/null 2>&1 &
> ```

### 2. Opening the Web Interface
- **Local Machine**: Open your browser at `http://localhost:8000`
- **Network / LAN Devices**: Open `http://<YOUR-SERVER-IP>` (e.g. `http://192.168.1.50` if Nginx reverse proxy is configured).

---

## 📊 Core Application Features & Tab Guide

### 1. Portfolio Dashboard
The central command hub for your paper investment account.
- **Account Summary Metrics**: Real-time view of **Net Worth (Total Equity)**, **Available Cash**, **Holdings Value**, **Unrealized P&L**, and **Realized P&L**.
- **Portfolio Performance Curve**: An interactive equity curve tracking historical portfolio net worth.
- **Holdings Allocation Breakdown**: Asset allocation percentage bars per stock/ETF.
- **Active Positions Table**: Detailed view of open positions with live quotes, cost-basis, quantity, current price, gain/loss badges, and a 1-click **Close Position** button.

---

### 2. Watchlist & Interactive Charts
Explore market assets, review technical indicators, and view price action.
- **Ticker & ETF Search**: Look up any Stock or ETF symbol (e.g. `AAPL`, `NVDA`, `SPY`, `QQQ`, `VOO`, `TSLA`, `SCHD`) and add them to your active watchlist.
- **Interactive Candlestick Chart**: Visualizes candlestick price bars (Open, High, Low, Close) and Volume histograms.
- **Technical Indicators & Overlays**:
  - **RSI (14)**: Relative Strength Index with Overbought (70) and Oversold (30) threshold lines.
  - **Moving Averages**: 20-day SMA, 50-day SMA, 9 EMA, 21 EMA.
  - **MACD**: MACD Line, Signal Line, and Histogram.
  - **Bollinger Bands**: Upper, Middle, and Lower volatility bands.
- **Quick Trade Modal**: Launch manual Market BUY or SELL orders with automatic cash and share validation.

---

### 3. AI Agent Command Center
The multi-agent AI debate panel powered by **Google Gemini 3.8 Flash**.
- **4 Specialized AI Agents**:
  1. 📈 **Technical Analyst Agent**: Evaluates chart setups, momentum metrics, indicator signals, and trend direction.
  2. 📰 **Sentiment Analyst Agent**: Scans news headline momentum, market mood, and sector catalysts.
  3. 🛡️ **Risk Manager Agent**: Calculates drawdown risk, stop-loss and take-profit target prices, and position limits.
  4. 🤖 **Executive Trader Consensus**: Synthesizes inputs into a single `BUY`, `SELL`, or `HOLD` recommendation, confidence score (0-100%), target price, stop loss, and executive summary.
- **1-Click Agent Trade Execution**: Instantly execute simulated paper trades based on AI consensus recommendations.
- **Audit Trail**: View chronological logs of all past AI agent deliberations.

---

### 4. Algo & Strategy Engine
Automate trading using custom quantitative rules and AI consensus triggers.
- **Custom Rule Builder**: Create trading strategies combining:
  - Technical triggers (RSI Oversold/Overbought thresholds, MA Crossovers).
  - AI Agent Consensus requirement (minimum confidence score filter).
  - Custom capital allocation $ per trade.
- **Strategy Simulation Tick Runner**: Click **Run Strategy Tick** to evaluate active rules against market data and automatically trigger paper trades when conditions match.

---

### 5. Order History
Complete audit trail table for all executed paper orders.
- Records Timestamp, Symbol, Side (`BUY`/`SELL`), Shares, Execution Price, Total Value, Trigger Source (`MANUAL`, `RULE`, or `AGENT`), and Reasoning.

---

## 🛠️ Environment Configuration & API Keys

### Google Gemini API Key (Optional)
AgentTrader includes a built-in heuristic reasoning fallback. To activate live Gemini AI agent debates:
```bash
export GEMINI_API_KEY="your-google-gemini-api-key"
python3 /home/brad/Documents/antigravity/Trader/backend/server.py
```

### Resetting Portfolio
To reset your paper trading balance back to **$100,000.00 cash** and clear active positions:
- Click the **🔄 Reset** icon in the top header bar of the Web UI, or
- Post to `/api/portfolio/reset`:
  ```bash
  curl -X POST http://localhost:8000/api/portfolio/reset
  ```

---

## 🌐 Nginx Network Proxy Setup (LAN / Web)

To access AgentTrader from any device (phone, tablet, laptop) on your local network on standard port 80:

1. Install Nginx:
   ```bash
   sudo apt update && sudo apt install nginx -y
   ```
2. Copy configuration:
   ```bash
   sudo cp /home/brad/Documents/antigravity/Trader/nginx.conf /etc/nginx/sites-available/agenttrader
   sudo ln -sf /etc/nginx/sites-available/agenttrader /etc/nginx/sites-enabled/default
   ```
3. Reload Nginx:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Access via browser:
   `http://<YOUR-SERVER-IP>`
