"""Manual scanner run and latest-result routes with database/local fallback."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus
from app.repositories.ohlc_db_repository import OhlcDbRepository
from app.repositories.scanner_db_repository import ScannerDbRepository
from app.schemas.scanner_result import ScannerCandidatesResponse, ScannerResultResponse
from app.services.dependencies import (
    get_ohlc_db_repository,
    get_ohlc_repository,
    get_scanner_db_repository,
    get_scanner_engine,
    get_scanner_repository,
)
from app.services.ohlc_repository import OhlcRepository
from app.services.scanner_engine import ScannerEngine
from app.services.scanner_repository import ScannerRepository

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _no_scan() -> ScannerResultResponse:
    return ScannerResultResponse(
        ok=False,
        mode="no_scan",
        data_source="none",
        scanned_symbols=0,
        eligible_symbols=0,
        qualified_count=0,
        watch_count=0,
        rejected_count=0,
        generated_at=None,
        message="No scanner result exists yet. Run POST /scanner/run first.",
        candidates=[],
    )


@router.post("/run", response_model=ScannerResultResponse)
def run_scanner(
    database_ohlc: Annotated[OhlcDbRepository, Depends(get_ohlc_db_repository)],
    local_ohlc: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    database_scanner: Annotated[ScannerDbRepository, Depends(get_scanner_db_repository)],
    local_scanner: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    scanner_engine: Annotated[ScannerEngine, Depends(get_scanner_engine)],
) -> ScannerResultResponse:
    if database_ohlc.is_available():
        source = "database"
        rows = database_ohlc.get_all_rows()
        empty_message = "No database DSE OHLC rows are available. Import DSE OHLC CSV into database first."
    else:
        source = "local_csv"
        rows = local_ohlc.get_all_rows()
        empty_message = "No local DSE OHLC CSV is available. Import DSE OHLC CSV first."
    if not rows:
        return ScannerResultResponse(
            ok=False,
            mode="no_data",
            data_source="none",
            scanned_symbols=0,
            eligible_symbols=0,
            qualified_count=0,
            watch_count=0,
            rejected_count=0,
            generated_at=None,
            message=empty_message,
            candidates=[],
        )
    result = scanner_engine.run(rows, source=source)
    if source == "database" and database_scanner.save(result):
        return result
    local_scanner.save(result)
    return result


@router.get("/latest", response_model=ScannerResultResponse)
def get_latest_scanner_result(
    database_repository: Annotated[ScannerDbRepository, Depends(get_scanner_db_repository)],
    local_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> ScannerResultResponse:
    return database_repository.load_latest() or local_repository.load() or _no_scan()


@router.get("/candidates", response_model=ScannerCandidatesResponse)
def get_scanner_candidates(
    database_repository: Annotated[ScannerDbRepository, Depends(get_scanner_db_repository)],
    local_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    grade: Annotated[SignalGrade | None, Query()] = None,
    signal_status: Annotated[SignalStatus | None, Query()] = None,
    sector: Annotated[SectorName | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ScannerCandidatesResponse:
    latest = database_repository.load_latest() or local_repository.load()
    if latest is None:
        return ScannerCandidatesResponse(
            ok=False,
            mode="no_scan",
            data_source="none",
            message="No scanner result exists yet. Run POST /scanner/run first.",
            candidates_count=0,
            candidates=[],
        )
    candidates = [
        candidate
        for candidate in latest.candidates
        if (grade is None or candidate.grade == grade)
        and (signal_status is None or candidate.signal_status == signal_status)
        and (sector is None or candidate.sector == sector)
    ][:limit]
    return ScannerCandidatesResponse(
        ok=True,
        mode=latest.mode,
        data_source=latest.data_source,
        message="Latest scanner candidates returned.",
        candidates_count=len(candidates),
        candidates=candidates,
    )
