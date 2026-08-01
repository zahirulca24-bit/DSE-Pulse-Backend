"""Protected manual DSE data collector endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status

from app.schemas.collector import (
    CollectorHistoryResponse,
    CollectorRunRequest,
    CollectorRunResponse,
    CollectorStatusResponse,
)
from app.security.admin import require_backend_admin
from app.services.collector_service import CollectorService
from app.services.dependencies import get_collector_service, get_production_collector_service
from app.services.production_collector_service import (
    ProductionCollectorDatabaseError,
    ProductionCollectorService,
    ProductionCollectorUnavailableError,
)

router = APIRouter(prefix="/collector", tags=["collector"])


@router.post(
    "/run",
    response_model=CollectorStatusResponse | CollectorRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_backend_admin)],
)
def run_collector(
    request: CollectorRunRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[
        ProductionCollectorService,
        Depends(get_production_collector_service),
    ],
    legacy_service: Annotated[CollectorService, Depends(get_collector_service)],
    collector_token: Annotated[str | None, Header(alias="X-Collector-Token")] = None,
) -> CollectorStatusResponse | CollectorRunResponse:
    """Run the configured verified production collector once."""

    try:
        return service.run(request.trade_date)
    except ProductionCollectorDatabaseError:
        return _run_legacy_collector(request, background_tasks, legacy_service, collector_token)
    except ProductionCollectorUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _run_legacy_collector(
    request: CollectorRunRequest,
    background_tasks: BackgroundTasks,
    service: CollectorService,
    collector_token: str | None,
) -> CollectorRunResponse:
    from app.services.collector_service import (
        CollectorAuthorizationError,
        CollectorDisabledError,
    )

    try:
        service.authorize(collector_token)
        job = service.start(request.trade_date)
    except CollectorDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except CollectorAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    background_tasks.add_task(service.execute, job.job_id, request.collect_missing)
    return job


@router.get("/status", response_model=CollectorStatusResponse)
def get_production_collector_status(
    service: Annotated[
        ProductionCollectorService,
        Depends(get_production_collector_service),
    ],
) -> CollectorStatusResponse:
    return service.status()


@router.post(
    "/start",
    response_model=CollectorStatusResponse,
    dependencies=[Depends(require_backend_admin)],
)
def start_collector(
    service: Annotated[
        ProductionCollectorService,
        Depends(get_production_collector_service),
    ],
) -> CollectorStatusResponse:
    try:
        return service.start()
    except ProductionCollectorDatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post(
    "/stop",
    response_model=CollectorStatusResponse,
    dependencies=[Depends(require_backend_admin)],
)
def stop_collector(
    service: Annotated[
        ProductionCollectorService,
        Depends(get_production_collector_service),
    ],
) -> CollectorStatusResponse:
    try:
        return service.stop()
    except ProductionCollectorDatabaseError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/status/{job_id}", response_model=CollectorRunResponse)
def get_collector_status(
    job_id: str,
    service: Annotated[CollectorService, Depends(get_collector_service)],
) -> CollectorRunResponse:
    job = service.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collector job was not found.")
    return job


@router.get("/latest", response_model=CollectorRunResponse)
def get_latest_collector_job(
    service: Annotated[CollectorService, Depends(get_collector_service)],
) -> CollectorRunResponse:
    job = service.latest()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No collector job is available.")
    return job


@router.get("/history", response_model=CollectorHistoryResponse)
def get_collector_history(
    service: Annotated[CollectorService, Depends(get_collector_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CollectorHistoryResponse:
    jobs = service.history(limit)
    return CollectorHistoryResponse(count=len(jobs), jobs=jobs)
