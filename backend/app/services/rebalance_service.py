from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.money import q_money, to_decimal
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.rebalance import RebalanceCategoryRead, RebalanceRead
from app.services.pricing.db_provider import DbPricingProvider


class RebalanceService:
    def __init__(self, db: Session) -> None:
        self._portfolio = PortfolioRepository(db)
        self._strategy = StrategyRepository(db)
        self._pricing = DbPricingProvider()

    def get_rebalance(self, user_id: int) -> RebalanceRead:
        positions = self._portfolio.list_positions(user_id)
        categories = self._strategy.list_for_user(user_id)

        total_current = Decimal("0")
        current_by_category: dict[int, Decimal] = {}
        ticker_by_fund: dict[int, str] = {}
        for p in positions:
            if p.fund is None:
                continue
            ticker_by_fund[int(p.fund.id)] = p.fund.ticker
            unit = q_money(self._pricing.get_unit_price(p.fund))
            cur = q_money(Decimal(int(p.total_units)) * unit)
            cid = int(p.category_id)
            current_by_category[cid] = current_by_category.get(cid, Decimal("0")) + cur
            total_current += cur
        total_current = q_money(total_current)

        rows: list[RebalanceCategoryRead] = []
        under: list[int] = []
        over: list[int] = []

        for c in sorted(categories, key=lambda x: (x.sort_order, x.id)):
            if not c.is_active:
                continue
            cur_amt = q_money(current_by_category.get(c.id, Decimal("0")))
            cur_w = Decimal("0")
            if total_current > 0:
                cur_w = q_money(cur_amt / total_current * Decimal("100"))
            tgt_w = q_money(to_decimal(c.target_percent))
            delta = q_money(cur_w - tgt_w)
            rows.append(
                RebalanceCategoryRead(
                    category_id=c.id,
                    category_name=c.name,
                    fund_ticker=ticker_by_fund.get(int(c.fund_id), c.fund.ticker if c.fund else ""),
                    target_weight_percent=tgt_w,
                    current_weight_percent=cur_w,
                    delta_percent=delta,
                    current_amount=cur_amt,
                )
            )
            if tgt_w > cur_w:
                under.append(c.id)
            elif cur_w > tgt_w:
                over.append(c.id)

        return RebalanceRead(categories=rows, underweight=under, overweight=over)
