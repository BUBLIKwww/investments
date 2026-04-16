from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.rebalance import RebalanceRead
from app.services.rebalance_service import RebalanceService

router = APIRouter()


@router.get("", response_model=RebalanceRead)
def get_rebalance(user: CurrentUser, db: DbSession) -> RebalanceRead:
    return RebalanceService(db).get_rebalance(int(user.id))
