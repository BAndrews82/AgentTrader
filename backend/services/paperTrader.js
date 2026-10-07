import { dbRun, dbGet, dbAll } from '../db.js';
import { getQuote, getCandles } from './marketData.js';
import { calculateTechnicalIndicators } from './indicators.js';
import { analyzeSymbolMultiAgent } from './agentEngine.js';

export async function getPortfolioSummary() {
  const account = await dbGet('SELECT * FROM account LIMIT 1');
  if (!account) throw new Error('Account record missing');

  const positions = await dbAll('SELECT * FROM positions WHERE shares > 0');

  let positionsValue = 0.0;
  let totalUnrealizedPnl = 0.0;
  let totalRealizedPnl = 0.0;

  const updatedPositions = [];
  for (const pos of positions) {
    const quote = await getQuote(pos.symbol);
    const currPrice = quote.current_price;
    const marketVal = pos.shares * currPrice;
    const unrealized = (currPrice - pos.avg_cost) * pos.shares;

    await dbRun(
      'UPDATE positions SET current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [currPrice, Math.round(unrealized * 100) / 100, pos.id]
    );

    positionsValue += marketVal;
    totalUnrealizedPnl += unrealized;
    totalRealizedPnl += pos.realized_pnl;

    updatedPositions.push({
      id: pos.id,
      symbol: pos.symbol,
      name: pos.name,
      asset_type: pos.asset_type,
      shares: Math.round(pos.shares * 10000) / 10000,
      avg_cost: Math.round(pos.avg_cost * 100) / 100,
      current_price: Math.round(currPrice * 100) / 100,
      market_value: Math.round(marketVal * 100) / 100,
      unrealized_pnl: Math.round(unrealized * 100) / 100,
      realized_pnl: Math.round(pos.realized_pnl * 100) / 100,
      pnl_percent: pos.avg_cost > 0 ? Math.round(((currPrice - pos.avg_cost) / pos.avg_cost * 100) * 100) / 100 : 0.0
    });
  }

  const totalEquity = account.cash_balance + positionsValue;
  const cumulativePnl = totalEquity - account.initial_capital;

  return {
    cash_balance: Math.round(account.cash_balance * 100) / 100,
    initial_capital: Math.round(account.initial_capital * 100) / 100,
    positions_value: Math.round(positionsValue * 100) / 100,
    total_equity: Math.round(totalEquity * 100) / 100,
    unrealized_pnl: Math.round(totalUnrealizedPnl * 100) / 100,
    realized_pnl: Math.round(totalRealizedPnl * 100) / 100,
    cumulative_pnl: Math.round(cumulativePnl * 100) / 100,
    cumulative_pnl_percent: Math.round((cumulativePnl / account.initial_capital * 100) * 100) / 100,
    positions: updatedPositions
  };
}

export async function executeOrder({ symbol, side, shares, order_type = 'MARKET', price, triggered_by = 'MANUAL', reasoning = 'Manual trade' }) {
  const sym = symbol.trim().toUpperCase();
  const orderSide = side.trim().toUpperCase();

  if (orderSide !== 'BUY' && orderSide !== 'SELL') {
    throw new Error('Order side must be BUY or SELL');
  }
  if (!shares || shares <= 0) {
    throw new Error('Shares must be greater than 0');
  }

  const quote = await getQuote(sym);
  const execPrice = price && price > 0 ? price : quote.current_price;
  const totalCost = shares * execPrice;

  const account = await dbGet('SELECT * FROM account LIMIT 1');
  const position = await dbGet('SELECT * FROM positions WHERE symbol = ?', [sym]);

  if (orderSide === 'BUY') {
    if (account.cash_balance < totalCost) {
      throw new Error(`Insufficient cash. Required: $${totalCost.toFixed(2)}, Available: $${account.cash_balance.toFixed(2)}`);
    }

    const newCash = account.cash_balance - totalCost;
    await dbRun('UPDATE account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', [newCash, account.id]);

    if (position) {
      const totalShares = position.shares + shares;
      const newAvgCost = ((position.shares * position.avg_cost) + totalCost) / totalShares;
      await dbRun(
        'UPDATE positions SET shares = ?, avg_cost = ?, current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        [totalShares, newAvgCost, execPrice, (execPrice - newAvgCost) * totalShares, position.id]
      );
    } else {
      await dbRun(
        'INSERT INTO positions (symbol, name, asset_type, shares, avg_cost, current_price, unrealized_pnl, realized_pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [sym, quote.name, quote.asset_type, shares, execPrice, execPrice, 0.0, 0.0]
      );
    }
  } else if (orderSide === 'SELL') {
    if (!position || position.shares < shares) {
      const avail = position ? position.shares : 0;
      throw new Error(`Insufficient shares of ${sym} to sell. Requested: ${shares}, Available: ${avail}`);
    }

    const newCash = account.cash_balance + totalCost;
    await dbRun('UPDATE account SET cash_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', [newCash, account.id]);

    const realized = (execPrice - position.avg_cost) * shares;
    const remainingShares = position.shares - shares;
    const newRealizedPnl = position.realized_pnl + realized;

    if (remainingShares <= 0.0001) {
      await dbRun('UPDATE positions SET shares = 0.0, unrealized_pnl = 0.0, realized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', [newRealizedPnl, position.id]);
    } else {
      await dbRun(
        'UPDATE positions SET shares = ?, realized_pnl = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        [remainingShares, newRealizedPnl, (execPrice - position.avg_cost) * remainingShares, position.id]
      );
    }
  }

  const orderRes = await dbRun(
    'INSERT INTO orders (symbol, side, shares, price, total_value, order_type, status, triggered_by, reasoning) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
    [sym, orderSide, shares, execPrice, totalCost, order_type, 'FILLED', triggered_by, reasoning]
  );

  const summary = await getPortfolioSummary();
  await dbRun(
    'INSERT INTO portfolio_snapshots (total_equity, cash_balance, positions_value, cumulative_pnl) VALUES (?, ?, ?, ?)',
    [summary.total_equity, summary.cash_balance, summary.positions_value, summary.cumulative_pnl]
  );

  return await dbGet('SELECT * FROM orders WHERE id = ?', [orderRes.lastID]);
}

