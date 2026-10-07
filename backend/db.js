import sqlite3 from 'sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dbPath = path.join(__dirname, 'trading.db');

export const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Failed to connect to SQLite DB:', err);
  } else {
    console.log('Connected to SQLite DB at:', dbPath);
  }
});

// Helper for promise-based queries
export const dbRun = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
};

export const dbGet = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

export const dbAll = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
};

export async function initDb() {
  await dbRun(`
    CREATE TABLE IF NOT EXISTS account (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cash_balance REAL DEFAULT 100000.0,
      initial_capital REAL DEFAULT 100000.0,
      currency TEXT DEFAULT 'USD',
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
    CREATE TABLE IF NOT EXISTS watchlist (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      asset_type TEXT DEFAULT 'Stock',
      added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
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
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
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
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
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
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      total_equity REAL NOT NULL,
      cash_balance REAL NOT NULL,
      positions_value REAL NOT NULL,
      cumulative_pnl REAL DEFAULT 0.0,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  await dbRun(`
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
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // Seed default account balance if empty
  const acc = await dbGet('SELECT * FROM account LIMIT 1');
  if (!acc) {
    await dbRun('INSERT INTO account (cash_balance, initial_capital) VALUES (100000.0, 100000.0)');
  }

  // Seed default watchlist items if empty
  const countWatch = await dbGet('SELECT COUNT(*) as cnt FROM watchlist');
  if (countWatch && countWatch.cnt === 0) {
    const defaultWatch = [
      { symbol: 'AAPL', name: 'Apple Inc.', asset_type: 'Stock' },
      { symbol: 'NVDA', name: 'NVIDIA Corporation', asset_type: 'Stock' },
      { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', asset_type: 'ETF' },
      { symbol: 'QQQ', name: 'Invesco QQQ Trust', asset_type: 'ETF' },
      { symbol: 'TSLA', name: 'Tesla, Inc.', asset_type: 'Stock' },
      { symbol: 'VOO', name: 'Vanguard S&P 500 ETF', asset_type: 'ETF' }
    ];
    for (const item of defaultWatch) {
      await dbRun('INSERT OR IGNORE INTO watchlist (symbol, name, asset_type) VALUES (?, ?, ?)', [
        item.symbol, item.name, item.asset_type
      ]);
    }
  }

  // Seed default strategies if empty
  const countStrg = await dbGet('SELECT COUNT(*) as cnt FROM strategies');
  if (countStrg && countStrg.cnt === 0) {
    await dbRun(`
      INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, ['S&P 500 Agentic RSI Dip Strategy', 'SPY', 35.0, 70.0, 20, 50, 1, 1, 70.0, 5000.0, 1]);

    await dbRun(`
      INSERT INTO strategies (name, symbol, rsi_buy_threshold, rsi_sell_threshold, ma_fast, ma_slow, use_ma_cross, use_agent_consensus, agent_min_confidence, allocation_amount, active)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, ['Tech Growth Breakout Strategy', 'NVDA', 40.0, 75.0, 9, 21, 1, 1, 75.0, 7500.0, 1]);
  }
}
