from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.investment_transaction import InvestmentTransaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user(self, user_id: int) -> list[InvestmentTransaction]:
        stmt = (
            select(InvestmentTransaction)
            .where(InvestmentTransaction.user_id == user_id)
            .options(
                joinedload(InvestmentTransaction.fund),
                joinedload(InvestmentTransaction.category),
            )
            .order_by(InvestmentTransaction.executed_at.desc(), InvestmentTransaction.id.desc())
        )
        return list(self._db.execute(stmt).unique().scalars().all())

    def list_for_user_chronological(self, user_id: int) -> list[InvestmentTransaction]:
        stmt = (
            select(InvestmentTransaction)
            .where(InvestmentTransaction.user_id == user_id)
            .order_by(InvestmentTransaction.executed_at.asc(), InvestmentTransaction.id.asc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def get(self, user_id: int, transaction_id: int) -> InvestmentTransaction | None:
        stmt = select(InvestmentTransaction).where(
            InvestmentTransaction.user_id == user_id,
            InvestmentTransaction.id == transaction_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, row: InvestmentTransaction) -> InvestmentTransaction:
        self._db.add(row)
        self._db.flush()
        self._db.refresh(row)
        return row

    def delete(self, row: InvestmentTransaction) -> None:
        self._db.delete(row)
        self._db.flush()
