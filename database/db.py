import os
from datetime import datetime, timedelta
from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from config import DB_URL, MSK, now, today
from database.models import Base, Booking, Broadcast, Review, Service, Slot, User, PortfolioPhoto

os.makedirs("data", exist_ok=True)

engine = create_async_engine(DB_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)



async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ================= USERS =================
async def get_or_create_user(tg_id: int, username: str | None, full_name: str | None) -> User:
    async with async_session() as s:
        user = await s.get(User, tg_id)
        if not user:
            user = User(id=tg_id, username=username, full_name=full_name)
            s.add(user)
            await s.commit()
        else:
            if username and user.username != username:
                user.username = username
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            await s.commit()
        return user


async def get_all_users() -> list[User]:
    async with async_session() as s:
        res = await s.execute(select(User).order_by(User.created_at.desc()))
        return list(res.scalars().all())


async def get_user(tg_id: int) -> User | None:
    async with async_session() as s:
        return await s.get(User, tg_id)


async def count_users() -> int:
    async with async_session() as s:
        res = await s.execute(select(func.count(User.id)))
        return res.scalar_one()


# ================= SERVICES =================
async def get_active_services() -> list[Service]:
    async with async_session() as s:
        res = await s.execute(
            select(Service).where(Service.is_active.is_(True)).order_by(Service.id)
        )
        return list(res.scalars().all())


async def get_all_services() -> list[Service]:
    async with async_session() as s:
        res = await s.execute(select(Service).order_by(Service.id))
        return list(res.scalars().all())


async def get_service(service_id: int) -> Service | None:
    async with async_session() as s:
        return await s.get(Service, service_id)


async def add_service(title: str, price: int, duration_min: int,
                      description: str | None = None) -> Service:
    async with async_session() as s:
        svc = Service(title=title, price=price, duration_min=duration_min, description=description)
        s.add(svc)
        await s.commit()
        await s.refresh(svc)
        return svc


async def delete_service(service_id: int) -> tuple[bool, str]:
    """Удалить услугу. Нельзя, если есть активные записи."""
    async with async_session() as s:
        svc = await s.get(Service, service_id)
        if not svc:
            return False, "Услуга не найдена"

        res = await s.execute(
            select(Booking).where(
                Booking.service_id == service_id,
                Booking.status == "active",
            )
        )
        if res.scalar_one_or_none():
            return False, "На эту услугу есть активные записи. Сначала отмени их."

        await s.delete(svc)
        await s.commit()
        return True, "Услуга удалена"


# ================= SLOTS =================
async def get_free_slots() -> list[Slot]:
    async with async_session() as s:
        res = await s.execute(
            select(Slot)
            .where(Slot.is_booked.is_(False), Slot.dt >= now())
            .order_by(Slot.dt)
        )
        return list(res.scalars().all())


async def get_all_future_slots() -> list[Slot]:
    async with async_session() as s:
        res = await s.execute(
            select(Slot).where(Slot.dt >= now()).order_by(Slot.dt)
        )
        return list(res.scalars().all())


async def get_slot(slot_id: int) -> Slot | None:
    async with async_session() as s:
        return await s.get(Slot, slot_id)


async def add_slot(dt: datetime) -> Slot:
    async with async_session() as s:
        slot = Slot(dt=dt)
        s.add(slot)
        await s.commit()
        await s.refresh(slot)
        return slot


async def add_slots_bulk(dts: list[datetime]) -> int:
    async with async_session() as s:
        for dt in dts:
            s.add(Slot(dt=dt))
        await s.commit()
        return len(dts)


async def delete_slot(slot_id: int, force: bool = False) -> dict:
    async with async_session() as s:
        slot = await s.get(Slot, slot_id)
        if not slot:
            return {"deleted": False, "had_booking": False,
                    "booking_id": None, "user_id": None, "dt": None}

        result = {
            "deleted": False,
            "had_booking": slot.is_booked,
            "booking_id": None,
            "user_id": None,
            "dt": slot.dt,
        }

        # 1. Находим ВСЕ записи на этот слот
        res = await s.execute(
            select(Booking).where(Booking.slot_id == slot_id)
        )
        bookings = res.scalars().all()

        # 2. Обнуляем slot_id у всех записей через raw SQL (в обход ORM)
        from sqlalchemy import text
        await s.execute(
            text("UPDATE bookings SET slot_id = NULL WHERE slot_id = :sid"),
            {"sid": slot_id}
        )

        # 3. Запоминаем отменённые записи для уведомления
        for booking in bookings:
            if booking.status == "active":
                result["booking_id"] = booking.id
                result["user_id"] = booking.user_id
                result["had_booking"] = True

        # 4. Отменяем активные записи
        await s.execute(
            text("UPDATE bookings SET status = 'cancelled' "
                 "WHERE slot_id IS NULL AND status = 'active' AND id = ANY(:ids)"),
            {"ids": [b.id for b in bookings if b.status == "active"] or [0]}
        )

        # 5. Удаляем слот
        await s.execute(
            text("DELETE FROM slots WHERE id = :sid"),
            {"sid": slot_id}
        )

        await s.commit()
        result["deleted"] = True
        return result
            


