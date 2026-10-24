import time
import json
import logging
from fastapi import FastAPI, Request

# Define model version for logging and tracking
MODEL_VERSION = "baseline-2baaf9359833"

# Initialize FastAPI app
app = FastAPI()

# Configure basic logging to output single-line JSON
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bike_demand")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log each request's event, status code, duration, and model version."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    
    # Construct structured JSON log entry
    log_data = {
        "event": request.url.path,
        "status": response.status_code,
        "ms": duration_ms,
        "model_version": MODEL_VERSION
    }
    
    logger.info(json.dumps(log_data))
    return response

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "healthy", "model_version": MODEL_VERSION}