import React from 'react';
import { Bot, TrendingUp, ShieldAlert, BarChart3, ListFilter, Cpu, History, RotateCcw, Wallet, Zap } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, portfolio, onResetAccount, onRunSimulationTick, simLoading }) {
  const netWorth = portfolio?.total_equity || 100000;
  const cash = portfolio?.cash_balance || 100000;
  const pnl = portfolio?.cumulative_pnl || 0;
  const pnlPct = portfolio?.cumulative_pnl_percent || 0;
  const isGain = pnl >= 0;

  return (
    <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-6 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand Logo & Agent Status */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-purple-600 to-emerald-500 p-0.5 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Bot className="w-5 h-5 text-purple-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                AgentTrader <span className="text-purple-400 text-xs font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">AI Paper Trading</span>
              </h1>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Multi-Agent Team Active & Ready (Gemini 3.8 Flash)
            </p>
          </div>
        </div>

        {/* Live Account Bar */}
        <div className="flex items-center gap-4 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2">
          <div className="flex items-center gap-2 border-r border-slate-800 pr-4">
            <Wallet className="w-4 h-4 text-blue-400" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Net Worth</div>
              <div className="text-sm font-bold mono text-slate-100">${netWorth.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 border-r border-slate-800 pr-4">
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Cash Balance</div>
              <div className="text-sm font-semibold mono text-slate-300">${cash.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
            </div>
          </div>

          <div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Total Paper P&L</div>
            <div className={`text-sm font-bold mono flex items-center gap-1 ${isGain ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isGain ? '+' : ''}${pnl.toFixed(2)} ({isGain ? '+' : ''}{pnlPct.toFixed(2)}%)
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRunSimulationTick}
            disabled={simLoading}
            className="flex items-center gap-1.5 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-medium text-xs px-3.5 py-2 rounded-lg transition-all shadow-md shadow-purple-500/20 active:scale-95 disabled:opacity-50"
            title="Evaluate active strategy rules & AI consensus triggers against market tick"
          >
            <Zap className={`w-3.5 h-3.5 ${simLoading ? 'animate-spin' : ''}`} />
            {simLoading ? 'Executing Tick...' : 'Run Strategy Tick'}
          </button>

          <button
            onClick={onResetAccount}
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors border border-transparent hover:border-rose-500/20"
            title="Reset Paper Account Balance to $100,000"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto flex items-center gap-2 mt-3 pt-2 border-t border-slate-800/60 overflow-x-auto">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'dashboard'
              ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <BarChart3 className="w-4 h-4" /> Portfolio Dashboard
        </button>

        <button
          onClick={() => setActiveTab('watchlist')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'watchlist'
              ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <ListFilter className="w-4 h-4" /> Watchlist & Charts
        </button>

        <button
          onClick={() => setActiveTab('agents')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'agents'
              ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <Cpu className="w-4 h-4 text-purple-400" /> AI Agent Command Center
        </button>

        <button
          onClick={() => setActiveTab('strategies')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'strategies'
              ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <TrendingUp className="w-4 h-4" /> Algo & Rule Engine
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === 'history'
              ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <History className="w-4 h-4" /> Order History
        </button>
      </div>
    </header>
  );
}
