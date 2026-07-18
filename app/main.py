"""FastAPI application entry point for DSE Pulse Backend."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    collector,
    data,
    database,
    drive,
    health,
    ohlc,
    scanner,
    scanner_run,
    signals,
    status,
    symbols,
)
from app.core.config import get_settings
from app.services.dependencies import get_market_scanner_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    scheduler = get_market_scanner_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Google Drive backed DSE data storage, audit, OHLC, and scheduled scanner API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-Collector-Token"],
)
app.include_router(health.router)
app.include_router(status.router)
app.include_router(drive.router)
app.include_router(database.router)
app.include_router(collector.router)
app.include_router(scanner.router)
app.include_router(scanner_run.router)
app.include_router(signals.router)
app.include_router(data.router)
app.include_router(symbols.router)
app.include_router(ohlc.router)
