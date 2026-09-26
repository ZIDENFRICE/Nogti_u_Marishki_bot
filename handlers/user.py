from database.db import get_all_portfolio, get_portfolio_photo
from utils.safe_edit import safe_render
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import (
    cancel_booking,
    get_all_reviews,
    get_booking,
    get_or_create_user,
    get_review_by_id,
    get_user_bookings,
    get_user_history,
)
from keyboards.user_kb import (
    main_menu_kb,
    my_bookings_kb,
)
from utils.pagination import (
    get_page_info,
    pagination_kb,
    register_pagination,
)
from utils.safe_edit import safe_render
from utils.texts import (
    DIVIDER,
    DIVIDER_STAR,
    booking_card,
    fmt_dt,
    money,
    stars,
)

REVIEWS_PER_PAGE = 5
router = Router()


ABOUT_TEXT = (
    f"<b>💅 Мастер Марина</b>\n"
    f"{DIVIDER}\n"
    "Большой опыт работы. Работаю с разными формами и длиной.\n\n"
    "<b>Что я делаю:</b>\n"
    "• Маникюр (аппаратный, комби)\n"
    "• Покрытие гель-лак\n"
    "• Наращивание и коррекция\n"
    "• Дизайн, стемпинг, слайдеры\n"
    f"{DIVIDER_STAR}\n"
    "<i>Запись через бота — быстро и удобно!</i>"
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    is_admin = message.from_user.id in ADMIN_IDS

    text = (
        f"✨ <b>Привет, {message.from_user.first_name}!</b> ✨\n"
        f"{DIVIDER}\n"
        "Меня зовут <b>Марина</b>, я мастер ногтевого сервиса 💅\n\n"
        "Здесь ты можешь:\n"
        "• 💅 Записаться на удобное время\n"
        "• 📋 Посмотреть свои записи\n"
        "• ⭐ Оставить отзыв\n\n"
        "Выбери действие ниже 👇"
    )
    await message.answer(text, reply_markup=main_menu_kb(is_admin))


@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = call.from_user.id in ADMIN_IDS
    text = (
        f"✨ <b>Главное меню</b>\n"
        f"{DIVIDER}\n"
        "Что будем делать?"
    )
    try:
        await call.message.edit_text(text, reply_markup=main_menu_kb(is_admin))
    except Exception:
        await call.message.answer(text, reply_markup=main_menu_kb(is_admin))


@router.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.message.edit_text(
        ABOUT_TEXT,
        reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
    )


# ================== МОИ ЗАПИСИ ==================
@router.callback_query(F.data == "my_bookings")
async def my_bookings(call: CallbackQuery):
    bookings = await get_user_bookings(call.from_user.id, status="active")
    if not bookings:
        await call.message.edit_text(
            f"📭 <b>У тебя пока нет активных записей</b>\n"
            f"{DIVIDER}\n"
            "Хочешь записаться? Нажми 💅 <b>Записаться</b>",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return

    text = f"📋 <b>Твои активные записи ({len(bookings)})</b>\n{DIVIDER}\n\n"
    cards = []
    for i, b in enumerate(bookings, 1):
        cards.append(booking_card(b, index=i))
    text += "\n\n".join(cards)
    text += f"\n\n{DIVIDER}\n<i>Чтобы отменить — нажми кнопку ниже</i>"

    await call.message.edit_text(text, reply_markup=my_bookings_kb(bookings))


@router.callback_query(F.data == "my_history")
async def my_history(call: CallbackQuery):
    bookings = await get_user_history(call.from_user.id)
    if not bookings:
        await call.message.edit_text(
            "📭 История пуста.",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return

    text = f"🕓 <b>История посещений ({len(bookings)})</b>\n{DIVIDER}\n\n"
    for b in bookings[:15]:
        status_icon = {"active": "🟢", "cancelled": "🔴", "done": "✅"}.get(b.status, "❔")
        dt_str = fmt_dt(b.slot.dt) if b.slot else "— (слот удалён)"
        text += (
            f"{status_icon} <b>#{b.id}</b> • {b.service.title}\n"
            f"   🗓 {dt_str} • {money(b.service.price)}\n\n"
        )
    if len(bookings) > 15:
        text += f"<i>...и ещё {len(bookings) - 15}</i>"

    await call.message.edit_text(
        text,
        reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
    )


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_my_booking(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    booking = await get_booking(booking_id)
    if not booking or booking.user_id != call.from_user.id:
        await call.answer("Запись не найдена", show_alert=True)
        return

    cancelled = await cancel_booking(booking_id)
    if cancelled:
        await call.answer("Запись отменена ✅", show_alert=False)
        # уведомим админов
        for admin_id in ADMIN_IDS:
            try:
                await call.bot.send_message(
                    admin_id,
                    f"⚠️ <b>Клиент отменил запись</b>\n"
                    f"{DIVIDER}\n"
                    f"#{cancelled.id} • {cancelled.service.title}\n"
                    f"🗓 {fmt_dt(cancelled.slot.dt)}\n"
                    f"👤 {cancelled.client_name} • 📞 {cancelled.client_phone}",
                )
            except Exception:
                pass
    else:
        await call.answer("Не удалось отменить", show_alert=True)
    await my_bookings(call)


# ================== ОТЗЫВЫ ==================

REVIEWS_PER_PAGE = 1   # ← по одному отзыву на страницу — красиво с фото


@router.callback_query(F.data == "reviews_view")
async def reviews_view(call: CallbackQuery):
    reviews = await get_all_reviews(limit=100)
    if not reviews:
        await call.message.edit_text(
            f"⭐ <b>Пока нет отзывов</b>\n{DIVIDER}\n"
            "Стань первой, кто оставит отзыв после визита!",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return
    ids = [r.id for r in reviews]
    register_pagination("reviews_user", ids, per_page=REVIEWS_PER_PAGE)
    await render_reviews_user(call)


async def render_reviews_user(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("reviews_user")
    if not page_ids:
        await call.message.edit_text("Отзывов больше нет.")
        return

    rid = page_ids[0]
    r = await get_review_by_id(rid)
    if not r:
        await call.answer("Отзыв пропал 😔")
        return

    # Имя клиента (маскируем — показываем только имя или «Клиент»)
    author = "Клиент"
    if r.user and r.user.full_name:
        author = r.user.full_name.split()[0]  # только имя
    elif r.user and r.user.username:
        author = f"@{r.user.username}"

    text = (
        f"⭐ <b>Отзыв</b>  ·  {page + 1} / {total_pages}\n"
        f"{DIVIDER}\n"
        f"Оценка: {stars(r.rating)}\n"
    )
    if r.text:
        text += f"\n💬 <i>{r.text}</i>\n"
    text += f"\n👤 {author}"

    kb = pagination_kb(
        key="reviews_user",
        page=page,
        total_pages=total_pages,
        extra_buttons=[("✍️ Написать отзыв", "review_write")],
        back_callback="back_main",
        back_text="⬅️ В меню",
    )

    await safe_render(call, text, photo_id=r.photo_id, reply_markup=kb)

PORTFOLIO_PER_PAGE = 1


@router.callback_query(F.data == "portfolio_view")
async def portfolio_view(call: CallbackQuery):
    photos = await get_all_portfolio()
    if not photos:
        await call.message.edit_text(
            f"📸 <b>Примеры работ</b>\n{DIVIDER}\n"
            "Мастер скоро добавит фотографии работ 💅",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return
    ids = [p.id for p in photos]
    register_pagination("portfolio_user", ids, per_page=PORTFOLIO_PER_PAGE)
    await render_portfolio_user(call)


async def render_portfolio_user(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("portfolio_user")
    if not page_ids:
        await call.message.edit_text("Пока нет фото.")
        return

    pid = page_ids[0]
    p = await get_portfolio_photo(pid)
    if not p:
        await call.answer("Фото не найдено")
        return

    caption = f"📸 <b>Примеры работ</b>  ·  {page + 1} / {total_pages}\n{DIVIDER}\n"
    if p.caption:
        caption += f"\n💬 <i>{p.caption}</i>"

    kb = pagination_kb(
        key="portfolio_user",
        page=page,
        total_pages=total_pages,
        extra_buttons=[("💅 Записаться", "book_start")],
        back_callback="back_main",
        back_text="⬅️ В меню",
    )
    await safe_render(call, caption, photo_id=p.photo_id, reply_markup=kb)