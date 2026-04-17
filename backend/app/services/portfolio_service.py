from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.money import q_money, to_decimal
from app.models.portfolio_position import PortfolioPosition
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.fund import FundRead
from app.schemas.portfolio import CategorySummary, PortfolioPositionRead, PortfolioRead
from app.services.pricing.db_provider import DbPricingProvider

logger = logging.getLogger(__name__)


def _empty_portfolio() -> PortfolioRead:
    return PortfolioRead(
        total_invested_amount=Decimal("0"),
        total_current_amount=Decimal("0"),
        total_pnl=Decimal("0"),
        total_pnl_percent=Decimal("0"),
        categories=[],
        positions=[],
    )


class PortfolioService:
    def __init__(self, db: Session) -> None:
        self._portfolio = PortfolioRepository(db)
        self._strategy = StrategyRepository(db)
        self._pricing = DbPricingProvider()

    def get_portfolio(self, user_id: int) -> PortfolioRead:
        try:
            return self._build_portfolio(user_id)
        except Exception:
            logger.exception("get_portfolio failed user_id=%s; returning empty portfolio", user_id)
            return _empty_portfolio()

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

        total_invested = q_money(sum(to_decimal(p.invested_amount) for p in positions))

        current_by_position: dict[int, Decimal] = {}
        total_current = Decimal("0")
        for p in positions:
            unit = q_money(self._pricing.get_unit_price(p.fund))
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
                        sum(to_decimal(p.invested_amount) for p in positions if int(p.category_id) == c.id)
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
            unit = q_money(self._pricing.get_unit_price(p.fund))
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
            total_invested_amount=total_invested,
            total_current_amount=total_current,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_pct,
            categories=summaries,
            positions=pos_reads,
        )
