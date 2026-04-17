from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import TransactionOperationType
from app.models.investment_transaction import InvestmentTransaction
from app.models.topup_history import TopupHistory


class CashRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def sum_topups(self, user_id: int) -> Decimal:
        stmt = select(func.coalesce(func.sum(TopupHistory.total_amount), 0)).where(TopupHistory.user_id == user_id)
        raw = self._db.execute(stmt).scalar_one_or_none()
        return raw if isinstance(raw, Decimal) else Decimal(str(raw or 0))

    def sum_transaction_amounts(self, user_id: int, operation: str) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(InvestmentTransaction.total_amount), 0))
            .where(
                InvestmentTransaction.user_id == user_id,
                InvestmentTransaction.operation_type == operation,
            )
        )
        raw = self._db.execute(stmt).scalar_one_or_none()
        return raw if isinstance(raw, Decimal) else Decimal(str(raw or 0))

    def cash_balance(self, user_id: int) -> Decimal:
        """Пополнения − покупки + продажи (руб.)."""
        top = self.sum_topups(user_id)
        buys = self.sum_transaction_amounts(user_id, TransactionOperationType.BUY.value)
        sells = self.sum_transaction_amounts(user_id, TransactionOperationType.SELL.value)
        return top - buys + sells
