import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field


# Global state to store the loaded model and its metadata version
class ModelStore:
    def __init__(self):
        self.model: Optional[Any] = None
        self.model_version: Optional[str] = None
        self.feature_names: Optional[list[str]] = None

    def is_loaded(self) -> bool:
        return self.model is not None and self.model_version is not None


model_store = ModelStore()


class BikePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    season: int = Field(..., ge=1, le=4)
    mnth: int = Field(..., ge=1, le=12)
    holiday: int = Field(..., ge=0, le=1)
    yr: int = Field(..., ge=0, le=1)
    hr: int = Field(..., ge=0, le=99)
    weekday: int = Field(..., ge=0, le=6)
    workingday: int = Field(..., ge=0, le=1)
    weathersit: int = Field(..., ge=1, le=4)
    temp: float = Field(..., ge=0.0, le=1.0)
    atemp: float = Field(..., ge=0.0, le=1.0)
    hum: float = Field(..., ge=0.0, le=1.0)
    windspeed: float = Field(..., ge=0.0, le=1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(os.getenv("MODEL_PATH", "artifacts/model.joblib"))
    metadata_path = Path(os.getenv("METADATA_PATH", "artifacts/model-metadata.json"))

    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                model_store.model_version = meta.get("model_version") or meta.get(
                    "version"
                )
                model_store.feature_names = meta.get("features") or meta.get(
                    "feature_names"
                )
        except Exception as e:
            print(f"Error reading metadata: {e}")

    if model_path.exists():
        try:
            artifact = joblib.load(model_path)
            if isinstance(artifact, dict) and "model" in artifact:
                model_store.model = artifact["model"]
                if not model_store.model_version:
                    model_store.model_version = artifact.get("metadata", {}).get(
                        "version"
                    )
            else:
                model_store.model = artifact
        except Exception as e:
            print(f"Error loading model: {e}")

    yield
    model_store.model = None
    model_store.model_version = None
    model_store.feature_names = None


# Initialize FastAPI app with lifespan
app = FastAPI(title="Bike Demand Prediction API", version="1.0.0", lifespan=lifespan)

# Configure basic logging to output single-line JSON
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bike_demand")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log each request's event, status code, duration, and model version, including exceptions."""
    start_time = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        current_version = model_store.model_version or "unknown"

        log_data = {
            "event": request.url.path,
            "status": status_code,
            "ms": duration_ms,
            "model_version": current_version,
        }
        logger.info(json.dumps(log_data))


@app.get("/health")
def health_check():
    """Health check endpoint to verify service and model status."""
    if not model_store.is_loaded():
        raise HTTPException(status_code=503, detail="Model not loaded")
    git_sha = os.getenv("GIT_SHA", "unknown")
    return {
        "status": "healthy",
        "model_version": model_store.model_version,
        "git_sha": git_sha,
    }


@app.post("/predict")
def predict(payload: BikePredictionRequest):
    """Predict bike demand based on input features with non-negative guard."""
    if not model_store.is_loaded():
        raise HTTPException(status_code=503, detail="Model not loaded")
    try:
        input_data = pd.DataFrame([payload.model_dump()])
        if model_store.feature_names:
            input_data = input_data[model_store.feature_names]
        prediction = model_store.model.predict(input_data)
        final_prediction = max(0.0, float(prediction[0]))
        git_sha = os.getenv("GIT_SHA", "unknown")
        return {
            "prediction": final_prediction,
            "model_version": model_store.model_version,
            "git_sha": git_sha,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
