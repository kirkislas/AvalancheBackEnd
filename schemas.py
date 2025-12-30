from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class AccidentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: str

    season: Optional[str] = None
    date: Optional[str] = None
    display_date: Optional[str] = None

    state: Optional[str] = None
    location: Optional[str] = None
    refined_location: Optional[str] = None

    summary_description: Optional[str] = None
    full_description: Optional[str] = None

    fatalities: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InvalidateCacheRequest(BaseModel):
    keys: Optional[List[str]] = None
