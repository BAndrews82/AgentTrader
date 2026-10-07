from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.database import engine, Base, get_db
from app.models import Account, WatchlistItem, StrategyRule, Position, Order, PortfolioSnapshot, AgentLog
from app import schemas
from app.services.market_data import search_tickers, get_quote, get_candles, get_company_news
from app.services.technical_analysis import calculate_technical_indicators
from app.services.agents import analyze_symbol_multi_agent
from app.services.paper_trader import get_or_create_account, get_portfolio_summary, execute_order, evaluate_strategies_and_run_tick

# Create Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AgentTrader API",
    description="Algorithmic and Multi-Agent Paper Trading Engine with FastAPI & yfinance",
    version="1.0.0"
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_db_seed():
    db = next(get_db())
    get_or_create_account(db)
    
    # Seed default watchlist if empty
    if db.query(WatchlistItem).count() == 0:
        default_items = [
            {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "Stock"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "asset_type": "Stock"},
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "asset_type": "ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_type": "ETF"},
            {"symbol": "TSLA", "name": "Tesla, Inc.", "asset_type": "Stock"},
            {"symbol": "SCHD", "name": "Schwab U.S. Dividend Equity ETF", "asset_type": "ETF"}
        ]
        for item in default_items:
            db.add(WatchlistItem(**item))
        db.commit()
        
    # Seed default strategy if empty
    if db.query(StrategyRule).count() == 0:
        db.add(StrategyRule(
            name="RSI Oversold + Agent Consensus Buy",
            symbol="SPY",
            rsi_buy_threshold=35.0,
            rsi_sell_threshold=70.0,
            ma_fast=20,
            ma_slow=50,
            use_ma_cross=True,
            use_agent_consensus=True,
            agent_min_confidence=70.0,
            allocation_amount=5000.0,
            active=True
        ))
        db.add(StrategyRule(
            name="Tech Growth Momentum Strategy",
            symbol="NVDA",
            rsi_buy_threshold=40.0,
            rsi_sell_threshold=75.0,
            ma_fast=9,
            ma_slow=21,
            use_ma_cross=True,
            use_agent_consensus=True,
            agent_min_confidence=75.0,
            allocation_amount=7500.0,
            active=True
        ))
        db.commit()

@app.get("/")
def root():
    return {"status": "ok", "app": "AgentTrader API", "version": "1.0.0"}

# --- PORTFOLIO & ACCOUNT ENDPOINTS ---
@app.get("/api/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    return get_portfolio_summary(db)

@app.get("/api/portfolio/snapshots")
def get_portfolio_snapshots(db: Session = Depends(get_db)):
    snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.asc()).limit(100).all()
    if not snapshots:
        # Generate initial snapshot
        summary = get_portfolio_summary(db)
        return [{
            "timestamp": "Initial",
            "total_equity": summary["total_equity"],
            "cash_balance": summary["cash_balance"],
            "positions_value": summary["positions_value"],
            "cumulative_pnl": 0.0
        }]
    return snapshots

@app.post("/api/portfolio/reset")
def reset_portfolio(db: Session = Depends(get_db)):
    db.query(Order).delete()
    db.query(Position).delete()
    db.query(PortfolioSnapshot).delete()
    
    account = get_or_create_account(db)
    account.cash_balance = 100000.0
    account.initial_capital = 100000.0
    db.commit()
    
    return {"message": "Portfolio reset to $100,000 cash balance"}

# --- WATCHLIST ENDPOINTS ---
@app.get("/api/watchlist")
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(WatchlistItem).all()
    results = []
    for item in items:
        quote = get_quote(item.symbol)
        results.append({
            "id": item.id,
            "symbol": item.symbol,
            "name": item.name,
            "asset_type": item.asset_type,
            "quote": quote
        })
    return results

