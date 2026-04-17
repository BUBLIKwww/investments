from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.core.config import settings
from app.repositories.fund_repository import FundRepository
from app.schemas.fund import FundAddRequest, FundRead, FundSearchResult, FundsPricesRefreshResponse
from app.services.pricing_service import PricingService
from app.services.tinvest_funds_service import TinvestFundsService

router = APIRouter()


@router.get("", response_model=list[FundRead])
def list_funds(db: DbSession) -> list[FundRead]:
    funds = FundRepository(db).list_active()
    return [FundRead.model_validate(f) for f in funds]


@router.get("/search", response_model=list[FundSearchResult])
def search_funds(
    db: DbSession,
    q: str = Query(..., alias="query", min_length=2, max_length=120, description="Строка поиска (FindInstrument)"),
    limit: int = Query(15, ge=1, le=25),
) -> list[FundSearchResult]:
    _ = db
    return TinvestFundsService(db, settings).search_instruments(q, limit=limit)


@router.post("/refresh-prices", response_model=FundsPricesRefreshResponse)
def refresh_fund_prices(db: DbSession) -> FundsPricesRefreshResponse:
    return PricingService(db, settings).refresh_prices()


@router.post("/add", response_model=FundRead)
def add_fund(payload: FundAddRequest, db: DbSession) -> FundRead:
    return TinvestFundsService(db, settings).add_fund(payload)


@router.get("/{fund_id}", response_model=FundRead)
def get_fund(fund_id: int, db: DbSession) -> FundRead:
    fund = FundRepository(db).get_by_id(fund_id)
    if fund is None or not fund.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found")
    return FundRead.model_validate(fund)
