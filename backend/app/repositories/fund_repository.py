from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fund import Fund


class FundRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_active(self) -> list[Fund]:
        stmt = select(Fund).where(Fund.is_active.is_(True)).order_by(Fund.ticker.asc())
        return list(self._db.execute(stmt).scalars().all())

    def list_all(self) -> list[Fund]:
        stmt = select(Fund).order_by(Fund.ticker.asc())
        return list(self._db.execute(stmt).scalars().all())

    def get_by_id(self, fund_id: int) -> Fund | None:
        return self._db.get(Fund, fund_id)

    def get_by_ids(self, fund_ids: list[int]) -> dict[int, Fund]:
        if not fund_ids:
            return {}
        stmt = select(Fund).where(Fund.id.in_(fund_ids))
        funds = self._db.execute(stmt).scalars().all()
        return {f.id: f for f in funds}

    def update_price(self, fund_id: int, *, price: Decimal, updated_at: datetime) -> None:
        fund = self._db.get(Fund, fund_id)
        if fund is None:
            return
        fund.price = price
        fund.last_price_updated_at = updated_at
