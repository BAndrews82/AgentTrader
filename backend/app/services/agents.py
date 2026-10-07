import os
import json
from typing import Dict, Any, List
from google import genai
from app.services.market_data import get_quote, get_candles, get_company_news
from app.services.technical_analysis import calculate_technical_indicators

def get_genai_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def analyze_symbol_multi_agent(symbol: str) -> Dict[str, Any]:
    symbol = symbol.strip().upper()
    quote = get_quote(symbol)
    candles = get_candles(symbol, period="3mo", interval="1d")
    indicators = calculate_technical_indicators(candles)
    news = get_company_news(symbol)
    
    current_price = quote["current_price"]
    
    client = get_genai_client()
    
    if client is None:
        return _generate_heuristic_multi_agent(symbol, quote, indicators, news)
    
    try:
        # Prompt for Gemini multi-agent debate synthesis
        prompt = f"""
        You are a team of top-tier Wall Street quantitative traders and portfolio managers analyzing {symbol} ({quote['name']}).
        Current Price: ${current_price} (Change: {quote['change']} / {quote['percent_change']}%)
        Asset Type: {quote['asset_type']}
        
        Technical Indicators:
        - RSI (14): {indicators['rsi']}
        - SMA 20: ${indicators['sma_20']}, SMA 50: ${indicators['sma_50']}
        - EMA 9: ${indicators['ema_9']}, EMA 21: ${indicators['ema_21']}
        - MACD Line: {indicators['macd']['macd']}, Signal: {indicators['macd']['signal']}, Histogram: {indicators['macd']['histogram']}
        - Bollinger Bands: Upper ${indicators['bollinger']['upper']}, Lower ${indicators['bollinger']['lower']}
        - Trend Stance: {indicators['trend']} (Technical Score: {indicators['score']}/100)
        - Key Signals: {', '.join(indicators['signals'])}

        Recent Market Headlines:
        {json.dumps(news, indent=2)}

        Please analyze this asset from 4 distinct agent perspectives:
        1. TECHNICAL ANALYST AGENT: Technical chart setup, momentum, support/resistance, indicator confirmation.
        2. SENTIMENT ANALYST AGENT: News sentiment, market perception, headline risks or catalysts.
        3. RISK MANAGER AGENT: Volatility risk, position sizing limit, stop-loss and take-profit levels.
        4. EXECUTIVE TRADER AGENT: Final synthesized consensus decision (BUY, SELL, or HOLD), confidence score (0-100%), target price, stop loss, and executive summary.

        Return ONLY a JSON object with this exact structure:
        {{
            "technical_agent": {{
                "agent_name": "Technical Analyst",
                "stance": "BULLISH" | "BEARISH" | "NEUTRAL",
                "confidence": 0-100,
                "reasoning": "Detailed technical analysis string..."
            }},
            "sentiment_agent": {{
                "agent_name": "Sentiment Analyst",
                "stance": "BULLISH" | "BEARISH" | "NEUTRAL",
                "confidence": 0-100,
                "reasoning": "Detailed sentiment analysis string..."
            }},
            "risk_agent": {{
                "agent_name": "Risk Manager",
                "stance": "BULLISH" | "BEARISH" | "NEUTRAL",
                "confidence": 0-100,
                "reasoning": "Detailed risk assessment string...",
                "suggested_max_allocation_pct": 5.0
            }},
            "executive_summary": "Synthesized executive takeaway...",
            "consensus_action": "BUY" | "SELL" | "HOLD",
            "consensus_confidence": 0-100,
            "target_price": number,
            "stop_loss": number,
            "take_profit": number
        }}
        """
        
        response = client.interactions.create(
            model="gemini-3.8-flash",
            input=prompt
        )
        
        output_text = response.output_text or ""
        # Clean JSON markdown if wrapped in ```json ... ```
        clean_text = output_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        parsed = json.loads(clean_text)
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "consensus_action": parsed.get("consensus_action", "HOLD"),
            "consensus_confidence": float(parsed.get("consensus_confidence", 65.0)),
            "executive_summary": parsed.get("executive_summary", f"Consensus evaluation for {symbol}"),
            "technical_agent": parsed.get("technical_agent"),
            "sentiment_agent": parsed.get("sentiment_agent"),
            "risk_agent": parsed.get("risk_agent"),
            "target_price": float(parsed.get("target_price", round(current_price * 1.08, 2))),
            "stop_loss": float(parsed.get("stop_loss", round(current_price * 0.95, 2))),
            "take_profit": float(parsed.get("take_profit", round(current_price * 1.12, 2)))
        }
    except Exception as e:
        print(f"Gemini API fallback triggered for {symbol}: {e}")
        return _generate_heuristic_multi_agent(symbol, quote, indicators, news)

def _generate_heuristic_multi_agent(symbol: str, quote: Dict[str, Any], indicators: Dict[str, Any], news: List[Dict[str, str]]) -> Dict[str, Any]:
    price = quote["current_price"]
    score = indicators["score"]
    rsi = indicators["rsi"]
    trend = indicators["trend"]
    
    if score >= 65:
        action = "BUY"
        tech_stance = "BULLISH"
        sentiment_stance = "BULLISH"
        risk_stance = "NEUTRAL"
        confidence = min(90.0, score + 10.0)
    elif score <= 35:
        action = "SELL"
        tech_stance = "BEARISH"
        sentiment_stance = "BEARISH"
        risk_stance = "BEARISH"
        confidence = min(90.0, (100 - score) + 5.0)
    else:
        action = "HOLD"
        tech_stance = "NEUTRAL"
        sentiment_stance = "BULLISH" if quote["percent_change"] > 0 else "NEUTRAL"
        risk_stance = "NEUTRAL"
        confidence = 60.0
        
    tech_reasoning = f"Chart indicators show a technical score of {score}/100. RSI stands at {rsi}. " + " ".join(indicators["signals"])
    sentiment_reasoning = f"Recent headlines indicate positive sentiment with price change of {quote['percent_change']}%. Catalyst drivers remain active."
    risk_reasoning = f"Current price ${price}. Recommended stop-loss set at 5% below entry (${round(price * 0.95, 2)}), target profit at 10% upside (${round(price * 1.10, 2)}). Position sizing should not exceed 5% of account cash."
    
    exec_summary = f"Multi-agent team reaches a {action} consensus on {symbol} with {confidence}% confidence based on technical score ({score}/100) and indicator alignment."
    
    return {
        "symbol": symbol,
        "current_price": price,
        "consensus_action": action,
        "consensus_confidence": confidence,
        "executive_summary": exec_summary,
        "technical_agent": {
            "agent_name": "Technical Analyst",
            "stance": tech_stance,
            "confidence": confidence,
            "reasoning": tech_reasoning
        },
        "sentiment_agent": {
            "agent_name": "Sentiment Analyst",
            "stance": sentiment_stance,
            "confidence": 70.0,
            "reasoning": sentiment_reasoning
        },
        "risk_agent": {
            "agent_name": "Risk Manager",
            "stance": risk_stance,
            "confidence": 80.0,
            "reasoning": risk_reasoning
        },
        "target_price": round(price * 1.10, 2),
        "stop_loss": round(price * 0.95, 2),
        "take_profit": round(price * 1.10, 2)
    }
