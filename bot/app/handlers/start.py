from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import get_settings
from app.keyboards.main import open_app_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    settings = get_settings()
    text = (
        "Привет! Я помогаю вести учёт инвестиций: стратегия по категориям, пополнения с учётом лотов, "
        "портфель и подсказки по ребалансу.\n\n"
        "Открой мини-приложение — там весь сценарий в удобном интерфейсе."
    )
    await message.answer(
        text,
        reply_markup=open_app_keyboard(settings.MINI_APP_URL, backend_api_url=settings.BACKEND_API_URL),
    )
