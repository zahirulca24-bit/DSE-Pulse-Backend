"""FastAPI application entry point for DSE Pulse Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import data, database, health, ohlc, scanner, scanner_run, signals, status, symbols
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Optional database and local CSV API foundation for the DSE Pulse frontend.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(health.router)
app.include_router(status.router)
app.include_router(database.router)
app.include_router(scanner.router)
app.include_router(scanner_run.router)
app.include_router(signals.router)
app.include_router(data.router)
app.include_router(symbols.router)
app.include_router(ohlc.router)
