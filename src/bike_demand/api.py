from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Bike Demand API")

class PredictRequest(BaseModel):
    # Reject unlisted fields
    model_config = ConfigDict(extra="forbid") 
    
    # Integer constraints
    season: int = Field(ge=1, le=4)
    yr: int = Field(ge=0, le=1)
    mnth: int = Field(ge=1, le=12)
    hr: int = Field(ge=0, le=23)
    holiday: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    workingday: int = Field(ge=0, le=1)
    weathersit: int = Field(ge=1, le=4)
    
    # Float constraints (0.0 to 1.0)
    temp: float = Field(ge=0.0, le=1.0)
    atemp: float = Field(ge=0.0, le=1.0)
    hum: float = Field(ge=0.0, le=1.0)
    windspeed: float = Field(ge=0.0, le=1.0)