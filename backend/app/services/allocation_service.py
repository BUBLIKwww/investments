from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException, status

from app.domain.enums import TopupMode
from app.domain.money import q_money, q_price, to_decimal
from app.models.fund import Fund
from app.models.portfolio_position import PortfolioPosition
from app.models.strategy_category import StrategyCategory
from app.schemas.topup import TopupCalculateResponse, TopupItemResult
from app.services.pricing.protocol import PricingProvider


@dataclass(frozen=True)
class CategoryFundRow:
    category: StrategyCategory
    fund: Fund


def _lot_cost(*, unit_price: Decimal, lot_size: int) -> Decimal:
    if lot_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lot must be > 0")
    if unit_price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="price must be > 0")
    return q_money(unit_price * Decimal(lot_size))


def _strict_split_total(total: Decimal, actives: list[StrategyCategory]) -> dict[int, Decimal]:
    if total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="total_amount must be > 0")
    if not actives:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active strategy categories")

    sum_pct = sum(to_decimal(c.target_percent) for c in actives)
    if sum_pct != Decimal("100"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sum of target_percent for active categories must be exactly 100",
        )

    out: dict[int, Decimal] = {}
    acc = Decimal("0")
    for i, c in enumerate(actives):
        pct = to_decimal(c.target_percent)
        if i == len(actives) - 1:
            out[c.id] = q_money(total - acc)
        else:
            part = q_money(total * pct / Decimal("100"))
            out[c.id] = part
            acc += part
    return out


def _current_category_values(
    positions: Iterable[PortfolioPosition],
    *,
    price_by_fund_id: dict[int, Decimal],
) -> tuple[dict[int, Decimal], Decimal]:
    values: dict[int, Decimal] = {}
    for p in positions:
        fid = int(p.fund_id)
        price = price_by_fund_id.get(fid)
        if price is None:
            continue
        cid = int(p.category_id)
        values[cid] = values.get(cid, Decimal("0")) + Decimal(int(p.total_units)) * price
    total = q_money(sum(values.values(), start=Decimal("0")))
    return values, total


def _smart_split_total(
    total: Decimal,
    actives: list[StrategyCategory],
    *,
    positions: list[PortfolioPosition],
    price_by_fund_id: dict[int, Decimal],
) -> dict[int, Decimal]:
    vals_by_cat, market_total = _current_category_values(positions, price_by_fund_id=price_by_fund_id)
    if market_total <= 0:
        return _strict_split_total(total, actives)

    tw = {c.id: to_decimal(c.target_percent) / Decimal("100") for c in actives}
    cw = {
        c.id: q_money(vals_by_cat.get(c.id, Decimal("0")) / market_total) if market_total > 0 else Decimal("0")
        for c in actives
    }

    raw = {c.id: max(Decimal("0"), total * (Decimal("2") * tw[c.id] - cw[c.id])) for c in actives}
    s = sum(raw.values(), start=Decimal("0"))
    if s <= 0:
        return _strict_split_total(total, actives)

    out: dict[int, Decimal] = {}
    acc = Decimal("0")
    for i, c in enumerate(actives):
        if i == len(actives) - 1:
            out[c.id] = q_money(total - acc)
        else:
            part = q_money(total * (raw[c.id] / s))
            out[c.id] = part
            acc += part
    return out


