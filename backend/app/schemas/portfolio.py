from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fund import FundRead


class PortfolioPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category_id: int
    fund_id: int
    category_name: str
    total_lots: int = Field(ge=0)
    total_units: int = Field(ge=0)
    invested_amount: Decimal = Field(ge=0)
    average_buy_price: Decimal = Field(ge=0)
    current_amount: Decimal = Field(ge=0)
    current_weight_percent: Decimal = Field(ge=0)
    fund: FundRead


class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    target_percent: Decimal
    current_weight_percent: Decimal
    current_amount: Decimal
    invested_amount: Decimal


class PortfolioRead(BaseModel):
    total_invested_amount: Decimal
    total_current_amount: Decimal
    categories: list[CategorySummary]
    positions: list[PortfolioPositionRead]
