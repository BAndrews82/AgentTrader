from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class WatchlistCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    asset_type: Optional[str] = "Stock"

class WatchlistResponse(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: str
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StrategyCreate(BaseModel):
    name: str
    symbol: str
    rsi_buy_threshold: float = 30.0
    rsi_sell_threshold: float = 70.0
    ma_fast: int = 20
    ma_slow: int = 50
    use_ma_cross: bool = True
    use_agent_consensus: bool = True
    agent_min_confidence: float = 70.0
    allocation_amount: float = 5000.0
    active: bool = True

class StrategyResponse(StrategyCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    symbol: str
    side: str # BUY or SELL
    shares: float
    order_type: Optional[str] = "MARKET"
    price: Optional[float] = None
    triggered_by: Optional[str] = "MANUAL"
    reasoning: Optional[str] = "Manual user order"

class OrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    shares: float
    price: float
    total_value: float
    order_type: str
    status: str
    triggered_by: str
    reasoning: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PositionResponse(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: str
    shares: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float

    class Config:
        from_attributes = True

class AccountResponse(BaseModel):
    cash_balance: float
    initial_capital: float
    positions_value: float
    total_equity: float
    unrealized_pnl: float
    realized_pnl: float
    cumulative_pnl: float

class AgentAnalysisRequest(BaseModel):
    symbol: str

class AgentLogResponse(BaseModel):
    id: int
    symbol: str
    agent_name: str
    stance: str
    confidence: float
    reasoning: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MultiAgentConsensusResponse(BaseModel):
    symbol: str
    current_price: float
    consensus_action: str # BUY, SELL, HOLD
    consensus_confidence: float # 0 to 100
    executive_summary: str
    technical_agent: AgentLogResponse
    sentiment_agent: AgentLogResponse
    risk_agent: AgentLogResponse
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
