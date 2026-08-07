"""Centralized authorization guards for privileged backend operations."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_backend_admin(
    supplied_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Require the configured backend admin token for privileged write routes."""

    configured_token = get_settings().backend_admin_token.strip()
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Privileged backend operations are disabled until BACKEND_ADMIN_TOKEN is configured.",
        )

    candidate = (supplied_token or "").strip()
    if not candidate or not secrets.compare_digest(configured_token, candidate):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backend administrator authorization failed.",
        )


def require_collector_run_authorization(
    supplied_collector_token: Annotated[str | None, Header(alias="X-Collector-Token")] = None,
    supplied_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    """Authorize collector execution for Cloud Scheduler or a backend administrator."""

    settings = get_settings()
    configured_collector_token = settings.collector_admin_token.strip()
    configured_admin_token = settings.backend_admin_token.strip()
    if not configured_collector_token and not configured_admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Collector execution is disabled until COLLECTOR_ADMIN_TOKEN or "
                "BACKEND_ADMIN_TOKEN is configured."
            ),
        )

    collector_candidate = (supplied_collector_token or "").strip()
    if (
        configured_collector_token
        and collector_candidate
        and secrets.compare_digest(configured_collector_token, collector_candidate)
    ):
        return

    admin_candidate = (supplied_admin_token or "").strip()
    if (
        configured_admin_token
        and admin_candidate
        and secrets.compare_digest(configured_admin_token, admin_candidate)
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Collector authorization failed.",
    )
