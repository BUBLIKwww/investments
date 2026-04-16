from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.strategy_category import StrategyCategory


class StrategyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user(self, user_id: int) -> list[StrategyCategory]:
        stmt = (
            select(StrategyCategory)
            .where(StrategyCategory.user_id == user_id)
            .options(joinedload(StrategyCategory.fund))
            .order_by(StrategyCategory.sort_order.asc(), StrategyCategory.id.asc())
        )
        return list(self._db.execute(stmt).unique().scalars().all())

    def get_by_id_for_user(self, user_id: int, category_id: int) -> StrategyCategory | None:
        stmt = (
            select(StrategyCategory)
            .where(StrategyCategory.user_id == user_id, StrategyCategory.id == category_id)
            .options(joinedload(StrategyCategory.fund))
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, category: StrategyCategory) -> StrategyCategory:
        self._db.add(category)
        self._db.flush()
        return category

    def delete(self, category: StrategyCategory) -> None:
        self._db.delete(category)
        self._db.flush()
