from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund
    from app.models.strategy_category import StrategyCategory
    from app.models.user import User


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "fund_id", name="uq_portfolio_user_category_fund"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("strategy_categories.id"), index=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    total_lots: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_units: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    average_buy_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="portfolio_positions")
    category: Mapped["StrategyCategory"] = relationship(back_populates="positions")
    fund: Mapped["Fund"] = relationship(back_populates="positions")
