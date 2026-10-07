import React from 'react';
import { History, ArrowUpRight, ArrowDownRight, Bot, Sliders, User } from 'lucide-react';

export default function TradeHistory({ orders }) {
  const getTriggerBadge = (trigger) => {
    if (trigger === 'AGENT') return <span className="badge badge-purple"><Bot className="w-3 h-3" /> AGENT</span>;
    if (trigger === 'RULE') return <span className="badge badge-blue"><Sliders className="w-3 h-3" /> ALGO RULE</span>;
    return <span className="badge badge-neutral"><User className="w-3 h-3" /> MANUAL</span>;
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <History className="w-5 h-5 text-blue-400" /> Completed Paper Order Log
          </h2>
          <p className="text-xs text-slate-400">Full audit log of executed simulated paper trades</p>
        </div>
        <span className="badge badge-blue mono">{orders?.length || 0} Orders Executed</span>
      </div>

      {(!orders || orders.length === 0) ? (
        <div className="p-8 text-center text-slate-500 text-xs italic">
          No paper trades executed yet. Run a strategy tick or place manual orders from the Watchlist tab.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Shares</th>
                <th>Execution Price</th>
                <th>Total Value</th>
                <th>Triggered By</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((ord) => {
                const isBuy = ord.side === 'BUY';
                return (
                  <tr key={ord.id}>
                    <td className="text-xs text-slate-400 mono">
                      {new Date(ord.created_at || Date.now()).toLocaleString()}
                    </td>
                    <td className="font-bold text-slate-100 mono">{ord.symbol}</td>
                    <td>
                      <span className={`badge ${isBuy ? 'badge-gain' : 'badge-loss'} mono`}>
                        {isBuy ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                        {ord.side}
                      </span>
                    </td>
                    <td className="mono">{ord.shares}</td>
                    <td className="mono">${ord.price?.toFixed(2)}</td>
                    <td className="mono font-semibold">${ord.total_value?.toFixed(2)}</td>
                    <td>{getTriggerBadge(ord.triggered_by)}</td>
                    <td className="text-xs text-slate-300 max-w-xs truncate">{ord.reasoning || 'Standard order'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
