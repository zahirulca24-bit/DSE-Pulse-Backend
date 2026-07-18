"""Manual scanner routes using only the approved Drive-backed local OHLC cache."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.sectors import SectorName
from app.core.signal_rules import SignalGrade, SignalStatus
from app.data.symbol_metadata import PHASE1_SYMBOLS
from app.schemas.scanner_result import ScannerCandidatesResponse, ScannerResultResponse
from app.services.dependencies import get_ohlc_repository, get_scanner_engine, get_scanner_repository
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
    ohlc_cache: Annotated[OhlcRepository, Depends(get_ohlc_repository)],
    scanner_repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    scanner_engine: Annotated[ScannerEngine, Depends(get_scanner_engine)],
) -> ScannerResultResponse:
    """Scan only the approved Phase-1 universe from the Drive-backed OHLC cache."""

    rows = ohlc_cache.get_all_rows()
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
            message=(
                "No approved DSE OHLC cache is available. "
                "Import/sync verified OHLC data through the Google Drive storage pipeline first."
            ),
            candidates=[],
        )

    source_symbols = {row.symbol for row in rows}
    approved_rows = [row for row in rows if row.symbol in PHASE1_SYMBOLS]
    approved_symbols = source_symbols & PHASE1_SYMBOLS
    out_of_scope_count = len(source_symbols - PHASE1_SYMBOLS)

    if not approved_rows:
        return ScannerResultResponse(
            ok=False,
            mode="no_data",
            data_source="none",
            scanned_symbols=len(source_symbols),
            eligible_symbols=0,
            qualified_count=0,
            watch_count=0,
            rejected_count=0,
            generated_at=None,
            message=(
                "The OHLC cache contains no approved Phase-1 symbols. "
                f"{out_of_scope_count} out-of-scope symbol(s) were excluded fail-closed."
            ),
            candidates=[],
        )

    result = scanner_engine.run(approved_rows, source="local_csv")
    result.scanned_symbols = len(source_symbols)
    result.message = (
        f"Phase-1 scanner evaluated {len(approved_symbols)} approved symbol(s). "
        f"{out_of_scope_count} out-of-scope symbol(s) were excluded fail-closed. "
        + result.message
    )
    scanner_repository.save(result)
    return result


@router.get("/latest", response_model=ScannerResultResponse)
def get_latest_scanner_result(
    repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
) -> ScannerResultResponse:
    """Return only the latest scan persisted by the approved cache-backed scanner path."""

    return repository.load() or _no_scan()


@router.get("/candidates", response_model=ScannerCandidatesResponse)
def get_scanner_candidates(
    repository: Annotated[ScannerRepository, Depends(get_scanner_repository)],
    grade: Annotated[SignalGrade | None, Query()] = None,
    signal_status: Annotated[SignalStatus | None, Query()] = None,
    sector: Annotated[SectorName | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ScannerCandidatesResponse:
    """Filter candidates from the latest approved cache-backed scanner result only."""

    latest = repository.load()
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
