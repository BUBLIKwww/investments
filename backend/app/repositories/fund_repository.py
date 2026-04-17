from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.money import q_price
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

    def get_by_ticker(self, ticker: str) -> Fund | None:
        t = ticker.strip().upper()
        stmt = select(Fund).where(Fund.ticker == t).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_instrument_uid(self, instrument_uid: str) -> Fund | None:
        uid = instrument_uid.strip()
        if not uid:
            return None
        stmt = select(Fund).where(Fund.instrument_uid == uid).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_figi(self, figi: str) -> Fund | None:
        fg = figi.strip()
        if not fg:
            return None
        stmt = select(Fund).where(Fund.figi == fg).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def upsert_from_tinvest(
        self,
        *,
        ticker: str,
        name: str,
        lot: int,
        currency: str,
        instrument_uid: str,
        figi: str | None,
        price: Decimal,
        updated_at: datetime,
    ) -> Fund:
        t = ticker.strip().upper()
        row = self.get_by_ticker(t)
        price_q = q_price(price)
        if row is None:
            row = Fund(
                name=name,
                ticker=t,
                figi_or_uid=instrument_uid,
                instrument_uid=instrument_uid,
                figi=figi,
                lot=lot,
                price=price_q,
                currency=currency.upper()[:8],
                last_price_updated_at=updated_at,
                is_active=True,
            )
            self._db.add(row)
            self._db.flush()
            return row
        row.name = name
        row.lot = lot
        row.currency = currency.upper()[:8]
        row.instrument_uid = instrument_uid
        row.figi = figi
        row.figi_or_uid = instrument_uid
        row.price = price_q
        row.last_price_updated_at = updated_at
        row.is_active = True
        return row

    def update_price(self, fund_id: int, *, price: Decimal, updated_at: datetime) -> None:
        fund = self._db.get(Fund, fund_id)
        if fund is None:
            return
        fund.price = price
        fund.last_price_updated_at = updated_at
