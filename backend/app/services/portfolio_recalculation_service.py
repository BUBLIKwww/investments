"""Пересчёт позиций портфеля из журнала сделок (investment_transactions)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import TransactionOperationType
from app.domain.money import q_money, q_price
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_position import PortfolioPosition
from app.models.user import User
from app.repositories.fund_repository import FundRepository
from app.repositories.transaction_repository import TransactionRepository


@dataclass
class _Bucket:
    units: int = 0
    invested: Decimal = Decimal("0")
    avg_price: Decimal = Decimal("0")


def _apply_transaction(bucket: _Bucket, op: str, qty: int, total_amount: Decimal) -> None:
    total_amount = q_money(total_amount)
    if op == TransactionOperationType.BUY.value:
        new_units = bucket.units + qty
        new_inv = q_money(bucket.invested + total_amount)
        bucket.units = new_units
        bucket.invested = new_inv
        bucket.avg_price = q_price(new_inv / Decimal(new_units)) if new_units else Decimal("0")
        return
    if op == TransactionOperationType.SELL.value:
        if qty > bucket.units:
            msg = f"Нельзя продать {qty} шт.: в позиции только {bucket.units} шт."
            raise ValueError(msg)
        removed = q_money(Decimal(qty) * bucket.avg_price)
        new_units = bucket.units - qty
        new_inv = q_money(bucket.invested - removed)
        bucket.units = new_units
        bucket.invested = new_inv
        if new_units <= 0:
            bucket.units = 0
            bucket.invested = Decimal("0")
            bucket.avg_price = Decimal("0")
        else:
            bucket.avg_price = q_price(new_inv / Decimal(new_units))
        return
    msg = f"Неизвестный тип операции: {op}"
    raise ValueError(msg)


def simulate_buckets(transactions: Sequence[Any]) -> dict[tuple[int, int], _Bucket]:
    ordered = sorted(
        transactions,
        key=lambda t: (t.executed_at, getattr(t, "id", None) if getattr(t, "id", None) is not None else 10**15),
    )
    buckets: dict[tuple[int, int], _Bucket] = {}
    for t in ordered:
        key = (int(t.category_id), int(t.fund_id))
        buckets.setdefault(key, _Bucket())
        _apply_transaction(buckets[key], t.operation_type, int(t.quantity), Decimal(str(t.total_amount)))
    return buckets


class PortfolioRecalculationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._tx = TransactionRepository(db)
        self._funds = FundRepository(db)

    def rebuild_positions_for_user(self, user_id: int) -> None:
        self._db.execute(delete(PortfolioPosition).where(PortfolioPosition.user_id == user_id))
        self._db.flush()
        txs = self._tx.list_for_user_chronological(user_id)
        if not txs:
            return
        fund_ids = {int(t.fund_id) for t in txs}
        fund_by_id = self._funds.get_by_ids(list(fund_ids))
        buckets = simulate_buckets(txs)
        now = datetime.now(timezone.utc)
        for (category_id, fund_id), st in buckets.items():
            if st.units <= 0:
                continue
            fund = fund_by_id.get(int(fund_id))
            if fund is None:
                continue
            lot = max(int(fund.lot), 1)
            total_lots = st.units // lot
            pos = PortfolioPosition(
                user_id=user_id,
                category_id=category_id,
                fund_id=fund_id,
                total_lots=int(total_lots),
                total_units=int(st.units),
                invested_amount=q_money(st.invested),
                average_buy_price=q_price(st.avg_price) if st.units else Decimal("0"),
                created_at=now,
                updated_at=now,
            )
            self._db.add(pos)
        self._db.flush()

    def rebuild_all_users_with_transactions(self) -> None:
        stmt = select(InvestmentTransaction.user_id).distinct()
        ids = [int(x) for x in self._db.scalars(stmt).all()]
        for uid in ids:
            self.rebuild_positions_for_user(uid)

    def rebuild_positions_for_all_users(self) -> None:
        """Пересчитать позиции у каждого пользователя (без сделок — пустой портфель)."""
        stmt = select(User.id)
        for uid in self._db.scalars(stmt).all():
            self.rebuild_positions_for_user(int(uid))
