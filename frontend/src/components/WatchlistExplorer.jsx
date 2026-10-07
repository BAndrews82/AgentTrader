import React, { useState } from 'react';
import { Search, Plus, Trash2, Bot, ArrowUpRight, ArrowDownRight, Layers, ShoppingBag } from 'lucide-react';

export default function WatchlistExplorer({
  watchlist,
  onAddSymbol,
  onRemoveSymbol,
  onSelectSymbolForAnalysis,
  onOpenTradeModal
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      setIsSearching(true);
      const res = await fetch(`/api/market/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddTicker = (symbol) => {
    onAddSymbol(symbol);
    setSearchQuery('');
    setSearchResults([]);
  };

  return (
    <div className="space-y-6">
      
      {/* Search Header Bar */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Market Explorer & Watchlist</h2>
            <p className="text-xs text-slate-400">Search and pick Stocks or ETFs for paper trading and multi-agent AI analysis</p>
          </div>
          
          {/* Ticker Search Bar */}
          <div className="relative w-full md:w-80">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search Ticker e.g. AAPL, NVDA, SPY..."
                value={searchQuery}
                onChange={handleSearch}
                className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors mono"
              />
            </div>

            {/* Dropdown Results */}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto divide-y divide-slate-800/60">
                {searchResults.map((item) => (
                  <div
                    key={item.symbol}
                    onClick={() => handleAddTicker(item.symbol)}
                    className="p-3 hover:bg-slate-800/80 cursor-pointer flex items-center justify-between transition-colors"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-200 mono">{item.symbol}</div>
                      <div className="text-[11px] text-slate-400">{item.name}</div>
                    </div>
                    <span className={`badge ${item.asset_type === 'ETF' ? 'badge-purple' : 'badge-blue'}`}>
                      + Add {item.asset_type}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Watchlist Asset Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {watchlist.map((item) => {
          const q = item.quote || {};
          const isGain = (q.change || 0) >= 0;
          return (
            <div key={item.symbol} className="glass-card p-5 space-y-4 relative group">
              
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold mono text-white">{item.symbol}</h3>
                    <span className={`badge ${item.asset_type === 'ETF' ? 'badge-purple' : 'badge-blue'}`}>
                      {item.asset_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 truncate max-w-[180px]">{item.name}</p>
                </div>
                
                <button
                  onClick={() => onRemoveSymbol(item.symbol)}
                  className="text-slate-600 hover:text-rose-400 p-1 rounded transition-colors opacity-0 group-hover:opacity-100"
                  title="Remove from watchlist"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Price Banner */}
              <div className="flex items-baseline justify-between border-t border-b border-slate-800/60 py-3">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Current Quote</div>
                  <div className="text-xl font-bold mono text-slate-100">${q.current_price?.toFixed(2) || '150.00'}</div>
                </div>

                <span className={`badge ${isGain ? 'badge-gain' : 'badge-loss'} mono`}>
                  {isGain ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {isGain ? '+' : ''}${q.change?.toFixed(2)} ({isGain ? '+' : ''}{q.percent_change?.toFixed(2)}%)
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => onSelectSymbolForAnalysis(item.symbol)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-semibold transition-all shadow-sm"
                >
                  <Bot className="w-3.5 h-3.5 text-purple-400" /> AI Agent Debate
                </button>

                <button
                  onClick={() => onOpenTradeModal(item.symbol)}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-lg text-xs font-semibold transition-all"
                >
                  <ShoppingBag className="w-3.5 h-3.5 text-blue-400" /> Trade
                </button>
              </div>

            </div>
          );
        })}
      </div>

    </div>
  );
}