def _allocate_lots_for_targets(
    targets: dict[int, Decimal],
    rows_by_category_id: dict[int, CategoryFundRow],
    *,
    unit_price_by_fund_id: dict[int, Decimal],
) -> dict[int, dict[str, object]]:
    per: dict[int, dict[str, object]] = {}
    for cid, target_amount in targets.items():
        row = rows_by_category_id[cid]
        lot_size = int(row.fund.lot)
        unit_price = q_price(unit_price_by_fund_id[int(row.fund.id)])
        lc = _lot_cost(unit_price=unit_price, lot_size=lot_size)
        purchased_lots = int((target_amount // lc)) if lc > 0 else 0
        purchased_units = purchased_lots * lot_size
        actual = q_money(Decimal(purchased_lots) * lc)
        cash_rem = q_money(target_amount - actual)
        per[cid] = {
            "target_amount": q_money(target_amount),
            "price_used": unit_price,
            "lot_size": lot_size,
            "purchased_lots": purchased_lots,
            "purchased_units": purchased_units,
            "actual_allocated_amount": actual,
            "cash_remainder": cash_rem,
        }
    return per


def _maximize_extra_lots(
    *,
    total_amount: Decimal,
    per: dict[int, dict[str, object]],
    rows_by_category_id: dict[int, CategoryFundRow],
    unit_price_by_fund_id: dict[int, Decimal],
) -> None:
    safety = 0
    while safety < 10_000:
        safety += 1
        allocated = q_money(sum(to_decimal(v["actual_allocated_amount"]) for v in per.values()))
        pool = q_money(total_amount - allocated)
        if pool <= 0:
            break

        candidates: list[tuple[Decimal, int]] = []
        for cid, row in rows_by_category_id.items():
            lot_size = int(row.fund.lot)
            unit_price = q_price(unit_price_by_fund_id[int(row.fund.id)])
            lc = _lot_cost(unit_price=unit_price, lot_size=lot_size)
            if lc <= 0 or lc > pool:
                continue
            candidates.append((lc, int(cid)))

        if not candidates:
            break

        lc_min, cid = min(candidates, key=lambda x: (x[0], x[1]))
        row = rows_by_category_id[cid]
        lot_size = int(row.fund.lot)
        unit_price = q_price(unit_price_by_fund_id[int(row.fund.id)])

        slot = per[cid]
        purchased_lots = int(slot["purchased_lots"]) + 1
        purchased_units = purchased_lots * lot_size
        lc_row = _lot_cost(unit_price=unit_price, lot_size=lot_size)
        actual = q_money(Decimal(purchased_lots) * lc_row)
        target_amount = to_decimal(slot["target_amount"])
        cash_rem = q_money(target_amount - actual)

        slot["purchased_lots"] = purchased_lots
        slot["purchased_units"] = purchased_units
        slot["actual_allocated_amount"] = actual
        slot["cash_remainder"] = cash_rem

        _ = lc_min


def _build_unit_prices(
    *,
    actives: list[StrategyCategory],
    positions: list[PortfolioPosition],
    pricing: PricingProvider,
) -> dict[int, Decimal]:
    unit_price_by_fund_id: dict[int, Decimal] = {}
    for c in actives:
        if c.fund is None:
            continue
        unit_price_by_fund_id[int(c.fund.id)] = q_price(pricing.get_unit_price(c.fund))

    for p in positions:
        if p.fund is None:
            continue
        fid = int(p.fund.id)
        if fid not in unit_price_by_fund_id:
            unit_price_by_fund_id[fid] = q_price(pricing.get_unit_price(p.fund))

    return unit_price_by_fund_id


def calculate_topup_allocation(
    *,
    total_amount: Decimal,
    mode: TopupMode,
    ordered_categories: list[StrategyCategory],
    positions: list[PortfolioPosition],
    pricing: PricingProvider,
) -> TopupCalculateResponse:
    total_amount = q_money(to_decimal(total_amount))

    actives = [c for c in ordered_categories if c.is_active and c.fund is not None and c.fund.is_active]
    if not actives:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active categories with funds")

    unit_price_by_fund_id = _build_unit_prices(actives=actives, positions=positions, pricing=pricing)

    rows_by_id: dict[int, CategoryFundRow] = {c.id: CategoryFundRow(category=c, fund=c.fund) for c in actives}

    if mode == TopupMode.STRICT:
        targets = _strict_split_total(total_amount, actives)
    elif mode == TopupMode.SMART:
        targets = _smart_split_total(
            total_amount,
            actives,
            positions=positions,
            price_by_fund_id=unit_price_by_fund_id,
        )
    elif mode == TopupMode.MAXIMIZE:
        targets = _strict_split_total(total_amount, actives)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported mode")

    per = _allocate_lots_for_targets(targets, rows_by_id, unit_price_by_fund_id=unit_price_by_fund_id)

    if mode == TopupMode.MAXIMIZE:
        _maximize_extra_lots(
            total_amount=total_amount,
            per=per,
            rows_by_category_id=rows_by_id,
            unit_price_by_fund_id=unit_price_by_fund_id,
        )

    items: list[TopupItemResult] = []
    for cid in [c.id for c in actives]:
        row = rows_by_id[cid]
        slot = per[cid]
        items.append(
            TopupItemResult(
                category_id=cid,
                category_name=row.category.name,
                fund_id=int(row.fund.id),
                fund_name=row.fund.name,
                ticker=row.fund.ticker,
                target_percent=to_decimal(row.category.target_percent),
                target_amount=to_decimal(slot["target_amount"]),
                price_used=to_decimal(slot["price_used"]),
                lot_size=int(slot["lot_size"]),
                purchased_lots=int(slot["purchased_lots"]),
                purchased_units=int(slot["purchased_units"]),
                actual_allocated_amount=to_decimal(slot["actual_allocated_amount"]),
                cash_remainder=to_decimal(slot["cash_remainder"]),
            )
        )

    total_allocated = q_money(sum(i.actual_allocated_amount for i in items))
    total_remainder = q_money(total_amount - total_allocated)

    if total_amount > 0 and all(i.purchased_units == 0 for i in items):
        min_costs: list[Decimal] = []
        for cid in [c.id for c in actives]:
            row = rows_by_id[cid]
            lot_size = int(row.fund.lot)
            unit_price = q_price(unit_price_by_fund_id[int(row.fund.id)])
            min_costs.append(_lot_cost(unit_price=unit_price, lot_size=lot_size))
        min_need = min(min_costs) if min_costs else Decimal("0")
        min_need_fmt = q_money(min_need)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Суммы недостаточно, чтобы купить хотя бы один лот по любой из категорий. "
                f"Минимальная стоимость одного лота сейчас около {min_need_fmt} ₽ — увеличьте сумму пополнения."
            ),
        )

    return TopupCalculateResponse(
        total_amount=total_amount,
        mode=mode,
        items=items,
        total_allocated_amount=total_allocated,
        total_cash_remainder=total_remainder,
    )
