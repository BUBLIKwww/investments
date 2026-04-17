"""План ребаланса с учётом денежного баланса (без реальных заявок T‑Invest)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_FLOOR, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    RebalancePreviewResponse,
)
from app.schemas.transaction import InvestmentTransactionCreate
from app.services.pricing.db_provider import DbPricingProvider
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
    ) -> tuple[list, set[int], dict[int, Decimal], Decimal, Decimal, Decimal, Decimal, dict[int, Decimal]]:
        """actives, act_ids, deltas, total_market, cash, scale, total_wealth, current_by_cat (руб. по категориям)."""
        if amount is not None and amount < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount не может быть отрицательным")

        categories = self._strategy.list_for_user(user_id)
        actives = _actives_ordered(categories)
        _validate_actives(actives)
        act_ids = {int(c.id) for c in actives}

        positions = self._portfolio.list_positions(user_id)
        current_by_cat: dict[int, Decimal] = {}
        for p in positions:
            if p.fund is None:
                continue
            cid = int(p.category_id)
            if cid not in act_ids:
                continue
            unit = q_price(self._pricing.get_unit_price(p.fund))
            if unit <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Некорректная цена фонда id={p.fund_id}; обновите котировки",
                )
            cur = q_money(Decimal(int(p.total_units)) * unit)
            current_by_cat[cid] = current_by_cat.get(cid, Decimal("0")) + cur

        total_market = q_money(sum(current_by_cat.values(), start=Decimal("0")))
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
    ) -> list[_RebalanceLeg]:
        """Сырые дельты → ноги с ограничением по позиции, лотам и доступному кэшу."""
        positions = self._portfolio.list_positions(user_id)
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
            legs.append(
                _RebalanceLeg(
                    category_id=cid,
                    fund_id=fid,
                    ticker=ticker,
                    action="sell",
                    quantity=qty,
                    total_amount=amt,
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
            legs.append(
                _RebalanceLeg(
                    category_id=cid,
                    fund_id=fid,
                    ticker=ticker,
                    action="buy",
                    quantity=qty,
                    total_amount=amt,
                )
            )

        sells_first = [l for l in legs if l.action == "sell"]
        buys_rest = [l for l in legs if l.action == "buy"]
        return sells_first + buys_rest

    def preview(self, user_id: int, amount: Decimal | None) -> RebalancePreviewResponse:
        actives, act_ids, deltas, total_market, cash, scale, total_wealth, current_by_cat = self._raw_deltas_scaled(
            user_id, amount
        )

        legs = self._build_legs(user_id, actives, act_ids, deltas, cash)
        actions = [
            RebalanceActionRead(fund_id=l.fund_id, ticker=l.ticker, action=l.action, amount=l.total_amount)
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

        return RebalancePreviewResponse(
            cash_balance=cash,
            scale=scale.quantize(Decimal("0.0001")),
            actions=actions,
            total_used=total_used,
            before_percent=before_pct,
            after_percent=after_pct,
            instruments=instruments,
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
