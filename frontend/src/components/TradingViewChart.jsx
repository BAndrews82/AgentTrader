import React, { useState, useMemo } from 'react';
import { Eye, Layers, TrendingUp, Sliders, Info } from 'lucide-react';

export default function TradingViewChart({ symbol, quote, candles, indicators }) {
  const [showSma, setShowSma] = useState(true);
  const [showRsi, setShowRsi] = useState(true);
  const [hoverBar, setHoverBar] = useState(null);

  const candleList = candles || [];

  const chartData = useMemo(() => {
    if (!candleList.length) return { maxP: 200, minP: 100, bars: [] };
    const maxP = Math.max(...candleList.map(c => c.high)) * 1.01;
    const minP = Math.min(...candleList.map(c => c.low)) * 0.99;
    return { maxP, minP, bars: candleList };
  }, [candleList]);

  const width = 800;
  const height = 320;
  const rsiHeight = 80;

  const activeBar = hoverBar || (chartData.bars.length ? chartData.bars[chartData.bars.length - 1] : null);

  return (
    <div className="glass-card p-6 space-y-4">
      
      {/* Chart Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold mono text-white">{symbol}</h2>
            <span className="badge badge-blue">{quote?.asset_type || 'Stock'}</span>
            <span className="text-xs text-slate-400">{quote?.name}</span>
          </div>
          {quote && (
            <div className="flex items-center gap-3 mt-1 text-sm font-mono">
              <span className="text-xl font-bold text-slate-100">${quote.current_price.toFixed(2)}</span>
              <span className={`badge ${quote.change >= 0 ? 'badge-gain' : 'badge-loss'}`}>
                {quote.change >= 0 ? '+' : ''}${quote.change.toFixed(2)} ({quote.change >= 0 ? '+' : ''}{quote.percent_change.toFixed(2)}%)
              </span>
              <span className="text-xs text-slate-500">Vol: {(quote.volume / 1000000).toFixed(2)}M</span>
            </div>
          )}
        </div>

        {/* Overlay Control Toggles */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSma(!showSma)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              showSma
                ? 'bg-blue-600/20 text-blue-400 border-blue-500/40'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
          >
            SMAs (20/50)
          </button>
          <button
            onClick={() => setShowRsi(!showRsi)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              showRsi
                ? 'bg-purple-600/20 text-purple-400 border-purple-500/40'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
          >
            RSI (14)
          </button>
        </div>
      </div>

      {/* Hover Bar Details */}
      {activeBar && (
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-slate-300">
          <span className="text-slate-500">Date: <strong className="text-slate-200">{activeBar.time}</strong></span>
          <span>O: <strong className="text-slate-200">${activeBar.open.toFixed(2)}</strong></span>
          <span>H: <strong className="text-emerald-400">${activeBar.high.toFixed(2)}</strong></span>
          <span>L: <strong className="text-rose-400">${activeBar.low.toFixed(2)}</strong></span>
          <span>C: <strong className="text-slate-200">${activeBar.close.toFixed(2)}</strong></span>
          <span>Vol: <strong className="text-slate-400">{(activeBar.volume / 1000).toFixed(0)}k</strong></span>
        </div>
      )}

      {/* Interactive Candlestick Chart SVG */}
      <div className="relative w-full overflow-x-auto bg-slate-950/60 rounded-xl border border-slate-800/80 p-2">
        <svg
          viewBox={`0 0 ${width} ${height + (showRsi ? rsiHeight + 20 : 0)}`}
          className="w-full h-auto select-none"
        >
          {/* Horizontal Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = height * pct;
            const priceVal = chartData.maxP - (pct * (chartData.maxP - chartData.minP));
            return (
              <g key={i}>
                <line x1="0" y1={y} x2={width} y2={y} stroke="#1e293b" strokeWidth="1" strokeDasharray="3,3" />
                <text x={width - 45} y={y - 4} fill="#64748b" fontSize="9" fontFamily="monospace">
                  ${priceVal.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* Render Candlesticks */}
          {chartData.bars.map((bar, idx) => {
            const numBars = chartData.bars.length;
            const barWidth = Math.max(3, (width - 60) / numBars - 2);
            const x = 10 + idx * ((width - 60) / numBars);

            const isGreen = bar.close >= bar.open;
            const candleColor = isGreen ? '#10b981' : '#f43f5e';

            const yHigh = height - ((bar.high - chartData.minP) / (chartData.maxP - chartData.minP || 1)) * height;
            const yLow = height - ((bar.low - chartData.minP) / (chartData.maxP - chartData.minP || 1)) * height;
            const yOpen = height - ((bar.open - chartData.minP) / (chartData.maxP - chartData.minP || 1)) * height;
            const yClose = height - ((bar.close - chartData.minP) / (chartData.maxP - chartData.minP || 1)) * height;

            const candleTop = Math.min(yOpen, yClose);
            const candleHeight = Math.max(2, Math.abs(yClose - yOpen));

            return (
              <g
                key={idx}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                onMouseEnter={() => setHoverBar(bar)}
              >
                {/* High-Low Wick */}
                <line x1={x + barWidth / 2} y1={yHigh} x2={x + barWidth / 2} y2={yLow} stroke={candleColor} strokeWidth="1.5" />
                {/* Body */}
                <rect
                  x={x}
                  y={candleTop}
                  width={barWidth}
                  height={candleHeight}
                  fill={candleColor}
                  rx="1"
                />
              </g>
            );
          })}

          {/* RSI Subplot */}
          {showRsi && (
            <g transform={`translate(0, ${height + 20})`}>
              <rect x="0" y="0" width={width} height={rsiHeight} fill="#0b0f19" rx="6" />
              {/* Overbought 70 / Oversold 30 Lines */}
              <line x1="0" y1="24" x2={width} y2="24" stroke="#f43f5e" strokeWidth="1" strokeDasharray="4,4" />
              <text x={width - 50} y="20" fill="#f43f5e" fontSize="9">70 OB</text>
              <line x1="0" y1="56" x2={width} y2="56" stroke="#10b981" strokeWidth="1" strokeDasharray="4,4" />
              <text x={width - 50} y="68" fill="#10b981" fontSize="9">30 OS</text>
              <text x="10" y="16" fill="#a855f7" fontSize="10" fontWeight="bold">RSI (14): {indicators?.rsi || 50}</text>
            </g>
          )}
        </svg>
      </div>

      {/* Technical Signals Banner */}
      {indicators && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
          <div>
            <div className="font-semibold text-slate-200 mb-1 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              Technical Indicator Breakdown & Signals
            </div>
            <ul className="space-y-1 text-slate-400 list-disc list-inside">
              {indicators.signals?.map((sig, i) => (
                <li key={i}>{sig}</li>
              ))}
            </ul>
          </div>
          <div className="flex items-center gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
            <div>
              <div className="text-[10px] text-slate-400 uppercase">Technical Score</div>
              <div className="text-xl font-bold mono text-purple-400">{indicators.score}/100</div>
            </div>
            <span className={`badge ${indicators.trend === 'BULLISH' ? 'badge-gain' : (indicators.trend === 'BEARISH' ? 'badge-loss' : 'badge-neutral')}`}>
              {indicators.trend}
            </span>
          </div>
        </div>
      )}

    </div>
  );
}