# ================= BOOKINGS =================
async def create_booking(user_id: int, service_id: int, slot_id: int,
                         client_name: str, client_phone: str,
                         note: str | None = None,
                         photo_id: str | None = None) -> Booking | None:
    async with async_session() as s:
        slot = await s.get(Slot, slot_id)
        if not slot or slot.is_booked:
            return None

        res = await s.execute(
            select(Booking).where(
                Booking.slot_id == slot_id,
                Booking.status == "active",
            )
        )
        if res.scalar_one_or_none():
            return None

        slot.is_booked = True
        booking = Booking(
            user_id=user_id,
            service_id=service_id,
            slot_id=slot_id,
            client_name=client_name,
            client_phone=client_phone,
            note=note,
            photo_id=photo_id,
        )
        s.add(booking)
        await s.commit()

        res2 = await s.execute(
            select(Booking)
            .options(selectinload(Booking.service), selectinload(Booking.slot))
            .where(Booking.id == booking.id)
        )
        return res2.scalar_one()

# ================= BOOKINGS (с ПОДГРУЗКОЙ СВЯЗЕЙ) =================
async def get_user_bookings(user_id: int, status: str = "active") -> list[Booking]:
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(selectinload(Booking.service), selectinload(Booking.slot))
            .where(Booking.user_id == user_id, Booking.status == status)
            .order_by(Booking.id.desc())
        )
        return list(res.scalars().all())


async def get_user_history(user_id: int) -> list[Booking]:
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(selectinload(Booking.service), selectinload(Booking.slot))
            .where(Booking.user_id == user_id)
            .order_by(Booking.id.desc())
        )
        return list(res.scalars().all())


async def get_active_bookings() -> list[Booking]:
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(
                selectinload(Booking.service),
                selectinload(Booking.slot),
                selectinload(Booking.user),
            )
            .where(Booking.status == "active")
            .order_by(Booking.slot_id)
        )
        return list(res.scalars().all())


async def get_bookings_today() -> list[Booking]:
    today_date = today()   # ← переименовали переменную
    start = datetime.combine(today_date, datetime.min.time())
    end = start + timedelta(days=1)
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(
                selectinload(Booking.service),
                selectinload(Booking.slot),
                selectinload(Booking.user),
            )
            .join(Slot, Slot.id == Booking.slot_id)
            .where(Booking.status == "active", Slot.dt >= start, Slot.dt < end)
            .order_by(Slot.dt)
        )
        return list(res.scalars().all())


async def get_bookings_tomorrow() -> list[Booking]:
    tomorrow_date = today() + timedelta(days=1)   # ← переименовали
    start = datetime.combine(tomorrow_date, datetime.min.time())
    end = start + timedelta(days=1)
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(
                selectinload(Booking.service),
                selectinload(Booking.slot),
                selectinload(Booking.user),
            )
            .join(Slot, Slot.id == Booking.slot_id)
            .where(Booking.status == "active", Slot.dt >= start, Slot.dt < end)
            .order_by(Slot.dt)
        )
        return list(res.scalars().all())


async def get_bookings_by_period(start: datetime, end: datetime) -> list[Booking]:
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .join(Slot, Slot.id == Booking.slot_id)
            .where(
                Booking.status == "active",
                Slot.dt >= start,
                Slot.dt < end,
            )
            .order_by(Slot.dt)
        )
        return list(res.scalars().all())


async def get_booking(booking_id: int) -> Booking | None:
    async with async_session() as s:
        res = await s.execute(
            select(Booking)
            .options(
                selectinload(Booking.service),
                selectinload(Booking.slot),
                selectinload(Booking.user),
            )
            .where(Booking.id == booking_id)
        )
        return res.scalar_one_or_none()


