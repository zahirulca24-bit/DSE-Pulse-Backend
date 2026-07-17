"""FastAPI application entry point for DSE Pulse Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, scanner, signals, status
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Demo/local-only API foundation for the DSE Pulse frontend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)

app.include_router(health.router)
app.include_router(status.router)
app.include_router(scanner.router)
app.include_router(signals.router)
