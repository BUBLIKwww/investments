from fastapi import APIRouter

from app.api.routes import funds, portfolio, rebalance, strategy, topups, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])
api_router.include_router(funds.router, prefix="/funds", tags=["funds"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(topups.router, prefix="/topups", tags=["topups"])
api_router.include_router(rebalance.router, prefix="/rebalance", tags=["rebalance"])