async def cancel_booking(booking_id: int) -> Booking | None:
    async with async_session() as s:
        booking = await s.get(Booking, booking_id)
        if not booking or booking.status != "active":
            return None

        booking.status = "cancelled"
        # НЕ обнуляем slot_id, просто освобождаем слот
        if booking.slot_id:
            slot = await s.get(Slot, booking.slot_id)
            if slot:
                slot.is_booked = False

        await s.commit()

        # перезагружаем со связями
        res = await s.execute(
            select(Booking)
            .options(selectinload(Booking.service), selectinload(Booking.slot))
            .where(Booking.id == booking_id)
        )
        return res.scalar_one()


async def mark_booking_done(booking_id: int) -> bool:
    async with async_session() as s:
        booking = await s.get(Booking, booking_id)
        if not booking:
            return False
        booking.status = "done"
        await s.commit()
        return True


# ================= STATS =================
async def get_stats() -> dict:
    async with async_session() as s:
        # всего клиентов
        total_users = (await s.execute(select(func.count(User.id)))).scalar_one()
        # активных записей
        active_bookings = (
            await s.execute(select(func.count(Booking.id)).where(Booking.status == "active"))
        ).scalar_one()
        # выполнено
        done_bookings = (
            await s.execute(select(func.count(Booking.id)).where(Booking.status == "done"))
        ).scalar_one()
        # отменено
        cancelled = (
            await s.execute(select(func.count(Booking.id)).where(Booking.status == "cancelled"))
        ).scalar_one()
        # выручка (по done + active)
        revenue = (
            await s.execute(
                select(func.coalesce(func.sum(Service.price), 0))
                .join(Booking, Booking.service_id == Service.id)
                .where(Booking.status.in_(["done", "active"]))
            )
        ).scalar_one()
        # свободных слотов в будущем
        free_slots = (
            await s.execute(
                select(func.count(Slot.id)).where(Slot.is_booked.is_(False), Slot.dt >= now())
            )
        ).scalar_one()
        # средний рейтинг
        avg_rating = (
            await s.execute(select(func.avg(Review.rating)))
        ).scalar()

    return {
        "total_users": total_users,
        "active_bookings": active_bookings,
        "done_bookings": done_bookings,
        "cancelled": cancelled,
        "revenue": int(revenue or 0),
        "free_slots": free_slots,
        "avg_rating": round(avg_rating, 2) if avg_rating else 0,
    }


async def get_revenue_by_month(year: int, month: int) -> int:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    async with async_session() as s:
        res = await s.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .join(Booking, Booking.service_id == Service.id)
            .join(Slot, Slot.id == Booking.slot_id)
            .where(
                Booking.status.in_(["done", "active"]),
                Slot.dt >= start,
                Slot.dt < end,
            )
        )
        return int(res.scalar_one() or 0)


# ================= BROADCASTS =================
async def save_broadcast(text: str | None, photo_id: str | None,
                         sent: int, failed: int) -> Broadcast:
    async with async_session() as s:
        b = Broadcast(text=text, photo_id=photo_id, sent_count=sent, failed_count=failed)
        s.add(b)
        await s.commit()
        await s.refresh(b)
        return b


# ================= REVIEWS =================
async def add_review(user_id: int, rating: int, text: str | None,
                     booking_id: int | None = None,
                     photo_id: str | None = None) -> Review:
    async with async_session() as s:
        r = Review(
            user_id=user_id,
            rating=rating,
            text=text,
            booking_id=booking_id,
            photo_id=photo_id,
        )
        s.add(r)
        await s.commit()
        await s.refresh(r)
        return r


async def get_all_reviews(limit: int = 20) -> list[Review]:
    async with async_session() as s:
        res = await s.execute(
            select(Review)
            .options(selectinload(Review.user))   # ← важно!
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())


async def get_review_by_id(review_id: int) -> Review | None:
    async with async_session() as s:
        res = await s.execute(
            select(Review)
            .options(selectinload(Review.user))   # ← важно!
            .where(Review.id == review_id)
        )
        return res.scalar_one_or_none()
# ================= REVIEWS (защита от накрутки) =================

async def get_done_bookings_for_review(user_id: int) -> list[Booking]:
    """Завершённые (done) записи клиента, по которым ещё нет отзыва."""
    async with async_session() as s:
        subq = select(Review.booking_id).where(
            Review.user_id == user_id,
            Review.booking_id.is_not(None),
        )
        res = await s.execute(
            select(Booking)
            .options(selectinload(Booking.service), selectinload(Booking.slot))
            .where(
                Booking.user_id == user_id,
                Booking.status == "done",
                Booking.id.not_in(subq),
            )
            .order_by(Booking.slot_id.desc())
        )
        return list(res.scalars().all())


