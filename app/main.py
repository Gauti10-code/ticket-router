from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

from .config import settings

app=FastAPI(title=settings.app_name,version=settings.version)


class ReadinessResponse(BaseModel):
    ready: bool
    model_loaded: bool
    detail: str

class HealthResponse(BaseModel):
    status:str
    app:str
    version:str
    environment:str

@app.get("/health",response_model=HealthResponse,tags=["system"])
def health()->HealthResponse:
    """Liveness check :is the process up??"""

    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )

@app.get("/ready",response_model=ReadinessResponse,tags=["system"])
def ready()->ReadinessResponse:
    """Readiness check: can this instance actually serve traffic?"""
    model_loaded=Path(settings.model_path).exists()
    return ReadinessResponse(
        ready=model_loaded,
        model_loaded=model_loaded,
        detail="model found" if model_loaded else "model not trained yet"
    )