"""Позиции для движка ребаланса (БД или live T‑Invest)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models.fund import Fund


@dataclass(slots=True)
class LiveEnginePosition:
    """Минимальный набор полей, совместимый с чтением в PortfolioRebalanceService."""

    category_id: int
    fund_id: int
    total_units: int
    fund: Fund
    broker_unit: Decimal | None = None
