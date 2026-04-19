"""Схемы live‑ордеров (покупка/продажа фонда через T‑Invest)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderRequest(BaseModel):
    fund_id: int = Field(description="ID фонда из каталога backend")
    quantity: int = Field(ge=1, description="Количество бумаг (штук); должно быть кратно lot фонда")


class OrderResult(BaseModel):
    success: bool
    broker_order_id: str | None = None
    execution_status: str | None = None
    message: str | None = None
    transaction_id: int | None = None
    account_id: str
    fund_id: int
    quantity: int
    lots: int
    action: str


class OrderHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fund_id: int
    category_id: int
    operation_type: str
    quantity: int
    price_per_unit: Decimal
    total_amount: Decimal
    executed_at: datetime
    note: str | None = None
    broker_order_id: str | None = None
    execution_status: str | None = None
