import React, { useState } from 'react';
import { Sliders, Plus, Play, Trash2, CheckCircle2, XCircle, ShieldCheck, Zap, ToggleLeft, ToggleRight } from 'lucide-react';

export default function StrategyBuilder({
  strategies,
  onCreateStrategy,
  onToggleStrategy,
  onDeleteStrategy,
  onRunSimulationTick,
  evaluations
}) {
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    symbol: 'SPY',
    rsi_buy_threshold: 35.0,
    rsi_sell_threshold: 70.0,
    ma_fast: 20,
    ma_slow: 50,
    use_ma_cross: true,
    use_agent_consensus: true,
    agent_min_confidence: 70.0,
    allocation_amount: 5000.0,
    active: true
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    onCreateStrategy(formData);
    setShowModal(false);
    setFormData({
      name: '',
      symbol: 'SPY',
      rsi_buy_threshold: 35.0,
      rsi_sell_threshold: 70.0,
      ma_fast: 20,
      ma_slow: 50,
      use_ma_cross: true,
      use_agent_consensus: true,
      agent_min_confidence: 70.0,
      allocation_amount: 5000.0,
      active: true
    });
  };

  return (
    <div className="space-y-6">
      
      {/* Header Controls */}
      <div className="glass-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-blue-400" /> Algorithmic & Agentic Strategy Builder
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Combine technical quantitative indicators (RSI, MA Crossovers) with AI Agent consensus triggers for automated paper trading.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRunSimulationTick}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-semibold text-xs rounded-xl shadow-lg transition-all active:scale-95"
          >
            <Zap className="w-4 h-4 fill-white" /> Run Strategy Tick Simulation
          </button>

          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-lg transition-all"
          >
            <Plus className="w-4 h-4" /> Create Strategy
          </button>
        </div>
      </div>

      {/* Strategy Rule Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {strategies.map((strg) => (
          <div key={strg.id} className={`glass-card p-6 space-y-4 relative ${strg.active ? 'border-blue-500/30' : 'opacity-60'}`}>
            
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">{strg.name}</h3>
                  <span className="badge badge-purple mono">{strg.symbol}</span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">Allocation: <strong className="text-emerald-400 mono">${strg.allocation_amount?.toFixed(2)}</strong></p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => onToggleStrategy(strg.id)}
                  className="p-1 text-slate-400 hover:text-white transition-colors"
                  title={strg.active ? 'Disable Strategy' : 'Enable Strategy'}
                >
                  {strg.active ? <ToggleRight className="w-6 h-6 text-emerald-400" /> : <ToggleLeft className="w-6 h-6 text-slate-600" />}
                </button>

                <button
                  onClick={() => onDeleteStrategy(strg.id)}
                  className="p-1 text-slate-600 hover:text-rose-400 transition-colors"
                  title="Delete strategy"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Rules Breakdown */}
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-900/80 p-3.5 rounded-xl border border-slate-800/80 mono">
              <div>
                <span className="text-slate-500">RSI Buy Threshold:</span>
                <div className="text-slate-200 font-semibold">RSI &le; {strg.rsi_buy_threshold}</div>
              </div>
              <div>
                <span className="text-slate-500">RSI Sell Threshold:</span>
                <div className="text-slate-200 font-semibold">RSI &ge; {strg.rsi_sell_threshold}</div>
              </div>
              <div>
                <span className="text-slate-500">Moving Average:</span>
                <div className="text-slate-200 font-semibold">{strg.ma_fast} EMA / {strg.ma_slow} SMA</div>
              </div>
              <div>
                <span className="text-slate-500">AI Agent Consensus:</span>
                <div className="text-purple-400 font-semibold">{strg.use_agent_consensus ? `Enabled (${strg.agent_min_confidence}%)` : 'Disabled'}</div>
              </div>
            </div>

          </div>
        ))}
      </div>

      {/* Simulation Log Feed */}
      {evaluations && evaluations.length > 0 && (
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Zap className="w-4 h-4 text-purple-400" /> Last Tick Simulation Results
          </h3>
          <div className="space-y-2 max-h-60 overflow-y-auto pr-2">
            {evaluations.map((ev, i) => (
              <div key={i} className="p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs flex items-center justify-between gap-4 mono">
                <div>
                  <div className="font-bold text-slate-200">{ev.strategy_name} ({ev.symbol})</div>
                  <div className="text-[11px] text-slate-400">
                    RSI: {ev.rsi} | AI Action: <span className="text-purple-300">{ev.agent_action}</span> ({ev.agent_confidence}%)
                  </div>
                </div>
                <span className={`badge ${ev.trade_executed?.includes('BUY') ? 'badge-gain' : (ev.trade_executed?.includes('SELL') ? 'badge-loss' : 'badge-neutral')}`}>
                  {ev.trade_executed}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create Strategy Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
          <div className="glass-card p-6 max-w-lg w-full space-y-5 border-blue-500/30">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100">Create New Algo & Agent Strategy</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-500 hover:text-slate-200 text-lg">&times;</button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Strategy Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. S&P 500 Oversold AI Dip Strategy"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">Target Symbol</label>
                  <input
                    type="text"
                    required
                    value={formData.symbol}
                    onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                    placeholder="e.g. SPY, AAPL"
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 mono uppercase focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Allocation Capital ($)</label>
                  <input
                    type="number"
                    required
                    value={formData.allocation_amount}
                    onChange={(e) => setFormData({ ...formData, allocation_amount: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 mono focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">RSI Buy Threshold (&le;)</label>
                  <input
                    type="number"
                    value={formData.rsi_buy_threshold}
                    onChange={(e) => setFormData({ ...formData, rsi_buy_threshold: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">RSI Sell Threshold (&ge;)</label>
                  <input
                    type="number"
                    value={formData.rsi_sell_threshold}
                    onChange={(e) => setFormData({ ...formData, rsi_sell_threshold: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-900 rounded-xl border border-slate-800">
                <div>
                  <div className="font-semibold text-slate-200">Require AI Agent Consensus</div>
                  <div className="text-[11px] text-slate-500">Only execute trade if AI Agents reach BUY consensus</div>
                </div>
                <input
                  type="checkbox"
                  checked={formData.use_agent_consensus}
                  onChange={(e) => setFormData({ ...formData, use_agent_consensus: e.target.checked })}
                  className="w-4 h-4 accent-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold shadow-lg shadow-blue-500/20"
                >
                  Create Strategy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