@app.post("/api/watchlist", response_model=schemas.WatchlistResponse)
def add_to_watchlist(data: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    symbol = data.symbol.strip().upper()
    existing = db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol).first()
    if existing:
        return existing
        
    quote = get_quote(symbol)
    name = data.name or quote["name"]
    asset_type = data.asset_type or quote["asset_type"]
    
    item = WatchlistItem(symbol=symbol, name=name, asset_type=asset_type)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/watchlist/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.strip().upper()
    db.query(WatchlistItem).filter(WatchlistItem.symbol == symbol).delete()
    db.commit()
    return {"message": f"Removed {symbol} from watchlist"}

# --- MARKET DATA ENDPOINTS ---
@app.get("/api/market/search")
def api_search_tickers(q: str = Query("", description="Search ticker or company name")):
    return search_tickers(q)

@app.get("/api/market/quote/{symbol}")
def api_get_quote(symbol: str):
    return get_quote(symbol)

@app.get("/api/market/candles/{symbol}")
def api_get_candles(symbol: str, period: str = "3mo", interval: str = "1d"):
    return get_candles(symbol, period=period, interval=interval)

@app.get("/api/market/news/{symbol}")
def api_get_news(symbol: str):
    return get_company_news(symbol)

@app.get("/api/market/indicators/{symbol}")
def api_get_indicators(symbol: str):
    candles = get_candles(symbol, period="3mo", interval="1d")
    return calculate_technical_indicators(candles)

# --- STRATEGY ENDPOINTS ---
@app.get("/api/strategies", response_model=List[schemas.StrategyResponse])
def get_strategies(db: Session = Depends(get_db)):
    return db.query(StrategyRule).all()

@app.post("/api/strategies", response_model=schemas.StrategyResponse)
def create_strategy(data: schemas.StrategyCreate, db: Session = Depends(get_db)):
    rule = StrategyRule(**data.dict())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@app.put("/api/strategies/{strategy_id}/toggle")
def toggle_strategy(strategy_id: int, db: Session = Depends(get_db)):
    rule = db.query(StrategyRule).filter(StrategyRule.id == strategy_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Strategy not found")
    rule.active = not rule.active
    db.commit()
    return {"id": rule.id, "active": rule.active}

@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db.query(StrategyRule).filter(StrategyRule.id == strategy_id).delete()
    db.commit()
    return {"message": "Strategy deleted"}

# --- ORDERS & TRADING ENDPOINTS ---
@app.get("/api/orders", response_model=List[schemas.OrderResponse])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc()).limit(100).all()

@app.post("/api/orders", response_model=schemas.OrderResponse)
def place_order(data: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        order = execute_order(
            db=db,
            symbol=data.symbol,
            side=data.side,
            shares=data.shares,
            order_type=data.order_type or "MARKET",
            price=data.price,
            triggered_by=data.triggered_by or "MANUAL",
            reasoning=data.reasoning or "Manual trade execution"
        )
        return order
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

# --- AGENT & SIMULATION ENDPOINTS ---
@app.post("/api/agents/analyze/{symbol}", response_model=schemas.MultiAgentConsensusResponse)
def run_agent_analysis(symbol: str, db: Session = Depends(get_db)):
    analysis = analyze_symbol_multi_agent(symbol)
    
    # Save logs to DB
    for key in ["technical_agent", "sentiment_agent", "risk_agent"]:
        adata = analysis.get(key)
        if adata:
            log = AgentLog(
                symbol=symbol,
                agent_name=adata["agent_name"],
                stance=adata["stance"],
                confidence=adata["confidence"],
                reasoning=adata["reasoning"],
                target_price=analysis.get("target_price"),
                stop_loss=analysis.get("stop_loss"),
                take_profit=analysis.get("take_profit")
            )
            db.add(log)
    db.commit()
    return analysis

@app.get("/api/agents/logs", response_model=List[schemas.AgentLogResponse])
def get_agent_logs(db: Session = Depends(get_db)):
    return db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(50).all()

@app.post("/api/simulation/tick")
def run_simulation_tick(db: Session = Depends(get_db)):
    tick_results = evaluate_strategies_and_run_tick(db)
    return {"status": "success", "evaluations": tick_results}
