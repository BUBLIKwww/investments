from __future__ import annotations

import random
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.money import q_price
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundRead


def _mock_price_change(old: Decimal) -> Decimal:
    """Random relative change between 1% and 5% up or down (mock pricing)."""
    magnitude = Decimal(str(round(random.uniform(0.01, 0.05), 6)))
    sign = Decimal(1) if random.random() < 0.5 else Decimal(-1)
    factor = Decimal("1") + sign * magnitude
    new_price = q_price(old * factor)
    if new_price <= 0:
        new_price = q_price(old * Decimal("0.95"))
    return new_price


class PricingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._funds = FundRepository(db)

    def refresh_prices(self) -> list[FundRead]:
        funds = self._funds.list_active()
        now = datetime.now(UTC)
        for f in funds:
            new_price = _mock_price_change(f.price)
            self._funds.update_price(int(f.id), price=new_price, updated_at=now)
        self._db.commit()
        refreshed = self._funds.list_active()
        return [FundRead.model_validate(x) for x in refreshed]
