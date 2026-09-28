import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

REMINDER_HOURS = int(os.getenv("REMINDER_HOURS", "3"))

# Neon PostgreSQL — берётся из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # убираем ?sslmode=require из URL — asyncpg его не понимает
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?")[0]

    # заменяем postgresql:// на postgresql+asyncpg://
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    DB_URL = DATABASE_URL
else:
    DB_URL = "sqlite+aiosqlite:///data/bot.db"

# === Информация о мастере / салоне ===
MASTER_NAME = "Марина"
MASTER_ABOUT = (
    "Мастер ногтевого сервиса с опытом более 5 лет.\n"
    "Работаю только с качественными материалами 💎\n"
    "Индивидуальный подход к каждому клиенту 💅"
)
SALON_ADDRESS = "г. Москва, ул. Примерная, д. 10, каб. 5"
SALON_PHONE = "+7 (999) 123-45-67"

# === Часовой пояс ===
MSK = timezone(timedelta(hours=3))


def now() -> datetime:
    """Текущее время в МСК (с таймзоной)."""
    return datetime.now(MSK)


def today():
    """Сегодняшняя дата в МСК."""
    return now().date()
