from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fund import Fund
from app.models.strategy_category import StrategyCategory
from app.models.user import User
from app.repositories.user_repository import MOCK_TELEGRAM_ID, UserRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SeedService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)

    def ensure_seeded(self) -> None:
        if self._db.execute(select(Fund.id).limit(1)).first() is not None:
            return

        funds = [
            Fund(
                name="Фонд крупнейших компаний РФ",
                ticker="FXRL",
                figi_or_uid="mock-figi-fxrl",
                lot=1,
                price=Decimal("42.350000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
            Fund(
                name="Фонд дивидендных акций",
                ticker="SBGB",
                figi_or_uid="mock-figi-sbgb",
                lot=10,
                price=Decimal("18.120000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
            Fund(
                name="Фонд российских технологий",
                ticker="TECH",
                figi_or_uid="mock-figi-tech",
                lot=1,
                price=Decimal("95.400000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
            Fund(
                name="Фонд трендовых акций",
                ticker="TREN",
                figi_or_uid="mock-figi-tren",
                lot=1,
                price=Decimal("31.750000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
            Fund(
                name="Сбалансированный фонд (запасной)",
                ticker="BALN",
                figi_or_uid="mock-figi-baln",
                lot=1,
                price=Decimal("55.000000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
            Fund(
                name="Краткосрочные облигации (запасной)",
                ticker="CASH",
                figi_or_uid="mock-figi-cash",
                lot=1,
                price=Decimal("101.300000"),
                currency="RUB",
                last_price_updated_at=_utcnow(),
                is_active=True,
            ),
        ]
        for f in funds:
            self._db.add(f)
        self._db.flush()

        user = self._users.get_mock_user()
        if user is None:
            user = User(telegram_id=MOCK_TELEGRAM_ID, username="mock_user")
            self._db.add(user)
            self._db.flush()

        fxrl, sbgb, tech, tren = funds[0], funds[1], funds[2], funds[3]
        defaults = [
            ("Крупнейшие компании РФ", Decimal("40.0000"), 1, fxrl.id),
            ("Дивидендные акции", Decimal("25.0000"), 2, sbgb.id),
            ("Российские технологии", Decimal("20.0000"), 3, tech.id),
            ("Трендовые акции", Decimal("15.0000"), 4, tren.id),
        ]
        for name, pct, order, fund_id in defaults:
            self._db.add(
                StrategyCategory(
                    user_id=int(user.id),
                    fund_id=int(fund_id),
                    name=name,
                    target_percent=pct,
                    sort_order=order,
                    is_active=True,
                )
            )

        self._db.commit()
