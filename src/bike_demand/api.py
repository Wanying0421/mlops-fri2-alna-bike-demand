import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Global state to store the loaded model and its metadata version
class ModelStore:
    def __init__(self):
        self.model: Optional[Any] = None
        self.model_version: Optional[str] = None

    def is_loaded(self) -> bool:
        return self.model is not None and self.model_version is not None


model_store = ModelStore()


# Pydantic request model enforcing the 12 required training features and ranges
class BikePredictionRequest(BaseModel):
    season: int = Field(..., ge=1, le=4)
    mnth: int = Field(..., ge=1, le=12)
    holiday: int = Field(..., ge=0, le=1)
    yr: int = Field(..., ge=0, le=1)
    hr: int = Field(..., ge=0, le=23)
    weekday: int = Field(..., ge=0, le=6)
    workingday: int = Field(..., ge=0, le=1)
    weathersit: int = Field(..., ge=1, le=4)
    temp: float = Field(..., ge=0.0, le=1.0)
    atemp: float = Field(..., ge=0.0, le=1.0)
    hum: float = Field(..., ge=0.0, le=1.0)
    windspeed: float = Field(..., ge=0.0, le=1.0)


# Startup lifecycle: load the saved model artifact and extract version from metadata (never train inside the service)
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = os.getenv("MODEL_PATH", "artifacts/model.joblib")

    if os.path.exists(model_path):
        try:
            artifact = joblib.load(model_path)
            # Handle dictionary artifact containing model and metadata
            if isinstance(artifact, dict) and "model" in artifact:
                model_store.model = artifact["model"]
                model_store.model_version = artifact.get("metadata", {}).get(
                    "version", "m-01"
                )
            else:
                model_store.model = artifact
                model_store.model_version = "m-01"
            print(f"Model loaded successfully. Version: {model_store.model_version}")
        except Exception as e:
            print(f"Error loading model: {e}")
            model_store.model = None
            model_store.model_version = None
    else:
        print(f"Warning: Model artifact not found at {model_path}.")

    yield
    # Clean up model state on shutdown
    model_store.model = None
    model_store.model_version = None


# Initialize FastAPI application
app = FastAPI(title="Bike Demand Prediction API", version="1.0.0", lifespan=lifespan)


# GET /health endpoint: returns 200 only when a usable model is loaded, otherwise 503
@app.get("/health")
def health_check():
    if not model_store.is_loaded():
        raise HTTPException(
            status_code=503, detail="Service unavailable: Model not loaded"
        )
    return {"status": "healthy", "model_version": model_store.model_version}


# POST /predict endpoint: returns a finite, non-negative prediction and model_version
@app.post("/predict")
def predict(payload: BikePredictionRequest):
    if not model_store.is_loaded():
        raise HTTPException(
            status_code=503, detail="Service unavailable: Model not loaded"
        )

    try:
        # Extract the 12 features in order for model prediction
        features = [
            [
                payload.season,
                payload.mnth,
                payload.holiday,
                payload.yr,
                payload.hr,
                payload.weekday,
                payload.workingday,
                payload.weathersit,
                payload.temp,
                payload.atemp,
                payload.hum,
                payload.windspeed,
            ]
        ]

        # Run prediction using the loaded model
        raw_pred = model_store.model.predict(features)[0]

        # Ensure the prediction is finite and non-negative
        prediction_val = max(0.0, float(raw_pred))

        return {
            "prediction": prediction_val,
            "model_version": model_store.model_version,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
