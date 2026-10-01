import asyncio
import logging
import logging.handlers
import os

from aiogram.types import ErrorEvent
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import admin, booking, cancel, pagination, reviews, user
from middlewares.edit_error import SafeEditMiddleware
from services.scheduler import setup_scheduler
from middlewares.antiflood import AntiFloodMiddleware
from handlers import user, booking, admin, reviews, pagination, cancel, legal

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),                      # в терминал
        logging.handlers.RotatingFileHandler(
            "logs/bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        ),                                            # в файл
    ],
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main():
    await init_db()
    
    # 👇 ВРЕМЕННАЯ ПРОВЕРКА
    from sqlalchemy import text
    from database.db import async_session
    async with async_session() as s:
        res = await s.execute(text(
            "SELECT column_name, is_nullable, table_schema "
            "FROM information_schema.columns "
            "WHERE table_name = 'bookings' AND column_name = 'slot_id'"
        ))
        for row in res:
            print(f"🔍 CHECK: {row}")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # мидлварь — ДО роутеров
    dp.callback_query.middleware(SafeEditMiddleware())
    dp.callback_query.middleware(AntiFloodMiddleware(rate=0.5))

    @dp.errors()
    async def on_error(event: ErrorEvent):
        logging.exception(f"Ошибка в хендлере: {event.exception}")
        try:
            if event.update.callback_query:
                await event.update.callback_query.answer(
                    "⚠️ Ой, что-то пошло не так. Попробуй /start",
                    show_alert=True,
                )
            elif event.update.message:
                await event.update.message.answer("⚠️ Ошибка. Попробуй позже.")
        except Exception:
            pass
        return True

    dp.include_router(admin.router)
    dp.include_router(pagination.router)   # ← добавить
    dp.include_router(cancel.router)
    dp.include_router(legal.router)
    dp.include_router(reviews.router)
    dp.include_router(booking.router)
    dp.include_router(user.router)

    setup_scheduler(bot)

    print("Бот запущен ✅")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")


