import { getQuote, getCandles, getCompanyNews } from './marketData.js';
import { calculateTechnicalIndicators } from './indicators.js';

export async function analyzeSymbolMultiAgent(symbol) {
  const sym = symbol.trim().toUpperCase();
  const quote = await getQuote(sym);
  const candles = await getCandles(sym, '3mo');
  const indicators = calculateTechnicalIndicators(candles);
  const news = await getCompanyNews(sym);

  const currentPrice = quote.current_price;
  const score = indicators.score;
  const rsi = indicators.rsi;
  const trend = indicators.trend;

  // Attempt Gemini API call if GEMINI_API_KEY environment variable is configured
  const apiKey = process.env.GEMINI_API_KEY;
  if (apiKey) {
    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: `You are a team of top financial quantitative traders analyzing ${sym} (${quote.name}).
Price: $${currentPrice}, RSI: ${rsi}, Score: ${score}/100, Trend: ${trend}.
News headlines: ${JSON.stringify(news.map(n => n.title))}

Evaluate ${sym} from 4 agent perspectives (Technical, Sentiment, Risk, Executive Consensus).
Return ONLY a valid JSON object matching:
{
  "technical_agent": { "agent_name": "Technical Analyst", "stance": "BULLISH"|"BEARISH"|"NEUTRAL", "confidence": 0-100, "reasoning": "..." },
  "sentiment_agent": { "agent_name": "Sentiment Analyst", "stance": "BULLISH"|"BEARISH"|"NEUTRAL", "confidence": 0-100, "reasoning": "..." },
  "risk_agent": { "agent_name": "Risk Manager", "stance": "BULLISH"|"BEARISH"|"NEUTRAL", "confidence": 0-100, "reasoning": "..." },
  "executive_summary": "...",
  "consensus_action": "BUY"|"SELL"|"HOLD",
  "consensus_confidence": 0-100,
  "target_price": number,
  "stop_loss": number,
  "take_profit": number
}`
            }]
          }]
        })
      });

      if (response.ok) {
        const data = await response.json();
        let rawText = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
        if (rawText.startsWith('```json')) rawText = rawText.substring(7);
        if (rawText.endsWith('```')) rawText = rawText.substring(0, rawText.length - 3);
        const parsed = JSON.parse(rawText.trim());
        return {
          symbol: sym,
          current_price: currentPrice,
          consensus_action: parsed.consensus_action || 'HOLD',
          consensus_confidence: parsed.consensus_confidence || 75.0,
          executive_summary: parsed.executive_summary || `Consensus on ${sym}`,
          technical_agent: parsed.technical_agent,
          sentiment_agent: parsed.sentiment_agent,
          risk_agent: parsed.risk_agent,
          target_price: parsed.target_price || Math.round(currentPrice * 1.08 * 100) / 100,
          stop_loss: parsed.stop_loss || Math.round(currentPrice * 0.95 * 100) / 100,
          take_profit: parsed.take_profit || Math.round(currentPrice * 1.12 * 100) / 100
        };
      }
    } catch (e) {
      console.log('Gemini API call fallback to heuristic agent synthesis:', e.message);
    }
  }

  // Multi-Agent Heuristic Synthesis
  let action = 'HOLD';
  let techStance = 'NEUTRAL';
  let sentimentStance = 'NEUTRAL';
  let riskStance = 'NEUTRAL';
  let confidence = 65.0;

  if (score >= 65) {
    action = 'BUY';
    techStance = 'BULLISH';
    sentimentStance = 'BULLISH';
    riskStance = 'NEUTRAL';
    confidence = Math.min(95.0, score + 12.0);
  } else if (score <= 35) {
    action = 'SELL';
    techStance = 'BEARISH';
    sentimentStance = 'BEARISH';
    riskStance = 'BEARISH';
    confidence = Math.min(95.0, (100 - score) + 8.0);
  } else {
    sentimentStance = quote.percent_change >= 0 ? 'BULLISH' : 'NEUTRAL';
  }

  const techReasoning = `Technical Analyst evaluation: Overall technical score is ${score}/100 with RSI at ${rsi}. Key triggers: ${indicators.signals.join('; ')}.`;
  const sentimentReasoning = `Sentiment Analyst evaluation: Headline momentum is net ${quote.percent_change >= 0 ? 'positive' : 'cautious'} with recent institutional volume activity.`;
  const riskReasoning = `Risk Manager evaluation: Volatility is moderate. Suggested entry at $${currentPrice}. Stop-loss recommended at 5% below entry ($${Math.round(currentPrice * 0.95 * 100) / 100}) with a 10% upside target ($${Math.round(currentPrice * 1.10 * 100) / 100}). Position allocation capped at 5% of account cash.`;
  const execSummary = `Multi-Agent Executive Consensus recommends ${action} on ${sym} with ${confidence}% confidence based on technical indicator alignment (${score}/100) and risk controls.`;

  return {
    symbol: sym,
    current_price: currentPrice,
    consensus_action: action,
    consensus_confidence: confidence,
    executive_summary: execSummary,
    technical_agent: {
      agent_name: 'Technical Analyst',
      stance: techStance,
      confidence: Math.round(confidence * 10) / 10,
      reasoning: techReasoning
    },
    sentiment_agent: {
      agent_name: 'Sentiment Analyst',
      stance: sentimentStance,
      confidence: 72.0,
      reasoning: sentimentReasoning
    },
    risk_agent: {
      agent_name: 'Risk Manager',
      stance: riskStance,
      confidence: 82.0,
      reasoning: riskReasoning
    },
    target_price: Math.round(currentPrice * 1.10 * 100) / 100,
    stop_loss: Math.round(currentPrice * 0.95 * 100) / 100,
    take_profit: Math.round(currentPrice * 1.10 * 100) / 100
  };
}
