from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from config import ADMIN_IDS, REMINDER_HOURS, now
from database.db import async_session, get_bookings_tomorrow
from database.models import Booking
from utils.texts import DIVIDER, fmt_dt

scheduler = AsyncIOScheduler()


async def check_client_reminders(bot):
    """Клиенту — за N часов до визита."""
    current = now()
    target = current + timedelta(hours=REMINDER_HOURS)

    async with async_session() as s:
        res = await s.execute(
            select(Booking).where(
                Booking.status == "active",
                Booking.reminder_sent.is_(False),
            )
        )
        bookings = list(res.scalars().all())

        for b in bookings:
            if current <= b.slot.dt <= target:
                try:
                    await bot.send_message(
                        b.user_id,
                        f"⏰ <b>Напоминание о визите</b>\n"
                        f"{DIVIDER}\n"
                        f"💅 {b.service.title}\n"
                        f"🗓 {fmt_dt(b.slot.dt)}\n"
                        f"💰 {b.service.price} ₽\n\n"
                        f"Жду тебя! 💖",
                    )
                    b.reminder_sent = True
                except Exception:
                    b.reminder_sent = True  # если бот заблокирован
        await s.commit()


async def remind_admin_morning(bot):
    """Каждое утро админам — сводка записей на сегодня."""
    bookings = await get_bookings_tomorrow()
    if not bookings:
        return
    text = f"🌅 <b>Записи на сегодня</b> ({len(bookings)})\n{DIVIDER}\n\n"
    for b in bookings:
        text += (
            f"🕐 {b.slot.dt.strftime('%H:%M')} — <b>{b.client_name}</b>\n"
            f"   💅 {b.service.title}\n"
            f"   📞 {b.client_phone}\n\n"
        )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


def setup_scheduler(bot):
    # каждый 15 минут проверяем напоминания
    scheduler.add_job(check_client_reminders, "interval", minutes=15, args=[bot])
    # каждый день в 09:00 — сводка админам
    scheduler.add_job(remind_admin_morning, "cron", hour=9, minute=0, args=[bot])
    scheduler.start()
