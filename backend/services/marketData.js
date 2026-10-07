const POPULAR_TICKERS = [
  { symbol: 'AAPL', name: 'Apple Inc.', asset_type: 'Stock', basePrice: 228.50 },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', asset_type: 'Stock', basePrice: 122.40 },
  { symbol: 'MSFT', name: 'Microsoft Corporation', asset_type: 'Stock', basePrice: 415.20 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', asset_type: 'Stock', basePrice: 186.30 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', asset_type: 'Stock', basePrice: 165.70 },
  { symbol: 'TSLA', name: 'Tesla, Inc.', asset_type: 'Stock', basePrice: 245.10 },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', asset_type: 'ETF', basePrice: 560.80 },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust', asset_type: 'ETF', basePrice: 485.40 },
  { symbol: 'VOO', name: 'Vanguard S&P 500 ETF', asset_type: 'ETF', basePrice: 512.90 },
  { symbol: 'IWM', name: 'iShares Russell 2000 ETF', asset_type: 'ETF', basePrice: 218.60 },
  { symbol: 'SCHD', name: 'Schwab U.S. Dividend Equity ETF', asset_type: 'ETF', basePrice: 82.30 },
  { symbol: 'AMD', name: 'Advanced Micro Devices', asset_type: 'Stock', basePrice: 154.20 }
];

export async function searchTickers(query = '') {
  const q = query.trim().toUpperCase();
  if (!q) return POPULAR_TICKERS.slice(0, 8);
  const matches = POPULAR_TICKERS.filter(
    t => t.symbol.includes(q) || t.name.toUpperCase().includes(q)
  );
  if (matches.length > 0) return matches;
  const isEtf = q.includes('ETF') || q.includes('FUND');
  return [{ symbol: q, name: `${q} Corporation`, asset_type: isEtf ? 'ETF' : 'Stock', basePrice: 150.00 }];
}

export async function getQuote(symbol) {
  const sym = symbol.trim().toUpperCase();
  const known = POPULAR_TICKERS.find(t => t.symbol === sym);
  const base = known ? known.basePrice : 150.0;
  const name = known ? known.name : `${sym} Corp`;
  const asset_type = known ? known.asset_type : 'Stock';

  // Add slight random intraday variation for realistic feel
  const randChange = (Math.random() - 0.47) * (base * 0.025);
  const current_price = Math.round((base + randChange) * 100) / 100;
  const previous_close = Math.round((base) * 100) / 100;
  const change = Math.round((current_price - previous_close) * 100) / 100;
  const percent_change = Math.round((change / previous_close * 100) * 100) / 100;

  return {
    symbol: sym,
    name,
    asset_type,
    current_price,
    previous_close,
    change,
    percent_change,
    day_high: Math.round((Math.max(current_price, previous_close) * 1.012) * 100) / 100,
    day_low: Math.round((Math.min(current_price, previous_close) * 0.988) * 100) / 100,
    volume: Math.floor(Math.random() * 8000000) + 1000000,
    timestamp: new Date().toISOString()
  };
}

export async function getCandles(symbol, period = '3mo') {
  const sym = symbol.trim().toUpperCase();
  const known = POPULAR_TICKERS.find(t => t.symbol === sym);
  const basePrice = known ? known.basePrice : 150.0;

  const candles = [];
  const days = period === '1mo' ? 30 : period === '6mo' ? 180 : 90;
  let currPrice = basePrice * 0.88; // simulate 90-day trend starting point

  const now = new Date();
  for (let i = days; i >= 0; i--) {
    const dt = new Date(now.valueOf() - i * 24 * 60 * 60 * 1000);
    const dayOfWeek = dt.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) continue; // skip weekends

    const dailyReturn = (Math.random() - 0.485) * 0.035;
    const openP = currPrice;
    const closeP = openP * (1 + dailyReturn);
    const highP = Math.max(openP, closeP) * (1 + Math.random() * 0.015);
    const lowP = Math.min(openP, closeP) * (1 - Math.random() * 0.015);
    const vol = Math.floor(Math.random() * 9000000) + 1500000;

    currPrice = closeP;
    const dateStr = dt.toISOString().split('T')[0];

    candles.push({
      time: dateStr,
      open: Math.round(openP * 100) / 100,
      high: Math.round(highP * 100) / 100,
      low: Math.round(lowP * 100) / 100,
      close: Math.round(closeP * 100) / 100,
      volume: vol
    });
  }
  return candles;
}

export async function getCompanyNews(symbol) {
  const sym = symbol.trim().toUpperCase();
  return [
    {
      title: `${sym} reports quarterly revenue beating consensus forecasts with expansion in key segments.`,
      publisher: 'Bloomberg Financial',
      link: '#',
      time: '1h ago'
    },
    {
      title: `Analyst upgrades ${sym} price target following quantitative trend breakout signals.`,
      publisher: 'MarketWatch',
      link: '#',
      time: '3h ago'
    },
    {
      title: `Institutional allocation in ${sym} surges as technical risk-to-reward ratio improves.`,
      publisher: 'Reuters Finance',
      link: '#',
      time: '5h ago'
    }
  ];
}
