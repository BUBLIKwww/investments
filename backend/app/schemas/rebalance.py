from decimal import Decimal

from pydantic import BaseModel, Field


class RebalanceCategoryRead(BaseModel):
    category_id: int
    category_name: str
    fund_ticker: str
    target_weight_percent: Decimal = Field(ge=0)
    current_weight_percent: Decimal = Field(ge=0)
    delta_percent: Decimal
    current_amount: Decimal


class RebalanceRead(BaseModel):
    categories: list[RebalanceCategoryRead]
    underweight: list[int]
    overweight: list[int]
