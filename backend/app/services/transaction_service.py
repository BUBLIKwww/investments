from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import TransactionOperationType
from app.domain.money import q_money, q_price
from app.models.investment_transaction import InvestmentTransaction
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    InvestmentTransactionCreate,
    InvestmentTransactionRead,
    InvestmentTransactionUpdate,
)
from app.services.portfolio_recalculation_service import PortfolioRecalculationService, simulate_buckets


class TransactionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = TransactionRepository(db)
        self._strategy = StrategyRepository(db)
        self._recalc = PortfolioRecalculationService(db)

    def _category_for_fund(self, user_id: int, fund_id: int) -> int:
        for c in self._strategy.list_for_user(user_id):
            if int(c.fund_id) == int(fund_id) and bool(c.is_active):
                return int(c.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Фонд не привязан к активной категории стратегии. Укажите category_id.",
        )

    def _merge_rows(
        self,
        user_id: int,
        *,
        exclude_transaction_id: int | None,
        extra: SimpleNamespace | None,
    ) -> list[object]:
        rows = [
            t
            for t in self._repo.list_for_user_chronological(user_id)
            if exclude_transaction_id is None or int(t.id) != int(exclude_transaction_id)
        ]
        if extra is not None:
            rows = list(rows) + [extra]
        return rows

    def _validate_chain(self, rows: list[object]) -> None:
        try:
            simulate_buckets(rows)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    def list(self, user_id: int) -> list[InvestmentTransactionRead]:
        return [InvestmentTransactionRead.model_validate(t) for t in self._repo.list_for_user(user_id)]

    def get(self, user_id: int, transaction_id: int) -> InvestmentTransactionRead:
        row = self._repo.get(user_id, transaction_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сделка не найдена")
        return InvestmentTransactionRead.model_validate(row)

    def create(self, user_id: int, payload: InvestmentTransactionCreate) -> InvestmentTransactionRead:
        if payload.category_id is not None:
            cat_id = int(payload.category_id)
        else:
            cat_id = self._category_for_fund(user_id, int(payload.fund_id))
        cat = self._strategy.get_by_id_for_user(user_id, cat_id)
        if cat is None or int(cat.fund_id) != int(payload.fund_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="category_id не соответствует fund_id",
            )

        now = datetime.now(timezone.utc)
        pending = SimpleNamespace(
            id=10**15,
            executed_at=payload.executed_at,
            category_id=cat_id,
            fund_id=int(payload.fund_id),
            operation_type=payload.operation_type.value,
            quantity=int(payload.quantity),
            total_amount=q_money(payload.total_amount),
        )
        rows = self._merge_rows(user_id, exclude_transaction_id=None, extra=pending)
        self._validate_chain(rows)

        entity = InvestmentTransaction(
            user_id=user_id,
            category_id=cat_id,
            fund_id=int(payload.fund_id),
            operation_type=payload.operation_type.value,
            quantity=int(payload.quantity),
            price_per_unit=q_price(payload.price_per_unit),
            total_amount=q_money(payload.total_amount),
            executed_at=payload.executed_at,
            note=payload.note,
            created_at=now,
            updated_at=now,
        )
        self._repo.add(entity)
        self._recalc.rebuild_positions_for_user(user_id)
        self._db.commit()
        self._db.refresh(entity)
        return InvestmentTransactionRead.model_validate(entity)

    def update(self, user_id: int, transaction_id: int, payload: InvestmentTransactionUpdate) -> InvestmentTransactionRead:
        row = self._repo.get(user_id, transaction_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сделка не найдена")

        new_fund_id = int(payload.fund_id) if payload.fund_id is not None else int(row.fund_id)
        new_cat_id = int(payload.category_id) if payload.category_id is not None else int(row.category_id)
        if payload.category_id is not None and payload.fund_id is None:
            cat = self._strategy.get_by_id_for_user(user_id, new_cat_id)
            if cat is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Категория не найдена")
            new_fund_id = int(cat.fund_id)
        if payload.fund_id is not None and payload.category_id is None:
            new_cat_id = self._category_for_fund(user_id, new_fund_id)

        cat = self._strategy.get_by_id_for_user(user_id, new_cat_id)
        if cat is None or int(cat.fund_id) != int(new_fund_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="category_id не соответствует fund_id",
            )

        merged = SimpleNamespace(
            id=10**15,
            executed_at=payload.executed_at if payload.executed_at is not None else row.executed_at,
            category_id=new_cat_id,
            fund_id=new_fund_id,
            operation_type=payload.operation_type.value if payload.operation_type else row.operation_type,
            quantity=int(payload.quantity) if payload.quantity is not None else int(row.quantity),
            total_amount=q_money(payload.total_amount) if payload.total_amount is not None else q_money(row.total_amount),
        )
        rows = self._merge_rows(user_id, exclude_transaction_id=transaction_id, extra=merged)
        self._validate_chain(rows)

        if payload.fund_id is not None:
            row.fund_id = int(payload.fund_id)
        if payload.category_id is not None:
            row.category_id = int(payload.category_id)
        elif payload.fund_id is not None:
            row.category_id = new_cat_id
        if payload.operation_type is not None:
            row.operation_type = payload.operation_type.value
        if payload.quantity is not None:
            row.quantity = int(payload.quantity)
        if payload.price_per_unit is not None:
            row.price_per_unit = q_price(payload.price_per_unit)
        if payload.total_amount is not None:
            row.total_amount = q_money(payload.total_amount)
        if payload.executed_at is not None:
            row.executed_at = payload.executed_at
        if payload.note is not None:
            row.note = payload.note
        row.updated_at = datetime.now(timezone.utc)
        self._db.flush()
        self._recalc.rebuild_positions_for_user(user_id)
        self._db.commit()
        self._db.refresh(row)
        return InvestmentTransactionRead.model_validate(row)

    def delete(self, user_id: int, transaction_id: int) -> None:
        row = self._repo.get(user_id, transaction_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сделка не найдена")
        self._repo.delete(row)
        self._recalc.rebuild_positions_for_user(user_id)
        self._db.commit()
