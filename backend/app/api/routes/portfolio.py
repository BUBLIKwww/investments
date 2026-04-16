from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.portfolio import PortfolioRead
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("", response_model=PortfolioRead)
def get_portfolio(user: CurrentUser, db: DbSession) -> PortfolioRead:
    return PortfolioService(db).get_portfolio(int(user.id))
