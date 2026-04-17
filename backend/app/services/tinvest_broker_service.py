"""Счета, кэш и снимок портфеля T‑Invest для live‑режима."""

from __future__ import annotations

import logging
from decimal import ROUND_FLOOR, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.fund import Fund
from app.repositories.broker_settings_repository import BrokerSettingsRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.broker import BrokerAccountRead
from app.services.live_positions import LiveEnginePosition
from app.services.tinvest_client import tinvest_client

logger = logging.getLogger(__name__)


def _account_type_name(v: object) -> str:
    try:
        from tinkoff.invest.schemas import AccountType

        if v == AccountType.ACCOUNT_TYPE_TINKOFF:
            return "tinkoff"
        if v == AccountType.ACCOUNT_TYPE_TINKOFF_IIS:
            return "iis"
        if v == AccountType.ACCOUNT_TYPE_INVEST_BOX:
            return "invest_box"
    except Exception:
        pass
    return "unknown"


def _account_status_name(v: object) -> str:
    try:
        from tinkoff.invest.schemas import AccountStatus

        if v == AccountStatus.ACCOUNT_STATUS_OPEN:
            return "open"
        if v == AccountStatus.ACCOUNT_STATUS_CLOSED:
            return "closed"
        if v == AccountStatus.ACCOUNT_STATUS_NEW:
            return "new"
    except Exception:
        pass
    return "unknown"


def _access_level_name(v: object) -> str:
    try:
        from tinkoff.invest.schemas import AccessLevel

        if v == AccessLevel.ACCOUNT_ACCESS_LEVEL_FULL_ACCESS:
            return "full"
        if v == AccessLevel.ACCOUNT_ACCESS_LEVEL_READ_ONLY:
            return "read_only"
        if v == AccessLevel.ACCOUNT_ACCESS_LEVEL_NO_ACCESS:
            return "none"
    except Exception:
        pass
    return "unknown"


class TinvestBrokerService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._broker_repo = BrokerSettingsRepository(db)
        self._strategy = StrategyRepository(db)

    def resolve_account_id(self) -> str:
        rid = self._broker_repo.get_selected_account_id()
        if rid:
            return rid
        env = (self._settings.TINVEST_DEFAULT_ACCOUNT_ID or "").strip()
        if env:
            return env
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не выбран счёт T‑Invest: GET /api/v1/broker/accounts и PUT /api/v1/broker/settings",
        )

    def list_accounts(self) -> list[dict]:
        with tinvest_client(self._settings) as client:
            resp = client.users.get_accounts()
            out: list[dict] = []
            for a in resp.accounts:
                row = BrokerAccountRead(
                    id=a.id,
                    name=(a.name or "").strip() or a.id,
                    type=_account_type_name(a.type),
                    status=_account_status_name(a.status),
                    access_level=_access_level_name(a.access_level),
                )
                out.append(row.model_dump())
            return out

    def pick_default_broker_account_id(self) -> str | None:
        """Первый открытый брокерский счёт (не ИИС), full access; иначе None."""
        try:
            from tinkoff.invest.schemas import AccessLevel, AccountStatus, AccountType
        except ImportError:
            return None

        with tinvest_client(self._settings) as client:
            resp = client.users.get_accounts()
            candidates: list[tuple[int, object]] = []
            for a in resp.accounts:
                if a.status != AccountStatus.ACCOUNT_STATUS_OPEN:
                    continue
                if a.access_level != AccessLevel.ACCOUNT_ACCESS_LEVEL_FULL_ACCESS:
                    continue
                if a.type not in (AccountType.ACCOUNT_TYPE_TINKOFF, AccountType.ACCOUNT_TYPE_INVEST_BOX):
                    continue
                prio = 0 if a.type == AccountType.ACCOUNT_TYPE_TINKOFF else 1
                candidates.append((prio, a))
            if not candidates:
                return None
            candidates.sort(key=lambda x: (x[0], x[1].id))
            return str(candidates[0][1].id)

    def rub_cash_on_account(self, account_id: str) -> Decimal:
        from tinkoff.invest.utils import money_to_decimal

        with tinvest_client(self._settings) as client:
            pos = client.operations.get_positions(account_id=account_id)
            for m in pos.money:
                cur = (m.currency or "").strip().upper()
                if cur == "RUB":
                    return money_to_decimal(m)
        return Decimal("0")

    def live_engine_positions_and_cash(self, user_id: int, account_id: str) -> tuple[list[LiveEnginePosition], Decimal]:
        """Позиции только по инструментам активных категорий стратегии + RUB на счёте."""
        from tinkoff.invest.utils import money_to_decimal, quotation_to_decimal

        categories = self._strategy.list_for_user(user_id)
        actives = sorted((c for c in categories if c.is_active), key=lambda x: (x.sort_order, x.id))
        uid_to_cf: dict[str, tuple[int, Fund]] = {}
        for c in actives:
            if c.fund is None:
                continue
            uid = (c.fund.instrument_uid or "").strip()
            if uid:
                uid_to_cf[uid] = (int(c.id), c.fund)
                continue
            fg = (c.fund.figi or "").strip()
            if fg:
                uid_to_cf[fg] = (int(c.id), c.fund)

        with tinvest_client(self._settings) as client:
            port = client.operations.get_portfolio(account_id=account_id)
            cash = self.rub_cash_on_account(account_id)

            out: list[LiveEnginePosition] = []
            for p in port.positions:
                uid = (p.instrument_uid or "").strip() or (p.figi or "").strip()
                if not uid or uid not in uid_to_cf:
                    continue
                cid, fund = uid_to_cf[uid]
                qty_dec = quotation_to_decimal(p.quantity)
                units = int(qty_dec.to_integral_value(rounding=ROUND_FLOOR)) if qty_dec > 0 else 0
                if units < 1:
                    continue
                bu: Decimal | None = None
                try:
                    if p.current_price is not None:
                        bu = money_to_decimal(p.current_price)
                except Exception:
                    bu = None
                out.append(
                    LiveEnginePosition(
                        category_id=cid,
                        fund_id=int(fund.id),
                        total_units=units,
                        fund=fund,
                        broker_unit=bu if bu and bu > 0 else None,
                    )
                )
            return out, cash
