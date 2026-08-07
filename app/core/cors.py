"""CORS origin helpers for Cloud Run and local development."""

from __future__ import annotations


def normalize_origins(*values: str) -> list[str]:
    """Return unique normalized HTTP(S) origins from comma-separated values."""

    origins: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in (value or "").split(","):
            origin = item.strip().rstrip("/")
            if not origin or not origin.startswith(("http://", "https://")):
                continue
            if origin not in seen:
                seen.add(origin)
                origins.append(origin)
    return origins
