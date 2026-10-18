
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
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


# Pydantic request model with strict validation and forbidden extra fields
class BikePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(os.getenv("MODEL_PATH", "artifacts/model.joblib"))
    metadata_path = Path(os.getenv("METADATA_PATH", "artifacts/model-metadata.json"))

    # Load version and feature names from model-metadata.json if present
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

    # Load model artifact
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


app = FastAPI(title="Bike Demand Prediction API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health_check():
    if not model_store.is_loaded():
        raise HTTPException(
            status_code=503, detail="Service unavailable: Model not loaded"
        )
    return {"status": "healthy", "model_version": model_store.model_version}


@app.post("/predict")
def predict(payload: BikePredictionRequest):
    if not model_store.is_loaded():
        raise HTTPException(
            status_code=503, detail="Service unavailable: Model not loaded"
        )

    try:
        data_dict = payload.model_dump()

        # Build pandas DataFrame with strict column order from metadata if available
        if model_store.feature_names:
            df = pd.DataFrame([data_dict])[model_store.feature_names]
        else:
            df = pd.DataFrame([data_dict])

        raw_pred = model_store.model.predict(df)[0]
        prediction_val = max(0.0, float(raw_pred))

        return {
            "prediction": prediction_val,
            "model_version": model_store.model_version,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
