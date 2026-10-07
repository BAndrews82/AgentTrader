import React, { useState } from 'react';
import { ShoppingBag, ArrowUpRight, ArrowDownRight, DollarSign } from 'lucide-react';

export default function TradeModal({ symbol, quote, portfolio, onClose, onSubmitOrder }) {
  const [side, setSide] = useState('BUY');
  const [shares, setShares] = useState(10);
  const [errorMsg, setErrorMsg] = useState('');

  const price = quote?.current_price || 150.0;
  const totalCost = shares * price;
  const availableCash = portfolio?.cash_balance || 100000;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (shares <= 0) {
      setErrorMsg('Shares must be greater than 0');
      return;
    }
    if (side === 'BUY' && totalCost > availableCash) {
      setErrorMsg(`Insufficient cash (${availableCash.toFixed(2)} available)`);
      return;
    }
    setErrorMsg('');
    onSubmitOrder({
      symbol,
      side,
      shares: parseFloat(shares),
      price,
      order_type: 'MARKET',
      triggered_by: 'MANUAL',
      reasoning: `Manual user paper order to ${side} ${shares} shares of ${symbol}`
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="glass-card p-6 max-w-md w-full space-y-5 border-blue-500/30">
        
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-blue-400" />
            <h3 className="text-base font-bold text-slate-100">Execute Paper Order - <span className="mono text-blue-400">{symbol}</span></h3>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200 text-xl font-bold">&times;</button>
        </div>

        {/* Quote Banner */}
        <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 flex items-center justify-between font-mono text-xs">
          <div>
            <span className="text-slate-500">Market Price:</span>
            <div className="text-base font-bold text-slate-100">${price.toFixed(2)}</div>
          </div>
          <div>
            <span className="text-slate-500">Available Cash:</span>
            <div className="text-sm font-semibold text-emerald-400">${availableCash.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
          </div>
        </div>

        {/* Side Toggle: BUY / SELL */}
        <div className="grid grid-cols-2 gap-2 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setSide('BUY')}
            className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1 ${
              side === 'BUY'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ArrowUpRight className="w-4 h-4" /> BUY
          </button>
          <button
            type="button"
            onClick={() => setSide('SELL')}
            className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1 ${
              side === 'SELL'
                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ArrowDownRight className="w-4 h-4" /> SELL
          </button>
        </div>

        {errorMsg && (
          <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-400">
            {errorMsg}
          </div>
        )}

        {/* Quantity Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-400 mb-1">Number of Shares</label>
            <input
              type="number"
              step="any"
              min="0.0001"
              required
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 mono text-base font-bold focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1 mono">
            <div className="flex justify-between text-slate-400">
              <span>Total Estimated Value:</span>
              <span className="text-white font-bold text-sm">${totalCost.toFixed(2)}</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`px-5 py-2 rounded-xl font-bold text-white shadow-lg transition-all ${
                side === 'BUY' ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-500/20' : 'bg-rose-600 hover:bg-rose-500 shadow-rose-500/20'
              }`}
            >
              Submit {side} Order
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
