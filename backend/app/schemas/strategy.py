from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fund import FundRead


class StrategyCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    fund_id: int
    name: str
    target_percent: Decimal = Field(ge=0)
    sort_order: int
    is_active: bool
    fund: FundRead


class StrategyRead(BaseModel):
    categories: list[StrategyCategoryRead]


class StrategyCategoryUpdate(BaseModel):
    id: int | None = None
    name: str
    target_percent: Decimal = Field(ge=0)
    fund_id: int
    sort_order: int
    is_active: bool


class StrategyUpdate(BaseModel):
    categories: list[StrategyCategoryUpdate]
