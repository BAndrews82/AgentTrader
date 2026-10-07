from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, List
from app.models import Account, Position, Order, StrategyRule, PortfolioSnapshot, AgentLog
from app.services.market_data import get_quote, get_candles
from app.services.technical_analysis import calculate_technical_indicators
from app.services.agents import analyze_symbol_multi_agent

def get_or_create_account(db: Session) -> Account:
    account = db.query(Account).first()
    if not account:
        account = Account(cash_balance=100000.0, initial_capital=100000.0, currency="USD")
        db.add(account)
        db.commit()
        db.refresh(account)
    return account

def get_portfolio_summary(db: Session) -> Dict[str, Any]:
    account = get_or_create_account(db)
    positions = db.query(Position).all()
    
    positions_value = 0.0
    total_unrealized_pnl = 0.0
    total_realized_pnl = 0.0
    
    updated_positions = []
    for pos in positions:
        if pos.shares > 0:
            quote = get_quote(pos.symbol)
            curr_price = quote["current_price"]
            pos.current_price = curr_price
            market_val = pos.shares * curr_price
            unrealized = (curr_price - pos.avg_cost) * pos.shares
            pos.unrealized_pnl = round(unrealized, 2)
            
            positions_value += market_val
            total_unrealized_pnl += unrealized
            total_realized_pnl += pos.realized_pnl
            
            updated_positions.append({
                "id": pos.id,
                "symbol": pos.symbol,
                "name": pos.name,
                "asset_type": pos.asset_type,
                "shares": round(pos.shares, 4),
                "avg_cost": round(pos.avg_cost, 2),
                "current_price": round(curr_price, 2),
                "market_value": round(market_val, 2),
                "unrealized_pnl": round(unrealized, 2),
                "realized_pnl": round(pos.realized_pnl, 2),
                "pnl_percent": round(((curr_price - pos.avg_cost) / pos.avg_cost * 100), 2) if pos.avg_cost > 0 else 0.0
            })
    
    db.commit()
    
    total_equity = account.cash_balance + positions_value
    cumulative_pnl = total_equity - account.initial_capital
    
    return {
        "cash_balance": round(account.cash_balance, 2),
        "initial_capital": round(account.initial_capital, 2),
        "positions_value": round(positions_value, 2),
        "total_equity": round(total_equity, 2),
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "realized_pnl": round(total_realized_pnl, 2),
        "cumulative_pnl": round(cumulative_pnl, 2),
        "cumulative_pnl_percent": round((cumulative_pnl / account.initial_capital * 100), 2),
        "positions": updated_positions
    }

def execute_order(
    db: Session,
    symbol: str,
    side: str,
    shares: float,
    order_type: str = "MARKET",
    price: float = None,
    triggered_by: str = "MANUAL",
    reasoning: str = "Manual paper trade"
) -> Order:
    symbol = symbol.strip().upper()
    side = side.strip().upper()
    
    if side not in ["BUY", "SELL"]:
        raise ValueError("Order side must be BUY or SELL")
        
    quote = get_quote(symbol)
    exec_price = price if price and price > 0 else quote["current_price"]
    total_cost = shares * exec_price
    
    account = get_or_create_account(db)
    position = db.query(Position).filter(Position.symbol == symbol).first()
    
    if side == "BUY":
        if account.cash_balance < total_cost:
            raise ValueError(f"Insufficient cash balance. Required: ${round(total_cost, 2)}, Available: ${round(account.cash_balance, 2)}")
            
        account.cash_balance -= total_cost
        
        if position:
            total_shares = position.shares + shares
            new_avg_cost = ((position.shares * position.avg_cost) + total_cost) / total_shares
            position.shares = total_shares
            position.avg_cost = new_avg_cost
            position.current_price = exec_price
            position.unrealized_pnl = (exec_price - new_avg_cost) * total_shares
        else:
            position = Position(
                symbol=symbol,
                name=quote["name"],
                asset_type=quote["asset_type"],
                shares=shares,
                avg_cost=exec_price,
                current_price=exec_price,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )
            db.add(position)
            
    elif side == "SELL":
        if not position or position.shares < shares:
            avail = position.shares if position else 0
            raise ValueError(f"Insufficient shares of {symbol} to sell. Requested: {shares}, Available: {avail}")
            
        account.cash_balance += total_cost
        
        realized = (exec_price - position.avg_cost) * shares
        position.realized_pnl += realized
        position.shares -= shares
        
        if position.shares <= 0.0001:
            position.shares = 0.0
            position.unrealized_pnl = 0.0
            
    order = Order(
        symbol=symbol,
        side=side,
        shares=shares,
        price=exec_price,
        total_value=total_cost,
        order_type=order_type,
        status="FILLED",
        triggered_by=triggered_by,
        reasoning=reasoning
    )
    db.add(order)
    
    # Take equity snapshot
    summary = get_portfolio_summary(db)
    snapshot = PortfolioSnapshot(
        total_equity=summary["total_equity"],
        cash_balance=summary["cash_balance"],
        positions_value=summary["positions_value"],
        cumulative_pnl=summary["cumulative_pnl"]
    )
    db.add(snapshot)
    
    db.commit()
    db.refresh(order)
    return order

