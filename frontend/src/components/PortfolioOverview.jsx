import React, { useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, PieChart, Activity, ArrowUpRight, ArrowDownRight, Layers, Bot, ShoppingCart } from 'lucide-react';

export default function PortfolioOverview({ portfolio, snapshots, onQuickSell, onSelectSymbolForAnalysis }) {
  const positions = portfolio?.positions || [];
  const totalEquity = portfolio?.total_equity || 100000;
  const cash = portfolio?.cash_balance || 100000;
  const posVal = portfolio?.positions_value || 0;
  const unrealized = portfolio?.unrealized_pnl || 0;
  const realized = portfolio?.realized_pnl || 0;
  const cumPnl = portfolio?.cumulative_pnl || 0;

  // Simple SVG sparkline curve generator for snapshots
  const renderEquityCurve = () => {
    if (!snapshots || snapshots.length < 2) {
      return (
        <div className="h-44 flex items-center justify-center text-xs text-slate-500 italic">
          Equity curve will populate as paper trades execute over time.
        </div>
      );
    }
    const values = snapshots.map(s => s.total_equity);
    const minVal = Math.min(...values) * 0.995;
    const maxVal = Math.max(...values) * 1.005;
    const width = 600;
    const height = 160;

    const points = values.map((val, idx) => {
      const x = (idx / (values.length - 1)) * width;
      const y = height - ((val - minVal) / (maxVal - minVal || 1)) * height;
      return `${x},${y}`;
    }).join(' ');

    const isGain = values[values.length - 1] >= values[0];
    const strokeColor = isGain ? '#10b981' : '#f43f5e';

    return (
      <div className="relative w-full h-44">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <polygon
            points={`0,${height} ${points} ${width},${height}`}
            fill="url(#equityGrad)"
          />
          <polyline
            fill="none"
            stroke={strokeColor}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
          />
        </svg>
        <div className="flex justify-between items-center text-[10px] text-slate-500 mt-2 font-mono">
          <span>Start: ${values[0].toLocaleString(undefined, {minimumFractionDigits:2})}</span>
          <span>Current: ${values[values.length - 1].toLocaleString(undefined, {minimumFractionDigits:2})}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      
      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Net Worth */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Net Worth (Total Equity)</span>
            <DollarSign className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold mono text-white">
            ${totalEquity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
          <div className="mt-2 flex items-center gap-1 text-xs">
            {cumPnl >= 0 ? (
              <span className="text-emerald-400 font-semibold flex items-center">
                <ArrowUpRight className="w-3.5 h-3.5" /> +${cumPnl.toFixed(2)} ({((cumPnl / 100000) * 100).toFixed(2)}%)
              </span>
            ) : (
              <span className="text-rose-400 font-semibold flex items-center">
                <ArrowDownRight className="w-3.5 h-3.5" /> -${Math.abs(cumPnl).toFixed(2)} ({((cumPnl / 100000) * 100).toFixed(2)}%)
              </span>
            )}
            <span className="text-slate-500">all time</span>
          </div>
        </div>

        {/* Cash Balance */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Available Cash</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold mono text-white">
            ${cash.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {((cash / totalEquity) * 100).toFixed(1)}% of portfolio liquid
          </div>
        </div>

        {/* Holdings Value */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Invested Holdings</span>
            <PieChart className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold mono text-white">
            ${posVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {positions.length} active paper position{positions.length === 1 ? '' : 's'}
          </div>
        </div>

        {/* Unrealized P&L */}
        <div className="glass-card p-5">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Unrealized P&L</span>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>
          <div className={`text-2xl font-bold mono ${unrealized >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {unrealized >= 0 ? '+' : ''}${unrealized.toFixed(2)}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Realized P&L: <span className={realized >= 0 ? 'text-emerald-400' : 'text-rose-400'}>${realized.toFixed(2)}</span>
          </div>
        </div>

      </div>

      {/* Equity Curve & Portfolio Allocations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Equity Curve Chart */}
        <div className="lg:col-span-2 glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Portfolio Performance Curve</h3>
              <p className="text-xs text-slate-400">Simulated total net worth trajectory</p>
            </div>
            <span className="badge badge-blue">Live Snapshot</span>
          </div>
          {renderEquityCurve()}
        </div>

        {/* Asset Breakdown Summary */}
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-slate-200 mb-4">Holdings Allocation</h3>
          {positions.length === 0 ? (
            <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
              <ShoppingCart className="w-8 h-8 mb-2 opacity-50" />
              No active paper positions yet. Use Watchlist or AI Agents to place your first trade!
            </div>
          ) : (
            <div className="space-y-3">
              {positions.map((pos) => {
                const pct = posVal > 0 ? ((pos.market_value / posVal) * 100).toFixed(1) : 0;
                return (
                  <div key={pos.symbol} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-bold text-slate-200">{pos.symbol} ({pos.asset_type})</span>
                      <span className="mono text-slate-400">${pos.market_value.toFixed(2)} ({pct}%)</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                        style={{ width: `${Math.min(100, Math.max(5, pct))}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>

      {/* Active Positions Table */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">Active Portfolio Positions</h3>
            <p className="text-xs text-slate-400">Live paper trading positions & market P&L</p>
          </div>
          <span className="text-xs text-slate-400 font-mono">{positions.length} Positions</span>
        </div>

        {positions.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            Your portfolio is currently 100% cash ($100,000.00). Search assets in the Watchlist tab to open paper trades.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Symbol / Name</th>
                  <th>Asset Class</th>
                  <th>Quantity</th>
                  <th>Avg Cost</th>
                  <th>Current Price</th>
                  <th>Market Value</th>
                  <th>Unrealized P&L</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const isGain = pos.unrealized_pnl >= 0;
                  return (
                    <tr key={pos.symbol}>
                      <td>
                        <div className="font-bold text-slate-100 flex items-center gap-2">
                          {pos.symbol}
                          <button
                            onClick={() => onSelectSymbolForAnalysis(pos.symbol)}
                            className="p-1 text-purple-400 hover:bg-purple-500/10 rounded transition-colors"
                            title="Analyze with AI Agents"
                          >
                            <Bot className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="text-xs text-slate-400 truncate max-w-[160px]">{pos.name}</div>
                      </td>
                      <td>
                        <span className={`badge ${pos.asset_type === 'ETF' ? 'badge-purple' : 'badge-blue'}`}>
                          {pos.asset_type}
                        </span>
                      </td>
                      <td className="mono">{pos.shares}</td>
                      <td className="mono">${pos.avg_cost.toFixed(2)}</td>
                      <td className="mono font-semibold text-slate-100">${pos.current_price.toFixed(2)}</td>
                      <td className="mono font-semibold">${pos.market_value.toFixed(2)}</td>
                      <td>
                        <span className={`badge ${isGain ? 'badge-gain' : 'badge-loss'} mono`}>
                          {isGain ? '+' : ''}${pos.unrealized_pnl.toFixed(2)} ({isGain ? '+' : ''}{pos.pnl_percent.toFixed(2)}%)
                        </span>
                      </td>
                      <td className="text-right">
                        <button
                          onClick={() => onQuickSell(pos)}
                          className="px-2.5 py-1 text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg transition-colors"
                        >
                          Close Position
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
