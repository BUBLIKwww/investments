from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fund import Fund
    from app.models.portfolio_position import PortfolioPosition
    from app.models.topup_item import TopupItem
    from app.models.user import User


class StrategyCategory(Base):
    __tablename__ = "strategy_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "sort_order", name="uq_strategy_category_user_sort"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    fund_id: Mapped[int] = mapped_column(ForeignKey("funds.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    target_percent: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    user: Mapped["User"] = relationship(back_populates="strategy_categories")
    fund: Mapped["Fund"] = relationship(back_populates="strategy_categories")
    positions: Mapped[list["PortfolioPosition"]] = relationship(back_populates="category")
    topup_items: Mapped[list["TopupItem"]] = relationship(back_populates="category")
