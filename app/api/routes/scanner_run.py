"""Manual scanner routes and market scheduler status."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus
from app.schemas.scanner_result import ScannerCandidatesResponse, ScannerResultResponse
from app.schemas.scanner_scheduler import ScannerSchedulerStatusResponse
from app.security.admin import require_backend_admin
from app.services.dependencies import (
    get_market_scanner_scheduler,
    get_scanner_repository,
    get_scanner_service,
)
from app.services.scanner_repository import ScannerRepository
from app.services.scanner_scheduler import MarketScannerScheduler
from app.services.scanner_service import ScannerService

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _no_scan() -> ScannerResultResponse:
    return ScannerResultResponse(ok=False, mode="no_scan", data_source="none", scanned_symbols=0,
        eligible_symbols=0, qualified_count=0, watch_count=0, rejected_count=0, generated_at=None,
        message="No scanner result exists yet. Run POST /scanner/run first.", candidates=[])


@router.post("/run", response_model=ScannerResultResponse, dependencies=[Depends(require_backend_admin)])
def run_scanner(service: Annotated[ScannerService, Depends(get_scanner_service)]) -> ScannerResultResponse:
    """Run the approved scanner path after administrator authorization."""
    return service.run()


@router.get("/scheduler/status", response_model=ScannerSchedulerStatusResponse)
def get_scanner_scheduler_status(
    scheduler: Annotated[MarketScannerScheduler, Depends(get_market_scanner_scheduler)],
) -> ScannerSchedulerStatusResponse:
    return scheduler.status()


@router.get("/latest", response_model=ScannerResultResponse)
def get_latest_scanner_result(
    repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> ScannerResultResponse:
    return repository.load() or _no_scan()


@router.get("/candidates", response_model=ScannerCandidatesResponse)
def get_scanner_candidates(
    repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    grade: Annotated[SignalGrade | None, Query()] = None,
    signal_status: Annotated[SignalStatus | None, Query()] = None,
    sector: Annotated[SectorName | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ScannerCandidatesResponse:
    latest = repository.load()
    if latest is None:
        return ScannerCandidatesResponse(ok=False, mode="no_scan", data_source="none",
            message="No scanner result exists yet. Run POST /scanner/run first.", candidates_count=0,
            candidates=[])
    candidates = [candidate for candidate in latest.candidates
        if (grade is None or candidate.grade == grade)
        and (signal_status is None or candidate.signal_status == signal_status)
        and (sector is None or candidate.sector == sector)][:limit]
    return ScannerCandidatesResponse(ok=True, mode=latest.mode, data_source=latest.data_source,
        message="Latest scanner candidates returned.", candidates_count=len(candidates), candidates=candidates)
