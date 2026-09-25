"""Тесты БД — проверяют логику без Telegram."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# подменяем БД на тестовую
os.environ["DB_URL"] = "sqlite+aiosqlite:///data/test.db"

from datetime import datetime, timedelta
from database.db import (
    init_db, get_or_create_user, add_service, get_active_services,
    add_slot, get_free_slots, create_booking, get_user_bookings,
    cancel_booking, get_stats, async_session,
)
from database.models import Base


async def reset_db():
    async with async_session() as s:
        pass
    from database.db import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()


async def test_full_flow():
    print("🧪 Тест: полный цикл записи")
    await reset_db()

    # 1. Создаём юзера
    user = await get_or_create_user(111, "test", "Тест Тестов")
    assert user.id == 111
    print("  ✅ Пользователь создан")

    # 2. Создаём услугу
    svc = await add_service("Маникюр", 1500, 60)
    assert svc.price == 1500
    print("  ✅ Услуга создана")

    # 3. Создаём слот
    dt = datetime.now() + timedelta(days=1)
    slot = await add_slot(dt)
    assert slot.is_booked is False
    print("  ✅ Слот создан")

    # 4. Свободные слоты
    free = await get_free_slots()
    assert len(free) == 1
    print("  ✅ Свободные слоты найдены")

    # 5. Создаём запись
    booking = await create_booking(111, svc.id, slot.id, "Тест", "+7999", "френч")
    assert booking is not None
    assert booking.client_name == "Тест"
    print("  ✅ Запись создана")

    # 6. Слот занят
    from database.db import get_slot
    slot2 = await get_slot(slot.id)
    assert slot2.is_booked is True
    print("  ✅ Слот помечен занятым")

    # 7. Мои записи
    my = await get_user_bookings(111)
    assert len(my) == 1
    assert my[0].service.title == "Маникюр"   # ← проверка подгрузки связи
    assert my[0].slot.dt == dt                 # ← проверка подгрузки связи
    print("  ✅ Мои записи возвращаются со связями")

    # 8. Двойное бронирование
    booking2 = await create_booking(111, svc.id, slot.id, "Другой", "+7888")
    assert booking2 is None
    print("  ✅ Повторное бронирование запрещено")

    # 9. Отмена
    cancelled = await cancel_booking(booking.id)
    assert cancelled.status == "cancelled"
    slot3 = await get_slot(slot.id)
    assert slot3.is_booked is False
    print("  ✅ Отмена работает")

    # 10. Статистика
    stats = await get_stats()
    assert stats["total_users"] == 1
    print("  ✅ Статистика корректна")

    print("🎉 Все тесты пройдены!\n")


async def main():
    await test_full_flow()


if __name__ == "__main__":
    asyncio.run(main())