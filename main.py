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
SIGNAL_ENTRY_URL = os.getenv("SIGNAL_ENTRY_URL", "https://tradingview-signal-processor-production.up.railway.app")

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

def format_signal_data(events: List[EconomicEvent]) -> dict:
    """Format events into a signal that matches the signal entry format."""
    if not events:
        return None
        
    # Get the highest impact event for the signal
    high_impact_events = [e for e in events if e.impact == "high"]
    main_event = high_impact_events[0] if high_impact_events else events[0]
    
    # Create signal in the format expected by signal entry
    signal = {
        "source": "economic_calendar",
        "instrument": main_event.currency + "USD",  # Convert to forex pair
        "action": "ALERT",  # No specific action, just an alert
        "entry": None,  # No entry price for calendar events
        "stop_loss": None,  # No stop loss for calendar events
        "take_profit": None,  # No take profit for calendar events
        "timeframe": "1h",
        "strategy": "Economic Calendar Alert",
        "events": [
            {
                "time": e.time,
                "currency": e.currency,
                "impact": e.impact,
                "event": e.event,
                "forecast": e.forecast,
                "previous": e.previous,
                "actual": e.actual
            } for e in events
        ],
        "risk_management": {
            "position_size": "1-2% max",
            "notes": [
                "Consider event impact on open positions",
                "Adjust position sizes during high impact events",
                "Be aware of potential market volatility"
            ]
        }
    }
    
    return signal

@app.get("/calendar")
async def get_calendar():
    """Get economic calendar data and send through signal entry."""
    try:
        events = await fetch_economic_calendar()
        signal = format_signal_data(events)
        
        if signal:
            # Send to signal entry service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SIGNAL_ENTRY_URL}/process_signal",
                    json=signal
                )
                response.raise_for_status()
                
                logger.info(f"Signal sent to entry processor: {signal}")
                return {"status": "success", "message": "Calendar signal sent to entry processor"}
        else:
            return {"status": "success", "message": "No events to process"}
        
    except Exception as e:
        logger.error(f"Error in get_calendar: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
