"""Manual local CSV scanner run and latest-result routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus
from app.schemas.scanner_result import ScannerCandidatesResponse, ScannerResultResponse
from app.services.dependencies import (
    get_ohlc_repository,
    get_scanner_engine,
    get_scanner_repository,
)
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _no_scan() -> ScannerResultResponse:
    return ScannerResultResponse(ok=False, mode="no_scan", data_source="none", scanned_symbols=0,
        eligible_symbols=0, qualified_count=0, watch_count=0, rejected_count=0, generated_at=None,
        message="No scanner result exists yet. Run POST /scanner/run first.", candidates=[])


@router.post("/run", response_model=ScannerResultResponse)
def run_scanner(
    ohlc_repository: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    scanner_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    scanner_engine: Annotated[ScannerEngine, Depends(get_scanner_engine)],
) -> ScannerResultResponse:
    rows = ohlc_repository.get_all_rows()
    if not rows:
        return ScannerResultResponse(ok=False, mode="no_data", data_source="none", scanned_symbols=0,
            eligible_symbols=0, qualified_count=0, watch_count=0, rejected_count=0, generated_at=None,
            message="No local DSE OHLC CSV is available. Import DSE OHLC CSV first.", candidates=[])
    result = scanner_engine.run(rows)
    scanner_repository.save(result)
    return result


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
            message="No scanner result exists yet. Run POST /scanner/run first.",
            candidates_count=0, candidates=[])
    candidates = [candidate for candidate in latest.candidates
        if (grade is None or candidate.grade == grade)
        and (signal_status is None or candidate.signal_status == signal_status)
        and (sector is None or candidate.sector == sector)]
    candidates = candidates[:limit]
    return ScannerCandidatesResponse(ok=True, mode="local_csv", data_source="local_csv",
        message="Latest scanner candidates returned.", candidates_count=len(candidates), candidates=candidates)
