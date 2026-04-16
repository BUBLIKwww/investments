from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def open_app_keyboard(web_app_url: str, *, backend_api_url: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=web_app_url),
            )
        ],
    ]
    if backend_api_url:
        rows.append([InlineKeyboardButton(text="Обновить цены (mock)", callback_data="refresh_prices")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
