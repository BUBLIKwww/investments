from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.money import q_money
from app.models.portfolio_position import PortfolioPosition


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_positions(self, user_id: int) -> list[PortfolioPosition]:
        stmt = (
            select(PortfolioPosition)
            .where(PortfolioPosition.user_id == user_id)
            .options(
                joinedload(PortfolioPosition.fund),
                joinedload(PortfolioPosition.category),
            )
            .order_by(PortfolioPosition.id.asc())
        )
        return list(self._db.execute(stmt).unique().scalars().all())

    def get_position(self, user_id: int, category_id: int, fund_id: int) -> PortfolioPosition | None:
        stmt = select(PortfolioPosition).where(
            PortfolioPosition.user_id == user_id,
            PortfolioPosition.category_id == category_id,
            PortfolioPosition.fund_id == fund_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def upsert_after_purchase(
        self,
        *,
        user_id: int,
        category_id: int,
        fund_id: int,
        purchased_units: int,
        purchased_lots: int,
        purchase_amount: Decimal,
    ) -> PortfolioPosition:
        purchase_amount_dec = q_money(purchase_amount)
        now = datetime.now(timezone.utc)
        pos = self.get_position(user_id, category_id, fund_id)
        if pos is None:
            avg = Decimal("0")
            if purchased_units > 0:
                avg = (purchase_amount_dec / Decimal(purchased_units)).quantize(Decimal("0.000001"))
            pos = PortfolioPosition(
                user_id=user_id,
                category_id=category_id,
                fund_id=fund_id,
                total_lots=purchased_lots,
                total_units=purchased_units,
                invested_amount=purchase_amount_dec,
                average_buy_price=avg,
                created_at=now,
                updated_at=now,
            )
            self._db.add(pos)
            self._db.flush()
            return pos

        new_units = int(pos.total_units) + int(purchased_units)
        new_invested = q_money(Decimal(str(pos.invested_amount)) + purchase_amount_dec)
        new_lots = int(pos.total_lots) + int(purchased_lots)
        if new_units <= 0:
            raise ValueError("Invalid units after purchase")
        new_avg = (new_invested / Decimal(new_units)).quantize(Decimal("0.000001"))
        pos.total_units = new_units
        pos.total_lots = new_lots
        pos.invested_amount = new_invested
        pos.average_buy_price = new_avg
        pos.updated_at = now
        self._db.flush()
        return pos
