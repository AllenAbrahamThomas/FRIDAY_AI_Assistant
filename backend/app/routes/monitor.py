from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.worldmonitor_service import world_monitor_service

router = APIRouter(prefix="/api/monitor", tags=["Monitor"])

class ConflictEvent(BaseModel):
    id: str
    region: str
    severity: str  # "Critical", "High", "Medium", "Low"
    description: str
    source: str

class TelemetryData(BaseModel):
    global_risk_index: float
    active_conflicts: int
    economic_stability_score: float
    last_updated: str
    recent_events: List[ConflictEvent]
    alternatives: List[Dict[str, str]]

@router.get("/telemetry", response_model=TelemetryData)
async def get_telemetry():
    # Fetch live telemetry data from World Monitor service
    telemetry = await world_monitor_service.get_telemetry()
    
    alternatives = [
        {
            "name": "GDELT Project",
            "url": "https://www.gdeltproject.org/",
            "desc": "Real-time global news monitoring and event mapping in 100+ languages."
        },
        {
            "name": "Liveuamap",
            "url": "https://liveuamap.com/",
            "desc": "Map-centric live tracker focusing on conflict zones, military actions, and protests."
        },
        {
            "name": "ACLED",
            "url": "https://acleddata.com/",
            "desc": "Armed Conflict Location & Event Data project tracking political violence globally."
        },
        {
            "name": "World Monitor App",
            "url": "https://www.worldmonitor.app/",
            "desc": "Aggregated OSINT dashboard for flights, ships, markets, infrastructure, and conflicts."
        }
    ]
    
    # Map dictionary returned from service to BaseModel
    recent_events = [ConflictEvent(**e) for e in telemetry["recent_events"]]
    
    return TelemetryData(
        global_risk_index=telemetry["global_risk_index"],
        active_conflicts=telemetry["active_conflicts"],
        economic_stability_score=telemetry["economic_stability_score"],
        last_updated=telemetry["last_updated"],
        recent_events=recent_events,
        alternatives=alternatives
    )
