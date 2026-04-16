from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import TopupMode


class TopupCalculateRequest(BaseModel):
    total_amount: Decimal = Field(gt=0)
    mode: TopupMode


class TopupItemResult(BaseModel):
    category_id: int
    category_name: str
    fund_id: int
    fund_name: str
    ticker: str
    target_percent: Decimal
    target_amount: Decimal
    price_used: Decimal
    lot_size: int
    purchased_lots: int
    purchased_units: int
    actual_allocated_amount: Decimal
    cash_remainder: Decimal


class TopupCalculateResponse(BaseModel):
    total_amount: Decimal
    mode: TopupMode
    items: list[TopupItemResult]
    total_allocated_amount: Decimal
    total_cash_remainder: Decimal


class TopupHistoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    fund_id: int
    target_amount: Decimal
    actual_allocated_amount: Decimal
    cash_remainder: Decimal
    price_used: Decimal
    lot_size: int
    purchased_lots: int
    purchased_units: int


class TopupHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    total_amount: Decimal
    mode: TopupMode

    @field_validator("mode", mode="before")
    @classmethod
    def _coerce_mode(cls, v: object) -> TopupMode:
        if isinstance(v, TopupMode):
            return v
        return TopupMode(str(v))
    total_allocated_amount: Decimal
    total_cash_remainder: Decimal
    created_at: datetime
    items: list[TopupHistoryItemRead]
