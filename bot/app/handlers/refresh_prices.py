import asyncio
import json
import urllib.error
import urllib.request

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings

router = Router()


def _post_refresh_sync(base_url: str) -> tuple[int, str]:
    url = f"{base_url.rstrip('/')}/api/v1/funds/refresh-prices"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return int(resp.status), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Сеть недоступна ({e.reason!s}).") from e


@router.callback_query(F.data == "refresh_prices")
async def on_refresh_prices(callback: CallbackQuery) -> None:
    settings = get_settings()
    base = settings.BACKEND_API_URL
    if not base:
        await callback.answer("URL backend не задан в .env", show_alert=True)
        return
    await callback.answer("Обновляем цены…")
    try:
        status, body = await asyncio.to_thread(_post_refresh_sync, base)
    except RuntimeError as exc:
        if callback.message:
            await callback.message.answer(str(exc))
        return
    if status == 200:
        try:
            parsed = json.loads(body)
            n = int(parsed.get("updated", 0))
        except (TypeError, ValueError, json.JSONDecodeError):
            n = 0
        if callback.message:
            await callback.message.answer(f"Цены обновлены (mock): инструментов — {n}.")
    else:
        short = body[:400] if body else ""
        if callback.message:
            await callback.message.answer(f"Ошибка backend ({status}): {short}")
