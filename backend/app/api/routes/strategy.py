from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.strategy import StrategyRead, StrategyUpdate
from app.services.strategy_service import StrategyService

router = APIRouter()


@router.get("", response_model=StrategyRead)
def get_strategy(user: CurrentUser, db: DbSession) -> StrategyRead:
    return StrategyService(db).get_strategy(int(user.id))


@router.put("", response_model=StrategyRead)
def put_strategy(user: CurrentUser, db: DbSession, payload: StrategyUpdate) -> StrategyRead:
    return StrategyService(db).update_strategy(int(user.id), payload)
