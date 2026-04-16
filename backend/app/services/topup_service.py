from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import TopupMode, TransactionOperationType
from app.domain.money import q_money, q_price, to_decimal
from app.models.investment_transaction import InvestmentTransaction
from app.models.topup_history import TopupHistory
from app.models.topup_item import TopupItem
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.topup_repository import TopupRepository
from app.schemas.topup import TopupCalculateRequest, TopupCalculateResponse
from app.services.allocation_service import calculate_topup_allocation
from app.services.portfolio_recalculation_service import PortfolioRecalculationService
from app.services.pricing.db_provider import DbPricingProvider


class TopupService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._strategy = StrategyRepository(db)
        self._portfolio = PortfolioRepository(db)
        self._topups = TopupRepository(db)
        self._pricing = DbPricingProvider()
        self._recalc = PortfolioRecalculationService(db)

    def calculate(self, user_id: int, payload: TopupCalculateRequest) -> TopupCalculateResponse:
        categories = self._strategy.list_for_user(user_id)
        positions = self._portfolio.list_positions(user_id)
        return calculate_topup_allocation(
            total_amount=payload.total_amount,
            mode=payload.mode,
            ordered_categories=categories,
            positions=positions,
            pricing=self._pricing,
        )

    def execute(self, user_id: int, payload: TopupCalculateRequest) -> TopupCalculateResponse:
        calc = self.calculate(user_id, payload)

        topup = TopupHistory(
            user_id=user_id,
            total_amount=q_money(calc.total_amount),
            mode=calc.mode.value,
            total_allocated_amount=q_money(calc.total_allocated_amount),
            total_cash_remainder=q_money(calc.total_cash_remainder),
        )
        items: list[TopupItem] = []
        for row in calc.items:
            items.append(
                TopupItem(
                    category_id=row.category_id,
                    fund_id=row.fund_id,
                    target_amount=q_money(row.target_amount),
                    actual_allocated_amount=q_money(row.actual_allocated_amount),
                    cash_remainder=q_money(row.cash_remainder),
                    price_used=q_price(to_decimal(row.price_used)),
                    lot_size=int(row.lot_size),
                    purchased_lots=int(row.purchased_lots),
                    purchased_units=int(row.purchased_units),
                )
            )

        self._topups.create_topup(topup, items)

        executed_at = topup.created_at or datetime.now(timezone.utc)
        if executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=timezone.utc)

        for row in calc.items:
            if int(row.purchased_units) <= 0:
                continue
            self._db.add(
                InvestmentTransaction(
                    user_id=user_id,
                    category_id=int(row.category_id),
                    fund_id=int(row.fund_id),
                    operation_type=TransactionOperationType.BUY.value,
                    quantity=int(row.purchased_units),
                    price_per_unit=q_price(to_decimal(row.price_used)),
                    total_amount=q_money(row.actual_allocated_amount),
                    executed_at=executed_at,
                    note=f"Пополнение #{topup.id}",
                )
            )

        self._recalc.rebuild_positions_for_user(user_id)
        self._db.commit()
        return calc
