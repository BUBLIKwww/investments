from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.money import q_price
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundRead, FundsPricesRefreshResponse


class PricingService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or Settings()
        self._funds = FundRepository(db)

    def refresh_prices(self) -> FundsPricesRefreshResponse:
        token = (self._settings.TINVEST_TOKEN or "").strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TINVEST_TOKEN не задан — обновление цен через T-Invest API недоступно.",
            )

        try:
            from tinkoff.invest import Client
            from tinkoff.invest.constants import INVEST_GRPC_API, INVEST_GRPC_API_SANDBOX
            from tinkoff.invest.utils import quotation_to_decimal
        except ImportError as e:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Сервер: не установлен пакет tinkoff-investments",
            ) from e

        funds = self._funds.list_active()
        now = datetime.now(UTC)
        uids: list[str] = []
        for f in funds:
            uid = (f.instrument_uid or "").strip()
            if uid:
                uids.append(uid)
        if not uids:
            self._db.execute(
                update(Fund)
                .where(Fund.is_active.is_(True), Fund.last_price_updated_at.is_(None))
                .values(last_price_updated_at=now)
            )
            self._db.commit()
            refreshed = self._funds.list_active()
            return FundsPricesRefreshResponse(
                updated=0,
                funds=[FundRead.model_validate(x) for x in refreshed],
            )

        target = INVEST_GRPC_API_SANDBOX if self._settings.TINVEST_USE_SANDBOX else INVEST_GRPC_API

        with Client(token, target=target) as client:
            lp = client.market_data.get_last_prices(instrument_id=uids)
            price_map: dict[str, Decimal] = {}
            for p in lp.last_prices:
                key = (p.instrument_uid or "").strip()
                if not key:
                    continue
                price_map[key] = quotation_to_decimal(p.price)

        updated_count = 0
        for f in funds:
            uid = (f.instrument_uid or "").strip()
            if not uid:
                continue
            new_price = price_map.get(uid)
            if new_price is None or new_price <= 0:
                continue
            self._funds.update_price(int(f.id), price=q_price(new_price), updated_at=now)
            updated_count += 1

        # Заполнить отсутствующий timestamp (например, после миграций), чтобы API было однозначно.
        self._db.execute(
            update(Fund)
            .where(Fund.is_active.is_(True), Fund.last_price_updated_at.is_(None))
            .values(last_price_updated_at=now)
        )

        self._db.commit()
        refreshed = self._funds.list_active()
        return FundsPricesRefreshResponse(
            updated=updated_count,
            funds=[FundRead.model_validate(x) for x in refreshed],
        )
