"""План ребаланса: симуляция по журналу или live по счёту T‑Invest."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.enums import TransactionOperationType
from app.domain.money import q_money, q_price, to_decimal
from app.repositories.cash_repository import CashRepository
from app.repositories.fund_repository import FundRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.portfolio_rebalance import (
    RebalanceActionRead,
    RebalanceExecuteResponse,
    RebalanceInstrumentPreview,
    RebalanceLiveExecuteRequest,
    RebalanceLiveExecuteResponse,
    RebalanceLiveOrderResult,
    RebalancePreviewResponse,
)
from app.schemas.transaction import InvestmentTransactionCreate
from app.services.pricing.db_provider import DbPricingProvider
from app.services.tinvest_broker_service import TinvestBrokerService
from app.services.tinvest_client import tinvest_client
from app.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


def _actives_ordered(categories: list) -> list:
    return sorted((c for c in categories if c.is_active), key=lambda x: (x.sort_order, x.id))


def _validate_actives(actives: list) -> None:
    if not actives:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет активных категорий стратегии")
    s = sum(to_decimal(c.target_percent) for c in actives)
    if s != Decimal("100"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма target_percent активных категорий должна быть ровно 100",
        )


def _buy_qty_from_budget(budget: Decimal, unit: Decimal, lot: int) -> int:
    """floor(budget / price / lot) * lot."""
    lot = max(1, lot)
    if budget <= 0 or unit <= 0:
        return 0
    lots_n = int((budget / (unit * Decimal(lot))).to_integral_value(rounding=ROUND_FLOOR))
    return max(0, lots_n * lot)


def _sell_qty_from_target(target_rub: Decimal, unit: Decimal, lot: int, available: int) -> int:
    """floor(target / price / lot) * lot, не больше доступных штук (сетка лотов)."""
    lot = max(1, lot)
    if target_rub <= 0 or unit <= 0 or available < 1:
        return 0
    lots_n = int((target_rub / (unit * Decimal(lot))).to_integral_value(rounding=ROUND_FLOOR))
    qty = lots_n * lot
    cap = (available // lot) * lot
    return int(min(qty, cap))


def _simulate_leg_impact(
    legs: list[_RebalanceLeg],
    current_by_cat: dict[int, Decimal],
    cash: Decimal,
    act_ids: set[int],
) -> tuple[dict[int, Decimal], Decimal]:
    cat = {int(k): q_money(v) for k, v in current_by_cat.items()}
    for aid in act_ids:
        cat.setdefault(int(aid), Decimal("0"))
    c_run = q_money(cash)
    for leg in legs:
        cid = int(leg.category_id)
        if leg.action == "sell":
            cat[cid] = q_money(cat.get(cid, Decimal("0")) - leg.total_amount)
            c_run = q_money(c_run + leg.total_amount)
        else:
            cat[cid] = q_money(cat.get(cid, Decimal("0")) + leg.total_amount)
            c_run = q_money(c_run - leg.total_amount)
    return cat, c_run


@dataclass(frozen=True)
class _RebalanceLeg:
    category_id: int
    fund_id: int
    ticker: str
    action: str
    quantity: int
    total_amount: Decimal
    lot: int
    instrument_id: str


def _plan_fingerprint(legs: list[_RebalanceLeg]) -> str:
    parts: list[dict[str, object]] = []
    for l in sorted(legs, key=lambda x: (x.action, x.ticker, x.fund_id)):
        lo = max(1, int(l.lot))
        lots_n = int(l.quantity) // lo if lo > 0 else 0
        parts.append(
            {
                "action": l.action,
                "ticker": l.ticker,
                "fund_id": l.fund_id,
                "qty": int(l.quantity),
                "lots": lots_n,
                "instrument_id": l.instrument_id,
                "amt": str(q_money(l.total_amount)),
            }
        )
    raw = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PortfolioRebalanceService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._cash = CashRepository(db)
        self._portfolio = PortfolioRepository(db)
        self._strategy = StrategyRepository(db)
        self._funds = FundRepository(db)
        self._pricing = DbPricingProvider()
        self._tx = TransactionService(db)

    def cash_balance(self, user_id: int) -> Decimal:
        return q_money(self._cash.cash_balance(user_id))

    def _raw_deltas_scaled(
        self,
        user_id: int,
        amount: Decimal | None,
        *,
        positions_override: list | None = None,
        cash_override: Decimal | None = None,
    ) -> tuple[list, set[int], dict[int, Decimal], Decimal, Decimal, Decimal, Decimal, dict[int, Decimal]]:
        """actives, act_ids, deltas, total_market, cash, scale, total_wealth, current_by_cat (руб. по категориям)."""
        if amount is not None and amount < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount не может быть отрицательным")

        categories = self._strategy.list_for_user(user_id)
        actives = _actives_ordered(categories)
        _validate_actives(actives)
        act_ids = {int(c.id) for c in actives}

        positions = positions_override if positions_override is not None else self._portfolio.list_positions(user_id)
        current_by_cat: dict[int, Decimal] = {}
        for p in positions:
            if p.fund is None:
                continue
            cid = int(p.category_id)
            if cid not in act_ids:
                continue
            bu = getattr(p, "broker_unit", None)
            if bu is not None and bu > 0:
                unit = q_price(bu)
            else:
                unit = q_price(self._pricing.get_unit_price(p.fund))
            if unit <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Некорректная цена фонда id={p.fund_id}; обновите котировки",
                )
            units = int(getattr(p, "total_units", 0))
            cur = q_money(Decimal(units) * unit)
            current_by_cat[cid] = current_by_cat.get(cid, Decimal("0")) + cur

        total_market = q_money(sum(current_by_cat.values(), start=Decimal("0")))
        if cash_override is not None:
            cash = q_money(cash_override)
        else:
            cash = q_money(self._cash.cash_balance(user_id))
        total_wealth = q_money(total_market + cash)

        deltas: dict[int, Decimal] = {}
        for c in actives:
            cid = int(c.id)
            tgt = q_money(to_decimal(c.target_percent) / Decimal("100") * total_wealth)
            cur = q_money(current_by_cat.get(cid, Decimal("0")))
            deltas[cid] = q_money(tgt - cur)

        scale = Decimal("1")
        if cash > 0 and amount is not None:
            cap = q_money(to_decimal(amount))
            if cap <= 0:
                scale = Decimal("0")
            else:
                use = min(cap, cash)
                scale = q_money(use / cash)
        elif cash <= 0 and amount is not None and amount <= 0:
            scale = Decimal("0")

        for cid in list(deltas.keys()):
            deltas[cid] = q_money(deltas[cid] * scale)

        return actives, act_ids, deltas, total_market, cash, scale, total_wealth, current_by_cat

    def _remaining_units(
        self,
        positions: list,
        act_ids: set[int],
    ) -> dict[tuple[int, int], int]:
        out: dict[tuple[int, int], int] = {}
        for p in positions:
            if p.fund is None:
                continue
            cid = int(p.category_id)
            if cid not in act_ids:
                continue
            key = (cid, int(p.fund_id))
            out[key] = out.get(key, 0) + int(p.total_units)
        return out

    def _build_legs(
        self,
        user_id: int,
        actives: list,
        act_ids: set[int],
        deltas: dict[int, Decimal],
        cash_balance: Decimal,
        *,
        positions_override: list | None = None,
    ) -> list[_RebalanceLeg]:
        """Сырые дельты → ноги с ограничением по позиции, лотам и доступному кэшу."""
        positions = positions_override if positions_override is not None else self._portfolio.list_positions(user_id)
        remaining = self._remaining_units(positions, act_ids)

        raw_sells: list[tuple[int, int, str, str, Decimal]] = []  # cat_id, fund_id, ticker, action, rub
        raw_buys: list[tuple[int, int, str, str, Decimal]] = []
        for c in actives:
            cid = int(c.id)
            d = deltas.get(cid, Decimal("0"))
            if abs(d) < Decimal("0.005"):
                continue
            if c.fund is None:
                continue
            fid = int(c.fund_id)
            ticker = c.fund.ticker
            if d > 0:
                raw_buys.append((cid, fid, ticker, "buy", q_money(d)))
            else:
                raw_sells.append((cid, fid, ticker, "sell", q_money(abs(d))))

        legs: list[_RebalanceLeg] = []
        rem = dict(remaining)

        for cid, fid, ticker, _op, target_rub in raw_sells:
            fund_ent = self._funds.get_by_id(fid)
            if fund_ent is None:
                continue
            unit = q_price(self._pricing.get_unit_price(fund_ent))
            lot = max(int(fund_ent.lot), 1)
            if unit <= 0:
                continue
            key = (cid, fid)
            avail = rem.get(key, 0)
            qty = _sell_qty_from_target(target_rub, unit, lot, avail)
            if qty < 1:
                logger.info(
                    "rebalance: skip sell user=%s fund_id=%s (qty=0 after lot cap), target_rub=%s avail=%s lot=%s",
                    user_id,
                    fid,
                    target_rub,
                    avail,
                    lot,
                )
                continue
            amt = q_money(Decimal(qty) * unit)
            rem[key] = avail - qty
            iid = (
                (fund_ent.instrument_uid or "").strip()
                or (fund_ent.figi or "").strip()
                or (fund_ent.figi_or_uid or "").strip()
            )
            if not iid:
                logger.warning("rebalance: skip sell fund_id=%s — нет instrument_uid/figi", fid)
                continue
            legs.append(
                _RebalanceLeg(
                    category_id=cid,
                    fund_id=fid,
                    ticker=ticker,
                    action="sell",
                    quantity=qty,
                    total_amount=amt,
                    lot=lot,
                    instrument_id=iid,
                )
            )

        cash_run = q_money(
            cash_balance + sum((l.total_amount for l in legs if l.action == "sell"), Decimal("0"))
        )

        for cid, fid, ticker, _op, target_rub in raw_buys:
            fund_ent = self._funds.get_by_id(fid)
            if fund_ent is None:
                continue
            unit = q_price(self._pricing.get_unit_price(fund_ent))
            lot = max(int(fund_ent.lot), 1)
            if unit <= 0:
                continue
            spend = min(target_rub, cash_run)
            if spend <= 0:
                logger.info(
                    "rebalance: skip buy user=%s fund_id=%s (no cash), target_rub=%s cash_run=%s",
                    user_id,
                    fid,
                    target_rub,
                    cash_run,
                )
                continue
            qty = _buy_qty_from_budget(spend, unit, lot)
            if qty < 1:
                logger.info(
                    "rebalance: skip buy user=%s fund_id=%s (qty=0 after lots), budget=%s lot=%s unit=%s",
                    user_id,
                    fid,
                    spend,
                    lot,
                    unit,
                )
                continue
            amt = q_money(Decimal(qty) * unit)
            if amt > cash_run:
                qty = _buy_qty_from_budget(cash_run, unit, lot)
                if qty < 1:
                    logger.info(
                        "rebalance: skip buy user=%s fund_id=%s after cash clamp, cash_run=%s",
                        user_id,
                        fid,
                        cash_run,
                    )
                    continue
                amt = q_money(Decimal(qty) * unit)
            cash_run = q_money(cash_run - amt)
            iid = (
                (fund_ent.instrument_uid or "").strip()
                or (fund_ent.figi or "").strip()
                or (fund_ent.figi_or_uid or "").strip()
            )
            if not iid:
                logger.warning("rebalance: skip buy fund_id=%s — нет instrument_uid/figi", fid)
                continue
            legs.append(
                _RebalanceLeg(
                    category_id=cid,
                    fund_id=fid,
                    ticker=ticker,
                    action="buy",
                    quantity=qty,
                    total_amount=amt,
                    lot=lot,
                    instrument_id=iid,
                )
            )

        sells_first = [l for l in legs if l.action == "sell"]
        buys_rest = [l for l in legs if l.action == "buy"]
        return sells_first + buys_rest

    def preview(
        self,
        user_id: int,
        amount: Decimal | None,
        *,
        mode: Literal["simulation", "live"] = "simulation",
    ) -> RebalancePreviewResponse:
        account_id: str | None = None
        pos_ov: list | None = None
        cash_ov: Decimal | None = None
        if mode == "live":
            br = TinvestBrokerService(self._db, settings)
            account_id = br.resolve_account_id()
            pos_ov, cash_ov = br.live_engine_positions_and_cash(user_id, account_id)

        actives, act_ids, deltas, total_market, cash, scale, total_wealth, current_by_cat = self._raw_deltas_scaled(
            user_id, amount, positions_override=pos_ov, cash_override=cash_ov
        )

        legs = self._build_legs(
            user_id, actives, act_ids, deltas, cash, positions_override=pos_ov
        )
        actions = [
            RebalanceActionRead(
                fund_id=l.fund_id,
                ticker=l.ticker,
                action=l.action,
                amount=l.total_amount,
                quantity=l.quantity,
                lots=int(l.quantity // max(1, l.lot)),
                instrument_id=l.instrument_id,
            )
            for l in legs
        ]
        buy_sum = q_money(sum((l.total_amount for l in legs if l.action == "buy"), Decimal("0")))
        sell_sum = q_money(sum((l.total_amount for l in legs if l.action == "sell"), Decimal("0")))
        total_used = q_money(buy_sum - sell_sum)

        cat_after, cash_after = _simulate_leg_impact(legs, current_by_cat, cash, act_ids)
        total_m_after = q_money(
            sum((cat_after.get(int(c.id), Decimal("0")) for c in actives), Decimal("0"))
        )
        tw_after = q_money(total_m_after + cash_after)
        before_pct = (
            q_money(total_market / total_wealth * Decimal("100")) if total_wealth > 0 else Decimal("0")
        )
        after_pct = q_money(total_m_after / tw_after * Decimal("100")) if tw_after > 0 else Decimal("0")

        instruments: list[RebalanceInstrumentPreview] = []
        for c in actives:
            cid = int(c.id)
            cur_r = q_money(current_by_cat.get(cid, Decimal("0")))
            aft_r = q_money(cat_after.get(cid, Decimal("0")))
            cur_pct = q_money(cur_r / total_wealth * Decimal("100")) if total_wealth > 0 else Decimal("0")
            aft_pct = q_money(aft_r / tw_after * Decimal("100")) if tw_after > 0 else Decimal("0")
            ticker = c.fund.ticker if c.fund else ""
            instruments.append(
                RebalanceInstrumentPreview(
                    ticker=ticker,
                    fund_id=int(c.fund_id),
                    current_percent=cur_pct,
                    target_percent=to_decimal(c.target_percent),
                    after_percent=aft_pct,
                )
            )

        fp = _plan_fingerprint(legs)
        return RebalancePreviewResponse(
            cash_balance=cash,
            scale=scale.quantize(Decimal("0.0001")),
            actions=actions,
            total_used=total_used,
            before_percent=before_pct,
            after_percent=after_pct,
            instruments=instruments,
            mode=mode,
            plan_fingerprint=fp,
            account_id=account_id,
        )

    def execute(self, user_id: int, amount: Decimal | None) -> RebalanceExecuteResponse:
        actives, act_ids, deltas, _tm, cash, _scale, _tw, _cbc = self._raw_deltas_scaled(user_id, amount)
        legs = self._build_legs(user_id, actives, act_ids, deltas, cash)

        now = datetime.now(timezone.utc)
        created: list[int] = []

        for leg in legs:
            fund_ent = self._funds.get_by_id(int(leg.fund_id))
            if fund_ent is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Фонд id={leg.fund_id} не найден в каталоге",
                )
            unit = q_price(self._pricing.get_unit_price(fund_ent))
            if unit <= 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Цена фонда должна быть > 0")

            op = TransactionOperationType.BUY if leg.action == "buy" else TransactionOperationType.SELL
            read = self._tx.create(
                user_id,
                InvestmentTransactionCreate(
                    fund_id=int(leg.fund_id),
                    category_id=int(leg.category_id),
                    operation_type=op,
                    quantity=int(leg.quantity),
                    price_per_unit=unit,
                    total_amount=q_money(leg.total_amount),
                    executed_at=now,
                    note="Ребаланс (симуляция)",
                ),
            )
            created.append(int(read.id))

        return RebalanceExecuteResponse(created_transaction_ids=created)

    def execute_live(self, user_id: int, payload: RebalanceLiveExecuteRequest) -> RebalanceLiveExecuteResponse:
        if not payload.dry_run and not payload.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для реальных заявок передайте confirm=true (или dry_run=true для проверки без ордеров)",
            )

        br = TinvestBrokerService(self._db, settings)
        account_id = br.resolve_account_id()
        pos_ov, cash_ov = br.live_engine_positions_and_cash(user_id, account_id)

        actives, act_ids, deltas, _tm, cash, _sc, _tw, _cbc = self._raw_deltas_scaled(
            user_id, payload.amount, positions_override=pos_ov, cash_override=cash_ov
        )
        legs = self._build_legs(
            user_id, actives, act_ids, deltas, cash, positions_override=pos_ov
        )
        fp = _plan_fingerprint(legs)
        if fp != payload.plan_fingerprint.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="План ребаланса изменился с момента preview — пересчитайте preview (live)",
            )

        if payload.dry_run:
            return RebalanceLiveExecuteResponse(orders=[], dry_run=True)

        sells = [l for l in legs if l.action == "sell"]
        buys = [l for l in legs if l.action == "buy"]
        ordered = sells + buys

        results: list[RebalanceLiveOrderResult] = []

        try:
            from tinkoff.invest.schemas import (
                OrderDirection,
                OrderExecutionReportStatus,
                OrderType,
            )
        except ImportError as e:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Пакет tinkoff-investments не установлен",
            ) from e

        with tinvest_client(settings) as client:
            for leg in ordered:
                lo = max(1, int(leg.lot))
                lots_n = int(leg.quantity) // lo
                if lots_n < 1:
                    results.append(
                        RebalanceLiveOrderResult(
                            ticker=leg.ticker,
                            action=leg.action,
                            instrument_id=leg.instrument_id,
                            lots=0,
                            success=False,
                            message="Ноль лотов после нормализации",
                        )
                    )
                    continue
                oid = str(uuid.uuid4())
                direction = (
                    OrderDirection.ORDER_DIRECTION_BUY
                    if leg.action == "buy"
                    else OrderDirection.ORDER_DIRECTION_SELL
                )
                logger.info(
                    "live_order_submit user=%s account=%s instrument=%s lots=%s dir=%s order_id=%s",
                    user_id,
                    account_id,
                    leg.instrument_id,
                    lots_n,
                    leg.action,
                    oid,
                )
                try:
                    r = client.orders.post_order(
                        instrument_id=leg.instrument_id,
                        quantity=lots_n,
                        account_id=account_id,
                        order_id=oid,
                        direction=direction,
                        order_type=OrderType.ORDER_TYPE_MARKET,
                    )
                    st = r.execution_report_status.name if r.execution_report_status is not None else None
                    st_e = r.execution_report_status
                    ok = st_e not in (
                        OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_REJECTED,
                        OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED,
                        OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_UNSPECIFIED,
                        None,
                    )
                    msg = (r.message or "").strip() or None
                    logger.info(
                        "live_order_result user=%s broker_order=%s status=%s msg=%s",
                        user_id,
                        r.order_id,
                        st,
                        msg,
                    )
                    results.append(
                        RebalanceLiveOrderResult(
                            ticker=leg.ticker,
                            action=leg.action,
                            instrument_id=leg.instrument_id,
                            lots=lots_n,
                            success=ok,
                            order_id=r.order_id or None,
                            execution_status=st,
                            message=msg,
                        )
                    )
                except Exception as e:
                    logger.exception("live_order_failed user=%s ticker=%s", user_id, leg.ticker)
                    results.append(
                        RebalanceLiveOrderResult(
                            ticker=leg.ticker,
                            action=leg.action,
                            instrument_id=leg.instrument_id,
                            lots=lots_n,
                            success=False,
                            message=str(e)[:500],
                        )
                    )

        return RebalanceLiveExecuteResponse(orders=results, dry_run=False)
