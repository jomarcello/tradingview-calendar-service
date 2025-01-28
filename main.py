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
        return "No economic events scheduled for today."
        
    message = "📅 Economic Calendar\n\n"
    
    for event in events:
        # Convert impact to emoji
        impact_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '⚪'
        }.get(event.impact, '⚪')
        
        message += f"{event.time} | {event.currency} | {impact_emoji} | {event.event}\n"
        
        if event.actual or event.forecast or event.previous:
            details = []
            if event.actual:
                details.append(f"A: {event.actual}")
            if event.forecast:
                details.append(f"F: {event.forecast}")
            if event.previous:
                details.append(f"P: {event.previous}")
            message += f"({' | '.join(details)})\n"
            
        message += "\n"
    
    return message

@app.get("/calendar")
async def get_calendar():
    """Get formatted economic calendar data."""
    try:
        events = await fetch_economic_calendar()
        message = format_telegram_message(events)
        
        # Send to telegram service
        if TELEGRAM_SERVICE_URL:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{TELEGRAM_SERVICE_URL}/send_calendar",
                    json={"message": message}
                )
        
        return {"status": "success", "data": message}
        
    except Exception as e:
        logger.error(f"Error in get_calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
