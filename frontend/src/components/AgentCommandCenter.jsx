import React, { useState } from 'react';
import { Bot, Cpu, ShieldCheck, TrendingUp, AlertTriangle, CheckCircle2, Play, RefreshCw, Zap, Target } from 'lucide-react';

export default function AgentCommandCenter({
  selectedSymbol,
  agentAnalysis,
  loading,
  onRunAnalysis,
  onExecuteAgentTrade,
  agentLogs
}) {
  const [tickerInput, setTickerInput] = useState(selectedSymbol || 'SPY');

  const handleSubmitAnalysis = (e) => {
    e.preventDefault();
    if (tickerInput.trim()) {
      onRunAnalysis(tickerInput.trim().toUpperCase());
    }
  };

  const consensus = agentAnalysis || {};
  const tech = consensus.technical_agent || {};
  const sent = consensus.sentiment_agent || {};
  const risk = consensus.risk_agent || {};

  const getStanceBadge = (stance) => {
    if (stance === 'BULLISH') return <span className="badge badge-gain">BULLISH</span>;
    if (stance === 'BEARISH') return <span className="badge badge-loss">BEARISH</span>;
    return <span className="badge badge-neutral">NEUTRAL</span>;
  };

  return (
    <div className="space-y-6">
      
      {/* Top Controls: Ticker Selector & Run Analysis */}
      <div className="glass-card p-6 border-purple-500/20 glass-glow-purple">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-bold text-slate-100">Multi-Agent AI Debate & Consensus Engine</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Powered by Google Gemini 3.8 Flash. Multi-agent team debates Technicals, Sentiment, and Risk to reach consensus.
            </p>
          </div>

          <form onSubmit={handleSubmitAnalysis} className="flex items-center gap-2 w-full md:w-auto">
            <input
              type="text"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL, NVDA, SPY"
              className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 mono uppercase w-32"
            />
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-purple-500/20 transition-all active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Debating...' : 'Run Agent Debate'}
            </button>
          </form>
        </div>
      </div>

      {/* Consensus Banner */}
      {consensus.consensus_action && (
        <div className="glass-card p-6 bg-gradient-to-r from-slate-900 via-purple-950/20 to-slate-900 border-purple-500/30">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-slate-400">Target Asset: <strong className="text-white mono">{consensus.symbol}</strong></span>
                <span className="text-sm font-semibold text-slate-400">Current Price: <strong className="text-emerald-400 mono">${consensus.current_price?.toFixed(2)}</strong></span>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">Consensus Trade Action:</span>
                <span className={`text-sm px-3 py-1 font-bold rounded-lg ${
                  consensus.consensus_action === 'BUY'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : (consensus.consensus_action === 'SELL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-amber-500/20 text-amber-300 border border-amber-500/40')
                }`}>
                  {consensus.consensus_action}
                </span>
                
                <span className="text-xs text-slate-400">Confidence: <strong className="text-purple-300 mono">{consensus.consensus_confidence}%</strong></span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed italic bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                "{consensus.executive_summary}"
              </p>
            </div>

            {/* Target Price Controls & Quick Execute */}
            <div className="bg-slate-950 p-4 rounded-xl border border-purple-500/20 space-y-3 min-w-[240px]">
              <div className="text-xs space-y-1 mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Target Profit:</span>
                  <span className="text-emerald-400 font-bold">${consensus.target_price?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Stop Loss:</span>
                  <span className="text-rose-400 font-bold">${consensus.stop_loss?.toFixed(2)}</span>
                </div>
              </div>

              <button
                onClick={() => onExecuteAgentTrade(consensus)}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-lg shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-1.5 active:scale-95"
              >
                <Zap className="w-4 h-4 fill-white" /> Execute Agent Paper Trade
              </button>
            </div>

          </div>
        </div>
      )}

      {/* 4 Multi-Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* 1. Technical Analyst Agent */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-bold text-slate-200">Technical Analyst</h3>
            </div>
            {getStanceBadge(tech.stance)}
          </div>
          <div className="text-xs text-slate-400 space-y-2">
            <div>Confidence Level: <strong className="text-slate-200 mono">{tech.confidence || 75}%</strong></div>
            <p className="leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/80 text-slate-300">
              {tech.reasoning || "Analyzing momentum metrics, RSI oversold/overbought conditions, and Moving Average crossovers..."}
            </p>
          </div>
        </div>

        {/* 2. Sentiment Analyst Agent */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-bold text-slate-200">Sentiment Analyst</h3>
            </div>
            {getStanceBadge(sent.stance)}
          </div>
          <div className="text-xs text-slate-400 space-y-2">
            <div>Confidence Level: <strong className="text-slate-200 mono">{sent.confidence || 70}%</strong></div>
            <p className="leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/80 text-slate-300">
              {sent.reasoning || "Scanning company press releases, earnings transcript tone, and market volume dynamics..."}
            </p>
          </div>
        </div>

        {/* 3. Risk Manager Agent */}
        <div className="glass-card p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-200">Risk Manager</h3>
            </div>
            {getStanceBadge(risk.stance)}
          </div>
          <div className="text-xs text-slate-400 space-y-2">
            <div>Confidence Level: <strong className="text-slate-200 mono">{risk.confidence || 82}%</strong></div>
            <p className="leading-relaxed bg-slate-950/40 p-3 rounded-lg border border-slate-800/80 text-slate-300">
              {risk.reasoning || "Evaluating portfolio concentration risk, max drawdown threshold, and calculating optimal stop-loss levels..."}
            </p>
          </div>
        </div>

      </div>

      {/* Historical Agent Audit Trail */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-purple-400" /> Recent AI Agent Audit Trail
        </h3>
        {(!agentLogs || agentLogs.length === 0) ? (
          <div className="text-xs text-slate-500 italic p-4 text-center">
            Agent reasoning audit trail will populate as you trigger AI debate sessions.
          </div>
        ) : (
          <div className="space-y-3 max-h-72 overflow-y-auto pr-2">
            {agentLogs.map((log) => (
              <div key={log.id} className="p-3 bg-slate-900/80 rounded-xl border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white mono">{log.symbol}</span>
                    <span className="text-slate-400">({log.agent_name})</span>
                    {getStanceBadge(log.stance)}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">{new Date(log.created_at || Date.now()).toLocaleTimeString()}</span>
                </div>
                <p className="text-slate-300">{log.reasoning}</p>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
