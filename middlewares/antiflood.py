"""Простой антифлуд — не более 1 колбэка в 0.5 сек."""
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5):
        self.rate = rate
        self.last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        uid = event.from_user.id
        now = time.time()
        if now - self.last.get(uid, 0) < self.rate:
            await event.answer("⏳ Слишком быстро", show_alert=False)
            return
        self.last[uid] = now
        return await handler(event, data)