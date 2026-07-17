"""Protected manual DSE data collector endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status

from app.schemas.collector import CollectorHistoryResponse, CollectorRunRequest, CollectorRunResponse
from app.services.collector_service import (
    CollectorAuthorizationError,
    CollectorConflictError,
    CollectorDisabledError,
    CollectorService,
    CollectorUnavailableError,
)
from app.services.dependencies import get_collector_service

router = APIRouter(prefix="/collector", tags=["collector"])


@router.post("/run", response_model=CollectorRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_collector(
    request: CollectorRunRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[CollectorService, Depends(get_collector_service)],
    collector_token: Annotated[str | None, Header(alias="X-Collector-Token")] = None,
) -> CollectorRunResponse:
    """Queue one protected collection job and return immediately."""

    try:
        service.authorize(collector_token)
        job = service.start(request.trade_date)
    except CollectorDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except CollectorAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CollectorConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CollectorUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    background_tasks.add_task(service.execute, job.job_id)
    return job


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
