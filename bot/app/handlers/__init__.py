from aiogram import Router

from app.handlers.refresh_prices import router as refresh_prices_router
from app.handlers.start import router as start_router


def setup_handlers(root: Router) -> None:
    root.include_router(start_router)
    root.include_router(refresh_prices_router)
