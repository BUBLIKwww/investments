from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundRead, FundsPricesRefreshResponse
from app.services.pricing_service import PricingService

router = APIRouter()


@router.get("", response_model=list[FundRead])
def list_funds(db: DbSession) -> list[FundRead]:
    funds = FundRepository(db).list_active()
    return [FundRead.model_validate(f) for f in funds]


@router.post("/refresh-prices", response_model=FundsPricesRefreshResponse)
def refresh_fund_prices(db: DbSession) -> FundsPricesRefreshResponse:
    funds = PricingService(db).refresh_prices()
    return FundsPricesRefreshResponse(updated=len(funds), funds=funds)


@router.get("/{fund_id}", response_model=FundRead)
def get_fund(fund_id: int, db: DbSession) -> FundRead:
    fund = FundRepository(db).get_by_id(fund_id)
    if fund is None or not fund.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found")
    return FundRead.model_validate(fund)
