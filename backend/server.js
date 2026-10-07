import express from 'express';
import cors from 'cors';
import { initDb, dbAll, dbRun, dbGet } from './db.js';
import { searchTickers, getQuote, getCandles, getCompanyNews } from './services/marketData.js';
import { calculateTechnicalIndicators } from './services/indicators.js';
import { analyzeSymbolMultiAgent } from './services/agentEngine.js';
import { getPortfolioSummary, executeOrder, evaluateStrategiesAndRunTick } from './services/paperTrader.js';

const app = express();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());

// Initialize SQLite database
await initDb();

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', app: 'AgentTrader API', version: '1.0.0' });
});

// --- PORTFOLIO & ACCOUNT ---
app.get('/api/portfolio', async (req, res) => {
  try {
    const summary = await getPortfolioSummary();
    res.json(summary);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/portfolio/snapshots', async (req, res) => {
  try {
    const snapshots = await dbAll('SELECT * FROM portfolio_snapshots ORDER BY timestamp ASC LIMIT 100');
    if (!snapshots || snapshots.length === 0) {
      const summary = await getPortfolioSummary();
      return res.json([{
        timestamp: 'Initial',
        total_equity: summary.total_equity,
        cash_balance: summary.cash_balance,
        positions_value: summary.positions_value,
        cumulative_pnl: 0.0
      }]);
    }
    res.json(snapshots);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/portfolio/reset', async (req, res) => {
  try {
    await dbRun('DELETE FROM orders');
    await dbRun('DELETE FROM positions');
    await dbRun('DELETE FROM portfolio_snapshots');
    await dbRun('UPDATE account SET cash_balance = 100000.0, initial_capital = 100000.0');
    res.json({ message: 'Portfolio reset to $100,000 cash balance' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- WATCHLIST ---
app.get('/api/watchlist', async (req, res) => {
  try {
    const items = await dbAll('SELECT * FROM watchlist');
    const results = [];
    for (const item of items) {
      const quote = await getQuote(item.symbol);
      results.push({
        id: item.id,
        symbol: item.symbol,
        name: item.name,
        asset_type: item.asset_type,
        quote
      });
    }
    res.json(results);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/watchlist', async (req, res) => {
  try {
    const { symbol, name, asset_type } = req.body;
    if (!symbol) return res.status(400).json({ error: 'Symbol is required' });

    const sym = symbol.trim().toUpperCase();
    const existing = await dbGet('SELECT * FROM watchlist WHERE symbol = ?', [sym]);
    if (existing) return res.json(existing);

    const quote = await getQuote(sym);
    const item = await dbRun(
      'INSERT INTO watchlist (symbol, name, asset_type) VALUES (?, ?, ?)',
      [sym, name || quote.name, asset_type || quote.asset_type]
    );
    res.json({ id: item.lastID, symbol: sym, name: name || quote.name, asset_type: asset_type || quote.asset_type });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/watchlist/:symbol', async (req, res) => {
  try {
    const sym = req.params.symbol.trim().toUpperCase();
    await dbRun('DELETE FROM watchlist WHERE symbol = ?', [sym]);
    res.json({ message: `Removed ${sym} from watchlist` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- MARKET DATA ---
app.get('/api/market/search', async (req, res) => {
  try {
    const q = req.query.q || '';
    const results = await searchTickers(q);
    res.json(results);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/market/quote/:symbol', async (req, res) => {
  try {
    const quote = await getQuote(req.params.symbol);
    res.json(quote);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/market/candles/:symbol', async (req, res) => {
  try {
    const period = req.query.period || '3mo';
    const candles = await getCandles(req.params.symbol, period);
    res.json(candles);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/market/news/:symbol', async (req, res) => {
  try {
    const news = await getCompanyNews(req.params.symbol);
    res.json(news);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/market/indicators/:symbol', async (req, res) => {
  try {
    const candles = await getCandles(req.params.symbol, '3mo');
    const indicators = calculateTechnicalIndicators(candles);
    res.json(indicators);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- STRATEGIES ---
app.get('/api/strategies', async (req, res) => {
  try {
    const strategies = await dbAll('SELECT * FROM strategies');
    res.json(strategies);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/strategies', async (req, res) => {
  try {
    const { name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active } = req.body;
    const result = await dbRun(`
      INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [name, symbol, rsi_buy_threshold || 30.0, rsi_sell_threshold || 70.0, ma_fast || 20, ma_slow || 50, use_ma_cross ? 1 : 0, use_agent_consensus ? 1 : 0, agent_min_confidence || 70.0, allocation_amount || 5000.0, active ? 1 : 0]);
    res.json({ id: result.lastID, ...req.body });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/strategies/:id/toggle', async (req, res) => {
  try {
    const strg = await dbGet('SELECT * FROM strategies WHERE id = ?', [req.params.id]);
    if (!strg) return res.status(404).json({ error: 'Strategy not found' });
    const newActive = strg.active ? 0 : 1;
    await dbRun('UPDATE strategies SET active = ? WHERE id = ?', [newActive, strg.id]);
    res.json({ id: strg.id, active: !!newActive });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/strategies/:id', async (req, res) => {
  try {
    await dbRun('DELETE FROM strategies WHERE id = ?', [req.params.id]);
    res.json({ message: 'Strategy deleted' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --- ORDERS ---
app.get('/api/orders', async (req, res) => {
  try {
    const orders = await dbAll('SELECT * FROM orders ORDER BY created_at DESC LIMIT 100');
    res.json(orders);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/orders', async (req, res) => {
  try {
    const order = await executeOrder(req.body);
    res.json(order);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// --- AGENTS & SIMULATION ---
app.post('/api/agents/analyze/:symbol', async (req, res) => {
  try {
    const analysis = await analyzeSymbolMultiAgent(req.params.symbol);
    if (analysis) {
      for (const key of ['technical_agent', 'sentiment_agent', 'risk_agent']) {
        const agentData = analysis[key];
        if (agentData) {
          await dbRun(
            'INSERT INTO agent_logs (symbol, agent_name, stance, confidence, reasoning, target_price, stop_loss, take_profit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [req.params.symbol, agentData.agent_name, agentData.stance, agentData.confidence, agentData.reasoning, analysis.target_price, analysis.stop_loss, analysis.take_profit]
          );
        }
      }
    }
    res.json(analysis);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/agents/logs', async (req, res) => {
  try {
    const logs = await dbAll('SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT 50');
    res.json(logs);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/simulation/tick', async (req, res) => {
  try {
    const evaluations = await evaluateStrategiesAndRunTick();
    res.json({ status: 'success', evaluations });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`AgentTrader Backend running on http://localhost:${PORT}`);
});
