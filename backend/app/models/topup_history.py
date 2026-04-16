from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.topup_item import TopupItem
    from app.models.user import User


class TopupHistory(Base):
    __tablename__ = "topup_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    total_allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_cash_remainder: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="topups")
    items: Mapped[list["TopupItem"]] = relationship(back_populates="topup", cascade="all, delete-orphan")
