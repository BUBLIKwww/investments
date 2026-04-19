"""Поиск и добавление инструментов через T-Invest Invest API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.money import q_price
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundAddRequest, FundRead, FundSearchResult
from app.services.tinvest_client import tinvest_client

logger = logging.getLogger(__name__)


class TinvestFundsService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._funds = FundRepository(db)

    def search_instruments(self, query: str, *, limit: int = 15) -> list[FundSearchResult]:
        q = (query or "").strip()
        if len(q) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query must be at least 2 characters")
        lim = max(1, min(limit, 25))

        from tinkoff.invest.schemas import InstrumentIdType
        from tinkoff.invest.utils import quotation_to_decimal

        out: list[FundSearchResult] = []
        seen_uid: set[str] = set()

        with tinvest_client(self._settings) as client:
            r = client.instruments.find_instrument(query=q, api_trade_available_flag=True)
            uids_order: list[str] = []
            for short in r.instruments:
                uid = (short.uid or "").strip()
                if not uid or uid in seen_uid:
                    continue
                seen_uid.add(uid)
                uids_order.append(uid)
                if len(uids_order) >= lim:
                    break

            if not uids_order:
                return []

            lp = client.market_data.get_last_prices(instrument_id=uids_order)
            price_by_uid: dict[str, Decimal] = {}
            for p in lp.last_prices:
                k = (p.instrument_uid or p.figi or "").strip()
                if k:
                    price_by_uid[k] = quotation_to_decimal(p.price)

            for uid in uids_order:
                full = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                    id=uid,
                ).instrument
                if full is None:
                    continue
                figi_v = (full.figi or "").strip() or None
                ticker = (full.ticker or "").strip().upper()
                name = (full.name or ticker).strip()
                lot = int(full.lot or 1)
                cur = (full.currency or "rub").upper()[:8]
                last = price_by_uid.get(uid)
                out.append(
                    FundSearchResult(
                        name=name,
                        ticker=ticker,
                        instrument_uid=uid,
                        figi=figi_v,
                        lot=lot,
                        currency=cur,
                        last_price=last,
                    )
                )
        return out

    def add_fund(self, payload: FundAddRequest) -> FundRead:
        uid = payload.instrument_uid.strip()
        if not uid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="instrument_uid is required")

        existing = self._funds.get_by_instrument_uid(uid)
        if existing is not None:
            self._refresh_single_price(existing)
            self._db.commit()
            return FundRead.model_validate(self._funds.get_by_id(int(existing.id)) or existing)

        from tinkoff.invest.schemas import InstrumentIdType
        from tinkoff.invest.utils import quotation_to_decimal

        now = datetime.now(UTC)
        with tinvest_client(self._settings) as client:
            full = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                id=uid,
            ).instrument
            if full is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found in T-Invest")
            api_ticker = (full.ticker or "").strip().upper()
            if api_ticker and api_ticker != payload.ticker.strip().upper():
                logger.warning("Ticker mismatch client=%s api=%s for uid=%s", payload.ticker, api_ticker, uid)
            name = (full.name or payload.name).strip()
            lot = int(full.lot or payload.lot)
            cur = (full.currency or payload.currency or "rub").upper()[:8]
            figi_v = (full.figi or payload.figi or "").strip() or None
            ticker_final = api_ticker or payload.ticker.strip().upper()

            lp = client.market_data.get_last_prices(instrument_id=[uid])
            price = Decimal("0")
            for p in lp.last_prices:
                k = (p.instrument_uid or "").strip()
                if k == uid:
                    price = quotation_to_decimal(p.price)
                    break
            if price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Не удалось получить last price для инструмента",
                )

        row = self._funds.upsert_from_tinvest(
            ticker=ticker_final,
            name=name,
            lot=lot,
            currency=cur,
            instrument_uid=uid,
            figi=figi_v,
            price=q_price(price),
            updated_at=now,
        )
        self._db.commit()
        refreshed = self._funds.get_by_id(int(row.id))
        return FundRead.model_validate(refreshed or row)

    def _refresh_single_price(self, fund: Fund) -> None:
        uid = (fund.instrument_uid or "").strip()
        if not uid:
            return
        from tinkoff.invest.utils import quotation_to_decimal

        now = datetime.now(UTC)
        with tinvest_client(self._settings) as client:
            lp = client.market_data.get_last_prices(instrument_id=[uid])
            for p in lp.last_prices:
                if (p.instrument_uid or "").strip() == uid:
                    dec = quotation_to_decimal(p.price)
                    if dec > 0:
                        self._funds.update_price(int(fund.id), price=q_price(dec), updated_at=now)
                    return
