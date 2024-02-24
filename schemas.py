from pydantic import BaseModel

class AccidentSchema(BaseModel):
    id: int
    season: str
    date: str
    state: str
    location: str
    description: str
    fatalities: int
    latitude: float
    longitude: float


    class Config:
        from_attributes = True