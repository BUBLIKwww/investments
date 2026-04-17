"""Общий gRPC‑клиент T‑Invest (боевой контур по умолчанию)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException, status

from app.core.config import Settings


@contextmanager
def tinvest_client(settings: Settings) -> Generator[object, None, None]:
    try:
        from tinkoff.invest import Client
        from tinkoff.invest.constants import INVEST_GRPC_API, INVEST_GRPC_API_SANDBOX
    except ImportError as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Сервер: не установлен пакет tinkoff-investments",
        ) from e

    token = (settings.TINVEST_TOKEN or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TINVEST_TOKEN не задан.",
        )

    target = INVEST_GRPC_API_SANDBOX if settings.TINVEST_USE_SANDBOX else INVEST_GRPC_API
    with Client(token, target=target) as client:
        yield client