export async function evaluateStrategiesAndRunTick() {
  const strategies = await dbAll('SELECT * FROM strategies WHERE active = 1');
  const evaluations = [];

  for (const strg of strategies) {
    try {
      const sym = strg.symbol;
      const quote = await getQuote(sym);
      const candles = await getCandles(sym, '1mo');
      const indicators = calculateTechnicalIndicators(candles);

      let techMatchBuy = false;
      let techMatchSell = false;

      if (indicators.rsi <= strg.rsi_buy_threshold) techMatchBuy = true;
      else if (indicators.rsi >= strg.rsi_sell_threshold) techMatchSell = true;

      if (strg.use_ma_cross) {
        if (indicators.ema_9 > indicators.ema_21 && indicators.sma_20 > indicators.sma_50) {
          techMatchBuy = true;
        } else if (indicators.ema_9 < indicators.ema_21) {
          techMatchSell = true;
        }
      }

      let agentConsensus = null;
      if (strg.use_agent_consensus) {
        agentConsensus = await analyzeSymbolMultiAgent(sym);
        if (agentConsensus) {
          for (const key of ['technical_agent', 'sentiment_agent', 'risk_agent']) {
            const agentData = agentConsensus[key];
            if (agentData) {
              await dbRun(
                'INSERT INTO agent_logs (symbol, agent_name, stance, confidence, reasoning, target_price, stop_loss, take_profit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                [sym, agentData.agent_name, agentData.stance, agentData.confidence, agentData.reasoning, agentConsensus.target_price, agentConsensus.stop_loss, agentConsensus.take_profit]
              );
            }
          }
        }
      }

      let tradeExecuted = null;
      if (techMatchBuy) {
        const agentOk = !strg.use_agent_consensus || (agentConsensus && agentConsensus.consensus_action === 'BUY' && agentConsensus.consensus_confidence >= strg.agent_min_confidence);
        if (agentOk) {
          const price = quote.current_price;
          const shares = Math.round((strg.allocation_amount / price) * 10000) / 10000;
          if (shares > 0) {
            try {
              const order = await executeOrder({
                symbol: sym,
                side: 'BUY',
                shares,
                price,
                triggered_by: 'RULE',
                reasoning: `Strategy '${strg.name}' trigger: RSI ${indicators.rsi}, Agent Consensus ${agentConsensus ? agentConsensus.consensus_action : 'N/A'}`
              });
              tradeExecuted = `BUY ${shares} shares at $${price}`;
            } catch (err) {
              tradeExecuted = `Signal BUY triggered, order failed: ${err.message}`;
            }
          }
        }
      } else if (techMatchSell) {
        const pos = await dbGet('SELECT * FROM positions WHERE symbol = ? AND shares > 0', [sym]);
        if (pos) {
          try {
            const order = await executeOrder({
              symbol: sym,
              side: 'SELL',
              shares: pos.shares,
              price: quote.current_price,
              triggered_by: 'RULE',
              reasoning: `Strategy '${strg.name}' sell trigger: RSI ${indicators.rsi}`
            });
            tradeExecuted = `SELL ${pos.shares} shares at $${quote.current_price}`;
          } catch (err) {
            tradeExecuted = `Signal SELL triggered, order failed: ${err.message}`;
          }
        }
      }

      evaluations.push({
        strategy_id: strg.id,
        strategy_name: strg.name,
        symbol: sym,
        tech_rsi: indicators.rsi,
        tech_score: indicators.score,
        agent_action: agentConsensus ? agentConsensus.consensus_action : 'N/A',
        agent_confidence: agentConsensus ? agentConsensus.consensus_confidence : 0,
        trade_executed: tradeExecuted || 'No trade conditions met'
      });
    } catch (err) {
      evaluations.push({
        strategy_id: strg.id,
        strategy_name: strg.name,
        symbol: strg.symbol,
        error: err.message
      });
    }
  }

  return evaluations;
}