async def can_leave_review(user_id: int, booking_id: int) -> tuple[bool, str]:
    async with async_session() as s:
        booking = await s.get(Booking, booking_id)
        if not booking:
            return False, "Запись не найдена"
        if booking.user_id != user_id:
            return False, "Это не твоя запись"
        if booking.status != "done":
            return False, "Отзыв можно оставить только после визита"

        res = await s.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.booking_id == booking_id,
            )
        )
        if res.scalar_one_or_none():
            return False, "Ты уже оставила отзыв по этой записи"

        return True, "Можно"

    # ================= PORTFOLIO =================

async def add_portfolio_photo(photo_id: str, caption: str | None = None) -> PortfolioPhoto:
    async with async_session() as s:
        p = PortfolioPhoto(photo_id=photo_id, caption=caption)
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p


async def get_all_portfolio() -> list[PortfolioPhoto]:
    async with async_session() as s:
        res = await s.execute(
            select(PortfolioPhoto).order_by(PortfolioPhoto.id.desc())
        )
        return list(res.scalars().all())


async def get_portfolio_photo(photo_id: int) -> PortfolioPhoto | None:
    async with async_session() as s:
        return await s.get(PortfolioPhoto, photo_id)


async def delete_portfolio_photo(photo_id: int) -> bool:
    async with async_session() as s:
        p = await s.get(PortfolioPhoto, photo_id)
        if not p:
            return False
        await s.delete(p)
        await s.commit()
        return True


async def count_portfolio() -> int:
    async with async_session() as s:
        res = await s.execute(select(func.count(PortfolioPhoto.id)))
        return res.scalar_one()

async def get_user(tg_id: int) -> User | None:
    async with async_session() as s:
        return await s.get(User, tg_id)


async def accept_terms(tg_id: int) -> None:
    async with async_session() as s:
        user = await s.get(User, tg_id)
        if not user:
            return
        user.terms_accepted = True
        user.terms_accepted_at = datetime.utcnow()
        user.marketing_accepted = True
        await s.commit()


async def has_accepted_terms(tg_id: int) -> bool:
    async with async_session() as s:
        user = await s.get(User, tg_id)
        return bool(user and user.terms_accepted)

async def get_users_for_broadcast() -> list[int]:
    async with async_session() as s:
        res = await s.execute(
            select(User.id).where(
                User.marketing_accepted == True,
                User.is_blocked == False,
            )
        )
        return [row[0] for row in res.all()]


async def set_marketing(tg_id: int, value: bool) -> None:
    async with async_session() as s:
        user = await s.get(User, tg_id)
        if user:
            user.marketing_accepted = value
            await s.commit()

# ================= SETTINGS =================

from database.models import Setting


async def get_setting(key: str) -> Setting | None:
    async with async_session() as s:
        res = await s.execute(select(Setting).where(Setting.key == key))
        return res.scalar_one_or_none()


async def set_setting(key: str, value: str | None = None,
                      photo_id: str | None = None) -> Setting:
    async with async_session() as s:
        res = await s.execute(select(Setting).where(Setting.key == key))
        st = res.scalar_one_or_none()

        if st:
            if value is not None:
                st.value = value
            if photo_id is not None:
                st.photo_id = photo_id
            st.updated_at = datetime.utcnow()
        else:
            st = Setting(key=key, value=value, photo_id=photo_id)
            s.add(st)

        await s.commit()
        await s.refresh(st)
        return st


async def get_about_text() -> str:
    """Возвращает текст «О мастере». Если не задан — дефолт."""
    st = await get_setting("about_text")
    if st and st.value:
        return st.value
    return (
        "💅 <b>Мастер Марина</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Опыт более 5 лет. Работаю с любыми формами и длиной.\n\n"
        "<b>Что я делаю:</b>\n"
        "• Маникюр (аппаратный, комби)\n"
        "• Покрытие гель-лак\n"
        "• Наращивание и коррекция\n"
        "• Дизайн, стемпинг, слайдеры\n"
        "• Педикюр\n\n"
        "✦ ─────────── ✦\n"
        "<i>Запись через бота — быстро и удобно!</i>"
    )


async def get_about_photo() -> str | None:
    """Возвращает file_id фото мастера (если задано)."""
    st = await get_setting("about_text")
    return st.photo_id if st else None