from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Account(Base):
    __tablename__ = "account"
    
    id = Column(Integer, primary_order=1, primary_key=True, index=True)
    cash_balance = Column(Float, default=100000.0)
    initial_capital = Column(Float, default=100000.0)
    currency = Column(String, default="USD")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

class WatchlistItem(Base):
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    asset_type = Column(String, default="Stock") # Stock or ETF
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class StrategyRule(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False) # e.g., 'AAPL', 'SPY', or 'ALL'
    rsi_buy_threshold = Column(Float, default=30.0)
    rsi_sell_threshold = Column(Float, default=70.0)
    ma_fast = Column(Integer, default=20)
    ma_slow = Column(Integer, default=50)
    use_ma_cross = Column(Boolean, default=True)
    use_agent_consensus = Column(Boolean, default=True)
    agent_min_confidence = Column(Float, default=70.0)
    allocation_amount = Column(Float, default=5000.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    asset_type = Column(String, default="Stock")
    shares = Column(Float, nullable=False, default=0.0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False) # BUY or SELL
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    order_type = Column(String, default="MARKET") # MARKET or LIMIT
    status = Column(String, default="FILLED") # FILLED, PENDING, CANCELLED
    triggered_by = Column(String, default="MANUAL") # MANUAL, RULE, AGENT
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    total_equity = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    day_pnl = Column(Float, default=0.0)
    cumulative_pnl = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    agent_name = Column(String, nullable=False) # Technical Analyst, Sentiment Analyst, Risk Manager, Executive Trader
    stance = Column(String, nullable=False) # BULLISH, BEARISH, NEUTRAL
    confidence = Column(Float, nullable=False) # 0 to 100
    reasoning = Column(Text, nullable=False)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
