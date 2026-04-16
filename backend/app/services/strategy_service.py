from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.portfolio_position import PortfolioPosition
from app.models.strategy_category import StrategyCategory
from app.repositories.fund_repository import FundRepository
from app.repositories.strategy_repository import StrategyRepository
from app.schemas.strategy import StrategyCategoryRead, StrategyRead, StrategyUpdate


class StrategyService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._strategy = StrategyRepository(db)
        self._funds = FundRepository(db)

    def get_strategy(self, user_id: int) -> StrategyRead:
        categories = self._strategy.list_for_user(user_id)
        return StrategyRead(categories=[StrategyCategoryRead.model_validate(c) for c in categories])

    def update_strategy(self, user_id: int, payload: StrategyUpdate) -> StrategyRead:
        self._validate_update(payload)

        existing = {c.id: c for c in self._strategy.list_for_user(user_id)}
        incoming_ids = {c.id for c in payload.categories if c.id is not None}

        for cid, row in list(existing.items()):
            if cid in incoming_ids:
                continue
            count = self._db.scalar(
                select(func.count())
                .select_from(PortfolioPosition)
                .where(
                    PortfolioPosition.user_id == user_id,
                    PortfolioPosition.category_id == cid,
                )
            )
            if int(count or 0) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot delete strategy category {cid}: portfolio positions exist",
                )
            self._strategy.delete(row)
            existing.pop(cid, None)

        for item in sorted(payload.categories, key=lambda x: x.sort_order):
            fund = self._funds.get_by_id(item.fund_id)
            if fund is None or not fund.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid fund_id")

            if item.id is None:
                self._strategy.add(
                    StrategyCategory(
                        user_id=user_id,
                        fund_id=item.fund_id,
                        name=item.name,
                        target_percent=item.target_percent,
                        sort_order=item.sort_order,
                        is_active=item.is_active,
                    )
                )
                continue

            row = existing.get(item.id)
            if row is None or row.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown category id")
            row.name = item.name
            row.target_percent = item.target_percent
            row.fund_id = item.fund_id
            row.sort_order = item.sort_order
            row.is_active = item.is_active

        self._db.commit()
        return self.get_strategy(user_id)

    def _validate_update(self, payload: StrategyUpdate) -> None:
        if not payload.categories:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="categories must not be empty")

        for c in payload.categories:
            if c.target_percent < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_percent must be >= 0")

        active_sum = sum((c.target_percent for c in payload.categories if c.is_active), start=Decimal("0"))
        if active_sum != Decimal("100"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sum of target_percent for active categories must be exactly 100",
            )
