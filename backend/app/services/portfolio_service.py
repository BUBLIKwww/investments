from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal
from typing import Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.money import q_money, q_price, to_decimal
from app.models.portfolio_position import PortfolioPosition
from app.repositories.fund_repository import FundRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.fund import FundRead
from app.schemas.portfolio import CategorySummary, PortfolioPositionRead, PortfolioRead
from app.services.pricing.db_provider import DbPricingProvider
from app.services.tinvest_broker_service import TinvestBrokerService
from app.services.tinvest_client import money_value_to_decimal, quotation_to_decimal, tinvest_client

logger = logging.getLogger(__name__)


def _empty_portfolio(*, source: str = "simulation") -> PortfolioRead:
    src: Literal["simulation", "live"] = "live" if source == "live" else "simulation"
    return PortfolioRead(
        source=src,
        total_invested_amount=Decimal("0"),
        total_current_amount=Decimal("0"),
        total_pnl=Decimal("0"),
        total_pnl_percent=Decimal("0"),
        categories=[],
        positions=[],
    )


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._portfolio = PortfolioRepository(db)
        self._strategy = StrategyRepository(db)
        self._funds = FundRepository(db)
        self._pricing = DbPricingProvider()

    def get_portfolio(self, user_id: int, *, source: str = "simulation") -> PortfolioRead:
        try:
            if source == "live":
                return self._build_portfolio_live(user_id)
            return self._build_portfolio(user_id)
        except HTTPException:
            raise
        except Exception:
            logger.exception("get_portfolio failed user_id=%s source=%s", user_id, source)
            src = source if source in ("live", "simulation") else "simulation"
            return _empty_portfolio(source=src)

    def _usable_positions(self, raw_positions: list[PortfolioPosition], user_id: int) -> list[PortfolioPosition]:
        """Позиции с валидным фондом (иначе Pydantic/цены дадут 500)."""
        out: list[PortfolioPosition] = []
        for p in raw_positions:
            if p.fund is None:
                logger.warning(
                    "portfolio: skip position id=%s user_id=%s (fund row missing)",
                    getattr(p, "id", "?"),
                    user_id,
                )
                continue
            try:
                FundRead.model_validate(p.fund)
            except Exception:
                logger.warning(
                    "portfolio: skip position id=%s user_id=%s (fund validation failed)",
                    p.id,
                    user_id,
                    exc_info=True,
                )
                continue
            out.append(p)
        return out

    def _build_portfolio(self, user_id: int) -> PortfolioRead:
        raw_positions = self._portfolio.list_positions(user_id)
        positions = self._usable_positions(raw_positions, user_id)

        categories = self._strategy.list_for_user(user_id)
        cat_by_id = {c.id: c for c in categories}

        total_invested = q_money(
            sum((to_decimal(p.invested_amount) for p in positions), Decimal("0"))
        )

        current_by_position: dict[int, Decimal] = {}
        total_current = Decimal("0")
        for p in positions:
            # Цена за шт. — q_price (микрошаг); q_money округляет до копеек и может обнулить мелкую цену → падение Pydantic current_price>0 и пустой портфель.
            unit = q_price(self._pricing.get_unit_price(p.fund))
            cur = q_money(Decimal(int(p.total_units)) * unit)
            current_by_position[int(p.id)] = cur
            total_current += cur
        total_current = q_money(total_current)

        current_by_category: dict[int, Decimal] = {}
        for p in positions:
            cid = int(p.category_id)
            current_by_category[cid] = current_by_category.get(cid, Decimal("0")) + current_by_position[int(p.id)]

        summaries: list[CategorySummary] = []
        for c in sorted(categories, key=lambda x: (x.sort_order, x.id)):
            cur_amt = q_money(current_by_category.get(c.id, Decimal("0")))
            cur_w = Decimal("0")
            if total_current > 0:
                cur_w = q_money(cur_amt / total_current * Decimal("100"))
            summaries.append(
                CategorySummary(
                    category_id=c.id,
                    category_name=c.name,
                    target_percent=to_decimal(c.target_percent),
                    current_weight_percent=cur_w,
                    current_amount=cur_amt,
                    invested_amount=q_money(
                        sum(
                            (
                                to_decimal(p.invested_amount)
                                for p in positions
                                if int(p.category_id) == c.id
                            ),
                            Decimal("0"),
                        )
                    ),
                )
            )

        pos_reads: list[PortfolioPositionRead] = []
        total_pnl = Decimal("0")
        for p in positions:
            cat = cat_by_id.get(int(p.category_id))
            cur_amt = current_by_position.get(int(p.id), Decimal("0"))
            cur_w = Decimal("0")
            if total_current > 0:
                cur_w = q_money(cur_amt / total_current * Decimal("100"))
            unit = q_price(self._pricing.get_unit_price(p.fund))
            inv = to_decimal(p.invested_amount)
            pnl = q_money(cur_amt - inv)
            total_pnl += pnl
            pnl_pct = q_money(pnl / inv * Decimal("100")) if inv > 0 else Decimal("0")
            raw_ts = getattr(p.fund, "last_price_updated_at", None)
            price_ts: datetime | None = raw_ts if isinstance(raw_ts, datetime) else None
            pos_reads.append(
                PortfolioPositionRead(
                    id=p.id,
                    user_id=p.user_id,
                    category_id=p.category_id,
                    fund_id=p.fund_id,
                    category_name=cat.name if cat else "",
                    total_lots=int(p.total_lots),
                    total_units=int(p.total_units),
                    invested_amount=inv,
                    average_buy_price=to_decimal(p.average_buy_price),
                    current_amount=cur_amt,
                    current_weight_percent=cur_w,
                    fund=FundRead.model_validate(p.fund),
                    current_price=unit,
                    quantity=int(p.total_units),
                    current_value=cur_amt,
                    invested_value=inv,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    last_price_updated_at=price_ts,
                )
            )
        total_pnl = q_money(total_pnl)
        total_pnl_pct = (
            q_money(total_pnl / total_invested * Decimal("100")) if total_invested > 0 else Decimal("0")
        )

        return PortfolioRead(
            source="simulation",
            total_invested_amount=total_invested,
            total_current_amount=total_current,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_pct,
            categories=summaries,
            positions=pos_reads,
        )

    def _build_portfolio_live(self, user_id: int) -> PortfolioRead:
        br = TinvestBrokerService(self._db, settings)
        account_id = br.resolve_account_id()

        categories = self._strategy.list_for_user(user_id)
        fund_to_cat: dict[int, tuple[int, str]] = {}
        for c in categories:
            if not c.is_active or c.fund_id is None:
                continue
            fid = int(c.fund_id)
            if fid not in fund_to_cat:
                fund_to_cat[fid] = (int(c.id), c.name)

        now = datetime.now(UTC)
        rows: list[dict] = []

        with tinvest_client(settings) as client:
            port = client.get_portfolio(account_id)
            for p in port.get("positions", []):
                uid = (str(p.get("instrumentUid") or "").strip())
                fg = (str(p.get("figi") or "").strip())
                fund_ent = self._funds.get_by_instrument_uid(uid) if uid else None
                if fund_ent is None and fg:
                    fund_ent = self._funds.get_by_figi(fg)
                if fund_ent is None:
                    logger.info("live portfolio: skip instrument without DB fund uid=%s figi=%s", uid, fg)
                    continue
                qty_dec = quotation_to_decimal(p.get("quantity"))
                units = int(qty_dec.to_integral_value(rounding=ROUND_FLOOR)) if qty_dec > 0 else 0
                if units < 1:
                    continue
                inv_unit = (
                    money_value_to_decimal(p.get("averagePositionPrice"))
                    if p.get("averagePositionPrice") is not None
                    else Decimal("0")
                )
                inv_unit = q_price(inv_unit)
                unit_cur = (
                    money_value_to_decimal(p.get("currentPrice")) if p.get("currentPrice") is not None else Decimal("0")
                )
                if unit_cur <= 0:
                    unit_cur = q_price(self._pricing.get_unit_price(fund_ent))
                else:
                    unit_cur = q_price(unit_cur)
                if unit_cur <= 0:
                    continue
                cur_amt = q_money(Decimal(units) * unit_cur)
                inv = q_money(Decimal(units) * inv_unit) if inv_unit > 0 else Decimal("0")
                cid, cname = fund_to_cat.get(int(fund_ent.id), (0, "Не в стратегии"))
                lot = max(int(fund_ent.lot), 1)
                pos_id = abs(hash((account_id, uid or fg, int(fund_ent.id)))) % 1_000_000_000 + 1
                rows.append(
                    {
                        "id": pos_id,
                        "category_id": cid,
                        "category_name": cname,
                        "fund": fund_ent,
                        "units": units,
                        "lots": units // lot,
                        "inv": inv,
                        "cur": cur_amt,
                        "unit": unit_cur,
                        "avg": inv_unit if inv_unit > 0 else unit_cur,
                    }
                )

        total_current = q_money(sum((r["cur"] for r in rows), Decimal("0")))
        total_invested = q_money(sum((r["inv"] for r in rows), Decimal("0")))

        current_by_category: dict[int, Decimal] = {}
        invested_by_category: dict[int, Decimal] = {}
        for r in rows:
            cid = int(r["category_id"])
            current_by_category[cid] = current_by_category.get(cid, Decimal("0")) + r["cur"]
            invested_by_category[cid] = invested_by_category.get(cid, Decimal("0")) + r["inv"]

        summaries: list[CategorySummary] = []
        for c in sorted(categories, key=lambda x: (x.sort_order, x.id)):
            cur_amt = q_money(current_by_category.get(c.id, Decimal("0")))
            cur_w = Decimal("0")
            if total_current > 0:
                cur_w = q_money(cur_amt / total_current * Decimal("100"))
            summaries.append(
                CategorySummary(
                    category_id=c.id,
                    category_name=c.name,
                    target_percent=to_decimal(c.target_percent),
                    current_weight_percent=cur_w,
                    current_amount=cur_amt,
                    invested_amount=q_money(invested_by_category.get(c.id, Decimal("0"))),
                )
            )

        pos_reads: list[PortfolioPositionRead] = []
        total_pnl = Decimal("0")
        for r in rows:
            cur_amt = r["cur"]
            inv = r["inv"]
            cur_w = q_money(cur_amt / total_current * Decimal("100")) if total_current > 0 else Decimal("0")
            pnl = q_money(cur_amt - inv)
            total_pnl += pnl
            pnl_pct = q_money(pnl / inv * Decimal("100")) if inv > 0 else Decimal("0")
            fund_ent = r["fund"]
            raw_ts = getattr(fund_ent, "last_price_updated_at", None)
            price_ts: datetime | None = raw_ts if isinstance(raw_ts, datetime) else None
            pos_reads.append(
                PortfolioPositionRead(
                    id=int(r["id"]),
                    user_id=user_id,
                    category_id=int(r["category_id"]),
                    fund_id=int(fund_ent.id),
                    category_name=str(r["category_name"]),
                    total_lots=int(r["lots"]),
                    total_units=int(r["units"]),
                    invested_amount=inv,
                    average_buy_price=r["avg"],
                    current_amount=cur_amt,
                    current_weight_percent=cur_w,
                    fund=FundRead.model_validate(fund_ent),
                    current_price=r["unit"],
                    quantity=int(r["units"]),
                    current_value=cur_amt,
                    invested_value=inv,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    last_price_updated_at=price_ts or now,
                )
            )

        total_pnl = q_money(total_pnl)
        total_pnl_pct = (
            q_money(total_pnl / total_invested * Decimal("100")) if total_invested > 0 else Decimal("0")
        )

        return PortfolioRead(
            source="live",
            total_invested_amount=total_invested,
            total_current_amount=total_current,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_pct,
            categories=summaries,
            positions=pos_reads,
        )
