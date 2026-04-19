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
from app.services.tinvest_client import money_value_to_decimal, quotation_to_decimal, tinvest_client

logger = logging.getLogger(__name__)


def _account_type_name(v: object) -> str:
    s = str(v or "").strip()
    if s in ("1", "ACCOUNT_TYPE_TINKOFF"):
        return "tinkoff"
    if s in ("2", "ACCOUNT_TYPE_TINKOFF_IIS"):
        return "iis"
    if s in ("3", "ACCOUNT_TYPE_INVEST_BOX"):
        return "invest_box"
    return "unknown"


def _account_status_name(v: object) -> str:
    s = str(v or "").strip()
    if s in ("2", "ACCOUNT_STATUS_OPEN"):
        return "open"
    if s in ("3", "ACCOUNT_STATUS_CLOSED"):
        return "closed"
    if s in ("1", "ACCOUNT_STATUS_NEW"):
        return "new"
    return "unknown"


def _access_level_name(v: object) -> str:
    s = str(v or "").strip()
    if s in ("1", "ACCOUNT_ACCESS_LEVEL_FULL_ACCESS"):
        return "full"
    if s in ("2", "ACCOUNT_ACCESS_LEVEL_READ_ONLY"):
        return "read_only"
    if s in ("3", "ACCOUNT_ACCESS_LEVEL_NO_ACCESS"):
        return "none"
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
        # Последний резерв: первый подходящий открытый счёт с полным доступом.
        try:
            picked = self.pick_default_broker_account_id()
        except Exception:
            logger.exception("pick_default_broker_account_id failed")
            picked = None
        if picked:
            return picked
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не выбран счёт T‑Invest: GET /api/v1/broker/accounts и PUT /api/v1/broker/settings",
        )

    def list_accounts(self) -> list[dict]:
        with tinvest_client(self._settings) as client:
            resp = client.get_accounts(status_name="ACCOUNT_STATUS_ALL")
            out: list[dict] = []
            for a in resp:
                if not isinstance(a, dict):
                    continue
                row = BrokerAccountRead(
                    id=str(a.get("id") or "").strip(),
                    name=(str(a.get("name") or "").strip() or str(a.get("id") or "").strip()),
                    type=_account_type_name(a.get("type")),
                    status=_account_status_name(a.get("status")),
                    access_level=_access_level_name(a.get("accessLevel")),
                )
                out.append(row.model_dump())
            return out

    def pick_default_broker_account_id(self) -> str | None:
        """Первый открытый брокерский счёт (не ИИС), full access; иначе None."""
        with tinvest_client(self._settings) as client:
            resp = client.get_accounts(status_name="ACCOUNT_STATUS_ALL")
            candidates: list[tuple[int, str]] = []
            first_available: str | None = None
            for a in resp:
                if not isinstance(a, dict):
                    continue
                aid = str(a.get("id") or "").strip()
                if not aid:
                    continue
                if first_available is None:
                    first_available = aid
                status_name = _account_status_name(a.get("status"))
                access_name = _access_level_name(a.get("accessLevel"))
                type_name = _account_type_name(a.get("type"))
                if status_name != "open":
                    continue
                if access_name not in ("full", "unknown"):
                    continue
                if type_name not in ("tinkoff", "invest_box", "unknown"):
                    continue
                prio = 0 if type_name == "tinkoff" else 1
                candidates.append((prio, aid))
            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]))
                return candidates[0][1]
            return first_available

    def rub_cash_on_account(self, account_id: str) -> Decimal:
        with tinvest_client(self._settings) as client:
            pos = client.get_withdraw_limits(account_id)
            rows = pos.get("money") if isinstance(pos.get("money"), list) else pos.get("withdrawMoney")
            if not isinstance(rows, list):
                rows = []
            for m in rows:
                cur = str(m.get("currency") or "").strip().upper()
                if cur == "RUB":
                    return money_value_to_decimal(m)
        return Decimal("0")

    def live_engine_positions_and_cash(self, user_id: int, account_id: str) -> tuple[list[LiveEnginePosition], Decimal]:
        """Позиции только по инструментам активных категорий стратегии + RUB на счёте."""
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
            port = client.get_portfolio(account_id)
            cash = self.rub_cash_on_account(account_id)

            out: list[LiveEnginePosition] = []
            for p in port.get("positions", []):
                uid = (str(p.get("instrumentUid") or "").strip() or str(p.get("figi") or "").strip())
                if not uid or uid not in uid_to_cf:
                    continue
                cid, fund = uid_to_cf[uid]
                qty_dec = quotation_to_decimal(p.get("quantity"))
                units = int(qty_dec.to_integral_value(rounding=ROUND_FLOOR)) if qty_dec > 0 else 0
                if units < 1:
                    continue
                bu: Decimal | None = None
                try:
                    if p.get("currentPrice") is not None:
                        bu = money_value_to_decimal(p.get("currentPrice"))
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
