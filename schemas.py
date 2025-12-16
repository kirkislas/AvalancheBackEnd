from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class AccidentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season: str
    date: str
    state: str
    location: str
    description: Optional[str] = None
    fatalities: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class InvalidateCacheRequest(BaseModel):
    keys: Optional[List[str]] = None
