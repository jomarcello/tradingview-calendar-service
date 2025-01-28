import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_SERVICE_URL = os.getenv("TELEGRAM_SERVICE_URL")
AI_PROCESSOR_URL = os.getenv("AI_PROCESSOR_URL", "https://tradingview-signal-ai-service-production.up.railway.app")
CHART_SERVICE_URL = os.getenv("CHART_SERVICE_URL", "https://tradingview-chart-service-production.up.railway.app")

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

class EconomicEvent(BaseModel):
    time: str
    currency: str
    impact: str
    event: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None

async def fetch_economic_calendar():
    """Fetch economic calendar data (currently using mock data)."""
    try:
        # Mock data for today
        mock_events = [
            {
                "time": "10:00",
                "currency": "EUR",
                "impact": "high",
                "event": "German GDP Q4",
                "actual": "",
                "forecast": "0.2%",
                "previous": "0.1%"
            },
            {
                "time": "14:30",
                "currency": "USD",
                "impact": "medium",
                "event": "Core Durable Goods Orders",
                "actual": "",
                "forecast": "0.5%",
                "previous": "0.3%"
            },
            {
                "time": "16:00",
                "currency": "USD",
                "impact": "high",
                "event": "CB Consumer Confidence",
                "actual": "",
                "forecast": "115.2",
                "previous": "110.7"
            }
        ]
        
        events = []
        for event_data in mock_events:
            event = EconomicEvent(
                time=event_data["time"],
                currency=event_data["currency"],
                impact=event_data["impact"],
                event=event_data["event"],
                actual=event_data["actual"],
                forecast=event_data["forecast"],
                previous=event_data["previous"]
            )
            events.append(event)
        
        # Sort events by time
        events.sort(key=lambda x: x.time)
        return events
            
    except Exception as e:
        logger.error(f"Error fetching calendar: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching calendar data: {str(e)}")

def format_telegram_message(events: List[EconomicEvent]) -> str:
    """Format economic events into a Telegram message."""
    if not events:
        return "No economic events scheduled."
        
    message = "🎯 Economic Calendar Update 🎯\n\n"
    
    for event in events:
        # Convert impact to emoji
        impact_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '⚪'
        }.get(event.impact, '⚪')
        
        message += f"Time: {event.time}\n"
        message += f"Currency: {event.currency}\n"
        message += f"Impact: {impact_emoji}\n"
        message += f"Event: {event.event}\n"
        
        if event.actual or event.forecast or event.previous:
            if event.forecast:
                message += f"Forecast: {event.forecast}\n"
            if event.previous:
                message += f"Previous: {event.previous}\n"
            if event.actual:
                message += f"Actual: {event.actual}\n"
            
        message += "\n-------------------\n\n"
    
    message += "Risk Management:\n"
    message += "• Consider event impact on open positions\n"
    message += "• Adjust position sizes during high impact events\n"
    message += "• Be aware of potential market volatility\n\n"
    
    message += "🤖 SigmaPips AI Analysis:\n"
    message += "Major economic events can cause significant market movements. "
    message += "Plan your trades accordingly and maintain proper risk management."
    
    return message

@app.get("/calendar")
async def get_calendar():
    """Get formatted economic calendar data and send through the system."""
    try:
        events = await fetch_economic_calendar()
        message = format_telegram_message(events)
        
        # Create signal format matching the system
        signal = {
            "type": "economic_calendar",
            "content": {
                "message": message,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📊 Technical Analysis",
                                "callback_data": "technical_analysis"
                            },
                            {
                                "text": "📰 Market Sentiment",
                                "callback_data": "market_sentiment"
                            }
                        ],
                        [
                            {
                                "text": "📅 Economic Calendar",
                                "callback_data": "economic_calendar"
                            }
                        ]
                    ]
                }
            }
        }
        
        # Send to telegram service
        if TELEGRAM_SERVICE_URL:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{TELEGRAM_SERVICE_URL}/send_signal",
                    json=signal
                )
        
        return {"status": "success", "data": signal}
        
    except Exception as e:
        logger.error(f"Error in get_calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
