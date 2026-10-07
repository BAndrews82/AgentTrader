import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PortfolioOverview from './components/PortfolioOverview';
import TradingViewChart from './components/TradingViewChart';
import WatchlistExplorer from './components/WatchlistExplorer';
import AgentCommandCenter from './components/AgentCommandCenter';
import StrategyBuilder from './components/StrategyBuilder';
import TradeHistory from './components/TradeHistory';
import TradeModal from './components/TradeModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // App Data State
  const [portfolio, setPortfolio] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [orders, setOrders] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  
  // Selected Chart & AI Agent State
  const [selectedSymbol, setSelectedSymbol] = useState('SPY');
  const [quote, setQuote] = useState(null);
  const [candles, setCandles] = useState([]);
  const [indicators, setIndicators] = useState(null);
  const [agentAnalysis, setAgentAnalysis] = useState(null);
  const [agentLoading, setAgentLoading] = useState(false);
  
  // Modal & Simulation State
  const [tradeModalSymbol, setTradeModalSymbol] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [evaluations, setEvaluations] = useState([]);

  // Fetch Core Portfolio & Watchlist Data
  const fetchData = async () => {
    try {
      const [portRes, snapRes, watchRes, strgRes, ordRes, logsRes] = await Promise.all([
        fetch('/api/portfolio'),
        fetch('/api/portfolio/snapshots'),
        fetch('/api/watchlist'),
        fetch('/api/strategies'),
        fetch('/api/orders'),
        fetch('/api/agents/logs')
      ]);

      if (portRes.ok) setPortfolio(await portRes.json());
      if (snapRes.ok) setSnapshots(await snapRes.json());
      if (watchRes.ok) setWatchlist(await watchRes.json());
      if (strgRes.ok) setStrategies(await strgRes.json());
      if (ordRes.ok) setOrders(await ordRes.json());
      if (logsRes.ok) setAgentLogs(await logsRes.json());
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  };

  // Fetch Specific Symbol Market Data
  const fetchSymbolData = async (symbol) => {
    try {
      const [qRes, cRes, iRes] = await Promise.all([
        fetch(`/api/market/quote/${symbol}`),
        fetch(`/api/market/candles/${symbol}`),
        fetch(`/api/market/indicators/${symbol}`)
      ]);
      if (qRes.ok) setQuote(await qRes.json());
      if (cRes.ok) setCandles(await cRes.json());
      if (iRes.ok) setIndicators(await iRes.json());
    } catch (err) {
      console.error('Error fetching symbol data:', err);
    }
  };

  // Run Multi-Agent Debate
  const handleRunAgentAnalysis = async (symbol) => {
    try {
      setAgentLoading(true);
      setSelectedSymbol(symbol);
      const res = await fetch(`/api/agents/analyze/${symbol}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setAgentAnalysis(data);
      }
      await fetchData();
    } catch (err) {
      console.error('Error running agent debate:', err);
    } finally {
      setAgentLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchSymbolData(selectedSymbol);
  }, []);

  useEffect(() => {
    fetchSymbolData(selectedSymbol);
  }, [selectedSymbol]);

  // Actions
  const handleResetAccount = async () => {
    if (window.confirm('Are you sure you want to reset your paper account to $100,000 cash?')) {
      await fetch('/api/portfolio/reset', { method: 'POST' });
      await fetchData();
    }
  };

  const handleRunSimulationTick = async () => {
    try {
      setSimLoading(true);
      const res = await fetch('/api/simulation/tick', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setEvaluations(data.evaluations || []);
      }
      await fetchData();
    } catch (err) {
      console.error('Simulation tick error:', err);
    } finally {
      setSimLoading(false);
    }
  };

  const handleAddWatchlist = async (symbol) => {
    await fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol })
    });
    await fetchData();
  };

  const handleRemoveWatchlist = async (symbol) => {
    await fetch(`/api/watchlist/${symbol}`, { method: 'DELETE' });
    await fetchData();
  };

  const handleCreateStrategy = async (strategyData) => {
    await fetch('/api/strategies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(strategyData)
    });
    await fetchData();
  };

  const handleToggleStrategy = async (id) => {
    await fetch(`/api/strategies/${id}/toggle`, { method: 'PUT' });
    await fetchData();
  };

  const handleDeleteStrategy = async (id) => {
    await fetch(`/api/strategies/${id}`, { method: 'DELETE' });
    await fetchData();
  };

  const handleSubmitOrder = async (orderData) => {
    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Order error: ${err.error || 'Failed to place order'}`);
    } else {
      await fetchData();
    }
  };

  const handleExecuteAgentTrade = async (consensus) => {
    if (!consensus || !consensus.symbol) return;
    const side = consensus.consensus_action === 'SELL' ? 'SELL' : 'BUY';
    const shares = 10;
    await handleSubmitOrder({
      symbol: consensus.symbol,
      side,
      shares,
      price: consensus.current_price,
      order_type: 'MARKET',
      triggered_by: 'AGENT',
      reasoning: `Executed Multi-Agent Consensus ${side} order: ${consensus.executive_summary}`
    });
    setActiveTab('dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        portfolio={portfolio}
        onResetAccount={handleResetAccount}
        onRunSimulationTick={handleRunSimulationTick}
        simLoading={simLoading}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        
        {activeTab === 'dashboard' && (
          <PortfolioOverview
            portfolio={portfolio}
            snapshots={snapshots}
            onQuickSell={(pos) => {
              setTradeModalSymbol(pos.symbol);
            }}
            onSelectSymbolForAnalysis={(sym) => {
              setSelectedSymbol(sym);
              handleRunAgentAnalysis(sym);
              setActiveTab('agents');
            }}
          />
        )}

        {activeTab === 'watchlist' && (
          <div className="space-y-6">
            <WatchlistExplorer
              watchlist={watchlist}
              onAddSymbol={handleAddWatchlist}
              onRemoveSymbol={handleRemoveWatchlist}
              onSelectSymbolForAnalysis={(sym) => {
                setSelectedSymbol(sym);
                handleRunAgentAnalysis(sym);
                setActiveTab('agents');
              }}
              onOpenTradeModal={(sym) => setTradeModalSymbol(sym)}
            />

            <TradingViewChart
              symbol={selectedSymbol}
              quote={quote}
              candles={candles}
              indicators={indicators}
            />
          </div>
        )}

        {activeTab === 'agents' && (
          <AgentCommandCenter
            selectedSymbol={selectedSymbol}
            agentAnalysis={agentAnalysis}
            loading={agentLoading}
            onRunAnalysis={handleRunAgentAnalysis}
            onExecuteAgentTrade={handleExecuteAgentTrade}
            agentLogs={agentLogs}
          />
        )}

        {activeTab === 'strategies' && (
          <StrategyBuilder
            strategies={strategies}
            onCreateStrategy={handleCreateStrategy}
            onToggleStrategy={handleToggleStrategy}
            onDeleteStrategy={handleDeleteStrategy}
            onRunSimulationTick={handleRunSimulationTick}
            evaluations={evaluations}
          />
        )}

        {activeTab === 'history' && (
          <TradeHistory orders={orders} />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500 font-mono">
        AgentTrader AI Paper Trading Suite &bull; Simulated Execution Engine &bull; Powered by Google Gemini 3.8 Flash & SQLite
      </footer>

      {/* Trade Modal */}
      {tradeModalSymbol && (
        <TradeModal
          symbol={tradeModalSymbol}
          quote={quote && quote.symbol === tradeModalSymbol ? quote : { current_price: 150.0 }}
          portfolio={portfolio}
          onClose={() => setTradeModalSymbol(null)}
          onSubmitOrder={handleSubmitOrder}
        />
      )}

    </div>
  );
}