def evaluate_strategies_and_run_tick(db: Session) -> List[Dict[str, Any]]:
    strategies = db.query(StrategyRule).filter(StrategyRule.active == True).all()
    results = []
    
    for strg in strategies:
        try:
            symbol = strg.symbol
            quote = get_quote(symbol)
            candles = get_candles(symbol, period="1mo", interval="1d")
            indicators = calculate_technical_indicators(candles)
            
            tech_match_buy = False
            tech_match_sell = False
            
            # Technical conditions
            if indicators["rsi"] <= strg.rsi_buy_threshold:
                tech_match_buy = True
            elif indicators["rsi"] >= strg.rsi_sell_threshold:
                tech_match_sell = True
                
            if strg.use_ma_cross:
                if indicators["ema_9"] > indicators["ema_21"] and indicators["sma_20"] > indicators["sma_50"]:
                    tech_match_buy = True
                elif indicators["ema_9"] < indicators["ema_21"]:
                    tech_match_sell = True
                    
            # Agent condition
            agent_consensus = None
            if strg.use_agent_consensus:
                agent_consensus = analyze_symbol_multi_agent(symbol)
                
                # Log agent output
                if agent_consensus:
                    for key in ["technical_agent", "sentiment_agent", "risk_agent"]:
                        agent_data = agent_consensus.get(key)
                        if agent_data:
                            log = AgentLog(
                                symbol=symbol,
                                agent_name=agent_data["agent_name"],
                                stance=agent_data["stance"],
                                confidence=agent_data["confidence"],
                                reasoning=agent_data["reasoning"],
                                target_price=agent_consensus.get("target_price"),
                                stop_loss=agent_consensus.get("stop_loss"),
                                take_profit=agent_consensus.get("take_profit")
                            )
                            db.add(log)
                    db.commit()

            # Execute trade if conditions met
            trade_executed = None
            if tech_match_buy:
                if not strg.use_agent_consensus or (agent_consensus and agent_consensus["consensus_action"] == "BUY" and agent_consensus["consensus_confidence"] >= strg.agent_min_confidence):
                    # Check if allocation cash is available
                    price = quote["current_price"]
                    shares = round(strg.allocation_amount / price, 4)
                    if shares > 0:
                        try:
                            order = execute_order(
                                db=db,
                                symbol=symbol,
                                side="BUY",
                                shares=shares,
                                price=price,
                                triggered_by="RULE",
                                reasoning=f"Strategy '{strg.name}' buy signal: RSI {indicators['rsi']}, Agent Consensus: {agent_consensus['consensus_action'] if agent_consensus else 'N/A'}"
                            )
                            trade_executed = f"BUY {shares} shares at ${price}"
                        except Exception as ex:
                            trade_executed = f"Signal BUY triggered but order failed: {ex}"
                            
            elif tech_match_sell:
                pos = db.query(Position).filter(Position.symbol == symbol, Position.shares > 0).first()
                if pos:
                    try:
                        order = execute_order(
                            db=db,
                            symbol=symbol,
                            side="SELL",
                            shares=pos.shares,
                            price=quote["current_price"],
                            triggered_by="RULE",
                            reasoning=f"Strategy '{strg.name}' sell signal: RSI {indicators['rsi']}"
                        )
                        trade_executed = f"SELL {pos.shares} shares at ${quote['current_price']}"
                    except Exception as ex:
                        trade_executed = f"Signal SELL triggered but order failed: {ex}"

            results.append({
                "strategy_id": strg.id,
                "strategy_name": strg.name,
                "symbol": symbol,
                "tech_rsi": indicators["rsi"],
                "tech_score": indicators["score"],
                "agent_action": agent_consensus["consensus_action"] if agent_consensus else "N/A",
                "agent_confidence": agent_consensus["consensus_confidence"] if agent_consensus else 0,
                "trade_executed": trade_executed or "No trade condition met"
            })
            
        except Exception as e:
            results.append({
                "strategy_id": strg.id,
                "strategy_name": strg.name,
                "symbol": strg.symbol,
                "error": str(e)
            })
            
    return results
