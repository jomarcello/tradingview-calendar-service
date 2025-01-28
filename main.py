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
    """Fetch economic calendar data from Investing.com."""
    url = "https://api.investing.com/economic-calendar/data"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.investing.com",
            "Referer": "https://www.investing.com/economic-calendar/"
        }
        
        # Get today's date
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        params = {
            "date": date_str,
            "timeZone": "Europe/Amsterdam",
            "timeFilter": "timeOnly",
            "importance": "1,2,3",
            "countries": "all"
        }
        
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for event in data.get('data', []):
                impact_level = {
                    '1': 'low',
                    '2': 'medium',
                    '3': 'high'
                }.get(str(event.get('importance', '1')), 'low')
                
                events.append(EconomicEvent(
                    time=event.get('time', ''),
                    currency=event.get('currency', ''),
                    impact=impact_level,
                    event=event.get('event', ''),
                    actual=event.get('actual', ''),
                    forecast=event.get('forecast', ''),
                    previous=event.get('previous', '')
                ))
            
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
