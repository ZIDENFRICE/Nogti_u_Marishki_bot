"""Глобально глушим ошибки редактирования медиа-сообщений."""
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


class SafeEditMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "no text in the message to edit" in err or "message is not modified" in err:
                try:
                    await event.answer("⚠️ Обнови меню — нажми /start", show_alert=False)
                except Exception:
                    pass
                return
            raise
