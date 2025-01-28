import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import asyncio
from dotenv import load_dotenv
import traceback

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

async def scrape_forex_factory():
    """Scrape economic calendar data from ForexFactory."""
    url = "https://www.forexfactory.com/calendar"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            # First get the cookies
            response = await client.get(url)
            response.raise_for_status()
            
            # Now get the calendar with cookies
            response = await client.get(url)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.text, 'lxml')
        calendar_table = soup.find('table', class_='calendar__table')
        
        if not calendar_table:
            raise ValueError("Calendar table not found")

        events = []
        current_date = None
        
        for row in calendar_table.find_all('tr', class_=['calendar__row', 'calendar_row']):
            # Extract date if present
            date_cell = row.find('td', class_='calendar__date')
            if date_cell and date_cell.text.strip():
                current_date = date_cell.text.strip()
                
            # Extract event data
            time_cell = row.find('td', class_='calendar__time')
            currency_cell = row.find('td', class_='calendar__currency')
            impact_cell = row.find('td', class_='calendar__impact')
            event_cell = row.find('td', class_='calendar__event')
            
            if all([time_cell, currency_cell, impact_cell, event_cell]):
                # Get impact level
                impact = 'low'
                if impact_cell.find('span'):
                    impact_class = impact_cell.find('span')['class'][0]
                    if 'high' in impact_class:
                        impact = 'high'
                    elif 'medium' in impact_class:
                        impact = 'medium'
                
                event = EconomicEvent(
                    time=time_cell.text.strip(),
                    currency=currency_cell.text.strip(),
                    impact=impact,
                    event=event_cell.text.strip()
                )
                events.append(event)
        
        return events
        
    except Exception as e:
        logger.error(f"Error scraping ForexFactory: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error scraping calendar data: {str(e)}")

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
        events = await scrape_forex_factory()
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
