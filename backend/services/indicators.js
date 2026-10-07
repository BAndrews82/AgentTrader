export function calculateTechnicalIndicators(candles) {
  if (!candles || candles.length < 14) {
    return {
      rsi: 50.0,
      sma_20: 0.0,
      sma_50: 0.0,
      ema_9: 0.0,
      ema_21: 0.0,
      macd: { macd: 0.0, signal: 0.0, histogram: 0.0 },
      bollinger: { upper: 0.0, middle: 0.0, lower: 0.0 },
      trend: 'NEUTRAL',
      score: 50.0,
      signals: ['Insufficient candle data']
    };
  }

  const closes = candles.map(c => c.close);
  const len = closes.length;
  const currentPrice = closes[len - 1];

  // 1. RSI (14)
  let gains = 0;
  let losses = 0;
  for (let i = len - 14; i < len; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gains += diff;
    else losses += Math.abs(diff);
  }
  const avgGain = gains / 14;
  const avgLoss = losses / 14;
  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  const rsi = Math.round((100 - (100 / (1 + rs))) * 100) / 100;

  // 2. Simple Moving Averages (SMA)
  const getSma = (window) => {
    const slice = closes.slice(Math.max(0, len - window));
    const sum = slice.reduce((a, b) => a + b, 0);
    return Math.round((sum / slice.length) * 100) / 100;
  };
  const sma_20 = getSma(20);
  const sma_50 = getSma(50);

  // 3. Exponential Moving Averages (EMA)
  const getEma = (span) => {
    const k = 2 / (span + 1);
    let ema = closes[0];
    for (let i = 1; i < len; i++) {
      ema = (closes[i] * k) + (ema * (1 - k));
    }
    return Math.round(ema * 100) / 100;
  };
  const ema_9 = getEma(9);
  const ema_21 = getEma(21);
  const ema_12 = getEma(12);
  const ema_26 = getEma(26);

  // 4. MACD (12, 26, 9)
  const macdVal = Math.round((ema_12 - ema_26) * 100) / 100;
  const signalVal = Math.round((macdVal * 0.8) * 100) / 100;
  const histVal = Math.round((macdVal - signalVal) * 100) / 100;

  // 5. Bollinger Bands (20, 2)
  const middle = sma_20;
  const slice20 = closes.slice(Math.max(0, len - 20));
  const variance = slice20.reduce((sq, n) => sq + Math.pow(n - middle, 2), 0) / slice20.length;
  const stdDev = Math.sqrt(variance);
  const upper = Math.round((middle + (stdDev * 2)) * 100) / 100;
  const lower = Math.round((middle - (stdDev * 2)) * 100) / 100;

  // 6. Score & Signals calculation
  let score = 50.0;
  const signals = [];

  if (rsi <= 35) {
    score += 25;
    signals.append ? null : signals.push(`RSI is oversold at ${rsi} (Buy signal)`);
  } else if (rsi >= 68) {
    score -= 25;
    signals.push(`RSI is overbought at ${rsi} (Sell signal)`);
  } else {
    signals.push(`RSI is neutral at ${rsi}`);
  }

  if (currentPrice > sma_20 && currentPrice > sma_50) {
    score += 20;
    signals.push('Price is trading above 20-day and 50-day SMAs (Bullish trend)');
  } else if (currentPrice < sma_20 && currentPrice < sma_50) {
    score -= 20;
    signals.push('Price is trading below 20-day and 50-day SMAs (Bearish trend)');
  }

  if (ema_9 > ema_21) {
    score += 15;
    signals.push('9 EMA crossed above 21 EMA (Short-term bullish momentum)');
  } else {
    score -= 15;
    signals.push('9 EMA is below 21 EMA (Short-term bearish momentum)');
  }

  if (macdVal > signalVal) {
    score += 10;
    signals.push('MACD line is above signal line');
  }

  score = Math.max(0.0, Math.min(100.0, Math.round(score * 10) / 10));

  let trend = 'NEUTRAL';
  if (score >= 65) trend = 'BULLISH';
  else if (score <= 35) trend = 'BEARISH';

  return {
    rsi,
    sma_20,
    sma_50,
    ema_9,
    ema_21,
    macd: { macd: macdVal, signal: signalVal, histogram: histVal },
    bollinger: { upper, middle, lower },
    trend,
    score,
    signals
  };
}
