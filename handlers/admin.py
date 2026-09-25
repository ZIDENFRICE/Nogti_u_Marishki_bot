from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import MSK, now
from database.db import (
    add_service,
    add_slot,
    add_slots_bulk,
    cancel_booking,
    delete_service,
    delete_slot,
    get_active_bookings,
    get_all_future_slots,
    get_all_reviews,
    get_all_services,
    get_all_users,
    get_booking,
    get_bookings_today,
    get_bookings_tomorrow,
    get_service,
    get_slot,
    get_stats,
    get_user,
    get_user_history,
    mark_booking_done,
    save_broadcast,
)
from filters.is_admin import IsAdmin
from keyboards.admin_kb import (
    admin_booking_detail_kb,
    admin_bookings_kb,
    admin_menu_kb,
    back_admin_kb,
    broadcast_confirm_kb,
    slot_detail_kb,
)
from keyboards.user_kb import cancel_kb
from states.states import AdminSG
from utils.pagination import (
    get_page_info,
    pagination_kb,
    register_pagination,
)
from utils.safe_edit import safe_edit, safe_render
from utils.texts import (
    DIVIDER,
    booking_card,
    fmt_date,
    fmt_dt,
    money,
    stars,
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ================== МЕНЮ ==================
@router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"⚙️ <b>Админ-панель</b>\n{DIVIDER}\nВыбери раздел:",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text(
            f"⚙️ <b>Админ-панель</b>\n{DIVIDER}\nВыбери раздел:",
            reply_markup=admin_menu_kb(),
        )
    except Exception:
        await call.message.answer(
            f"⚙️ <b>Админ-панель</b>\n{DIVIDER}",
            reply_markup=admin_menu_kb(),
        )


# ================== СТАТИСТИКА ==================
@router.callback_query(F.data == "adm_stats")
async def adm_stats(call: CallbackQuery):
    s = await get_stats()
    text = (
        f"📊 <b>Статистика</b>\n"
        f"{DIVIDER}\n"
        f"👥 Клиентов: <b>{s['total_users']}</b>\n"
        f"🟢 Активных записей: <b>{s['active_bookings']}</b>\n"
        f"✅ Выполнено: <b>{s['done_bookings']}</b>\n"
        f"🔴 Отменено: <b>{s['cancelled']}</b>\n"
        f"🕐 Свободных слотов: <b>{s['free_slots']}</b>\n"
        f"{DIVIDER}\n"
        f"💰 Выручка (записи): <b>{money(s['revenue'])}</b>\n"
        f"⭐ Средний рейтинг: <b>{s['avg_rating']}</b>"
    )
    await call.message.edit_text(text, reply_markup=back_admin_kb())


# ================== ЗАПИСИ ==================
@router.callback_query(F.data == "adm_today")
async def adm_today(call: CallbackQuery):
    bookings = await get_bookings_today()
    if not bookings:
        await call.message.edit_text(
            f"📅 <b>Сегодня записей нет</b>\n{DIVIDER}\nОтдыхай 😊",
            reply_markup=back_admin_kb(),
        )
        return
    text = f"📅 <b>Записи на сегодня</b> ({len(bookings)})\n{DIVIDER}\n\n"
    for i, b in enumerate(bookings, 1):
        text += booking_card(b, for_admin=True, index=i) + "\n\n"
    await call.message.edit_text(text, reply_markup=admin_bookings_kb(bookings))


@router.callback_query(F.data == "adm_tomorrow")
async def adm_tomorrow(call: CallbackQuery):
    bookings = await get_bookings_tomorrow()
    if not bookings:
        await call.message.edit_text(
            f"📅 <b>Завтра записей нет</b>\n{DIVIDER}",
            reply_markup=back_admin_kb(),
        )
        return
    text = f"📅 <b>Записи на завтра</b> ({len(bookings)})\n{DIVIDER}\n\n"
    for i, b in enumerate(bookings, 1):
        text += booking_card(b, for_admin=True, index=i) + "\n\n"
    await call.message.edit_text(text, reply_markup=admin_bookings_kb(bookings))


BOOKINGS_PER_PAGE = 5


@router.callback_query(F.data == "adm_bookings")
async def adm_bookings(call: CallbackQuery):
    bookings = await get_active_bookings()
    if not bookings:
        await call.message.edit_text(
            f"📋 <b>Активных записей нет</b>\n{DIVIDER}",
            reply_markup=back_admin_kb(),
        )
        return
    ids = [b.id for b in bookings]
    register_pagination("bookings_adm", ids, per_page=BOOKINGS_PER_PAGE)
    await render_bookings_adm(call)


async def render_bookings_adm(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("bookings_adm")
    text = f"📋 <b>Все активные записи</b> (стр. {page + 1} из {total_pages})\n{DIVIDER}\n\n"

    for i, bid in enumerate(page_ids, 1):
        b = await get_booking(bid)
        if not b:
            continue
        # защита: слот мог быть удалён
        if b.slot is None:
            text += f"<b>#{b.id}</b> — ⚠️ слот удалён\n\n"
            continue
        text += booking_card(b, for_admin=True, index=page * BOOKINGS_PER_PAGE + i) + "\n\n"

    kb = pagination_kb(
        key="bookings_adm",
        page=page,
        total_pages=total_pages,
        back_callback="admin_panel",
    )
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("adm_booking:"))
async def adm_booking_detail(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    b = await get_booking(booking_id)
    if b.slot:
        dt_line = f"🗓 {fmt_date(b.slot.dt)} в {b.slot.dt.strftime('%H:%M')}\n"
    else:
        dt_line = "🗓 — (слот удалён)\n"

    text = (
        f"📌 <b>Запись #{b.id}</b>\n"
        f"{DIVIDER}\n"
        f"💅 <b>{b.service.title}</b>\n"
        f"{dt_line}"
        f"💰 {money(b.service.price)} • ⏱ {b.service.duration_min} мин\n"
        f"👤 {b.client_name}\n"
        f"📞 <code>{b.client_phone}</code>\n"
    )
    if b.note:
        text += f"📝 <i>{b.note}</i>\n"
    if b.user:
        uname = f"@{b.user.username}" if b.user.username else f"id{b.user_id}"
        text += f"🔗 {uname}\n"
    text += f"📌 Статус: <b>{b.status}</b>"
    await call.message.edit_text(
        text,
        reply_markup=admin_booking_detail_kb(b.id),
    )


@router.callback_query(F.data.startswith("adm_booking_done:"))
async def adm_booking_done(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    b = await get_booking(booking_id)
    ok = await mark_booking_done(booking_id)
    if ok and b:
        await call.answer("Отмечено как выполнено ✅")
        # уведомим клиента
        try:
            await call.bot.send_message(
                b.user_id,
                f"✅ <b>Спасибо за визит!</b>\n"
                f"{DIVIDER}\n"
                f"Было приятно поработать 💖\n"
                f"Буду рада отзыву — /start → ⭐ Отзывы",
            )
        except Exception:
            pass
    else:
        await call.answer("Не удалось", show_alert=True)
    await adm_bookings(call)


@router.callback_query(F.data.startswith("adm_booking_cancel:"))
async def adm_booking_cancel(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    b = await get_booking(booking_id)
    cancelled = await cancel_booking(booking_id)
    if not cancelled:
        await call.answer("Не удалось отменить", show_alert=True)
        return
    await call.answer("Запись отменена")
    if b:
        try:
            await call.bot.send_message(
                b.user_id,
                f"❌ <b>Твоя запись отменена</b>\n"
                f"{DIVIDER}\n"
                f"#{b.id} • {b.service.title}\n"
                f"🗓 {fmt_dt(b.slot.dt)}\n\n"
                f"Если это ошибка — свяжись с мастером.",
            )
        except Exception:
            pass
    await adm_bookings(call)


# ================== УСЛУГИ ==================
SERVICES_PER_PAGE_ADM = 8


@router.callback_query(F.data == "adm_services")
async def adm_services(call: CallbackQuery):
    services = await get_all_services()
    ids = [s.id for s in services]
    register_pagination("services_adm", ids, per_page=SERVICES_PER_PAGE_ADM)
    await render_services_adm(call)


async def render_services_adm(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("services_adm")
    text = f"💅 <b>Услуги</b> (стр. {page + 1} из {total_pages})\n{DIVIDER}\n\n"
    if not page_ids:
        text += "<i>Пока нет услуг</i>\n"

    for sid in page_ids:
        s = await get_service(sid)
        if not s:
            continue
        active = "🟢" if s.is_active else "🔴"
        text += f"{active} <b>{s.title}</b> — {money(s.price)} ({s.duration_min} мин)\n"

    # Добавим кнопки удаления к каждой услуге через InlineKeyboardBuilder
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить услугу", callback_data="adm_service_add")
    for sid in page_ids:
        s = await get_service(sid)
        if not s:
            continue
        b.button(text=f"🗑 {s.title}", callback_data=f"adm_service_del:{sid}")
    # навигация
    nav = pagination_kb(
        key="services_adm",
        page=page,
        total_pages=total_pages,
        back_callback="admin_panel",
    )
    for row in nav.inline_keyboard:
        b.row(*row)
    b.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=b.as_markup())
    except Exception:
        await call.message.answer(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "adm_service_add")
async def adm_service_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.add_service_title)
    await safe_edit(
        call,
        f"➕ <b>Новая услуга — шаг 1/4</b>\n{DIVIDER}\n"
        "Введи <b>название</b> услуги:",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_service_title, F.text)
async def adm_service_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminSG.add_service_desc)
    await message.answer(
        f"📝 <b>Шаг 2/4 — Описание</b>\n{DIVIDER}\n"
        "Введи короткое описание (или <b>—</b>, чтобы пропустить):",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_service_desc, F.text)
async def adm_service_desc(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc in ("-", "—", "нет"):
        desc = None
    await state.update_data(desc=desc)
    await state.set_state(AdminSG.add_service_price)
    await message.answer(
        f"💰 <b>Шаг 3/4 — Цена</b>\n{DIVIDER}\n"
        "Введи цену в рублях (целое число):",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_service_price, F.text)
async def adm_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно целое число. Попробуй снова:")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AdminSG.add_service_duration)
    await message.answer(
        f"⏱ <b>Шаг 4/4 — Длительность</b>\n{DIVIDER}\n"
        "Введи длительность в минутах:",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_service_duration, F.text)
async def adm_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Нужно целое число. Попробуй снова:")
        return
    data = await state.get_data()
    await state.clear()
    svc = await add_service(
        data["title"], data["price"], int(message.text), data.get("desc")
    )
    await message.answer(
        f"✅ <b>Услуга добавлена!</b>\n{DIVIDER}\n"
        f"💅 {svc.title}\n"
        f"💰 {money(svc.price)}\n"
        f"⏱ {svc.duration_min} мин",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("adm_service_del:"))
async def adm_service_del(call: CallbackQuery):
    service_id = int(call.data.split(":")[1])
    svc = await get_service(service_id)
    await delete_service(service_id)
    await call.answer(f"Удалено: {svc.title if svc else '—'}")
    await adm_services(call)


# ================== СЛОТЫ ==================
SLOTS_PER_PAGE = 10


@router.callback_query(F.data == "adm_slots")
async def adm_slots(call: CallbackQuery):
    slots = await get_all_future_slots()
    ids = [s.id for s in slots]
    register_pagination("slots_adm", ids, per_page=SLOTS_PER_PAGE)
    await render_slots_adm(call)


async def render_slots_adm(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("slots_adm")
    text = (
        f"🕐 <b>Слоты</b> (стр. {page + 1} из {total_pages})\n"
        f"{DIVIDER}\n🟢 свободен • 🔴 занят\n\n"
    )
    if not page_ids:
        text += "<i>Слотов пока нет</i>\n"

    # Кнопки: добавить + список слотов
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить слот", callback_data="adm_slot_add")
    b.button(text="➕ Добавить несколько", callback_data="adm_slot_bulk")

    for sid in page_ids:
        s = await get_slot(sid)
        if not s:
            continue
        mark = "🔴" if s.is_booked else "🟢"
        text += f"{mark} {fmt_dt(s.dt)}\n"
        b.button(text=f"{mark} {s.dt.strftime('%d.%m %H:%M')}", callback_data=f"adm_slot_view:{sid}")

    nav = pagination_kb(
        key="slots_adm",
        page=page,
        total_pages=total_pages,
        back_callback="admin_panel",
    )
    for row in nav.inline_keyboard:
        b.row(*row)
    b.adjust(2, 1)

    try:
        await call.message.edit_text(text, reply_markup=b.as_markup())
    except Exception:
        await call.message.answer(text, reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("adm_slot_view:"))
async def adm_slot_view(call: CallbackQuery):
    slot_id = int(call.data.split(":")[1])
    slot = await get_slot(slot_id)
    if not slot:
        await call.answer("Слот не найден", show_alert=True)
        return
    status = "🔴 Занят" if slot.is_booked else "🟢 Свободен"
    text = (
        f"🕐 <b>Слот #{slot.id}</b>\n"
        f"{DIVIDER}\n"
        f"🗓 {fmt_date(slot.dt)}\n"
        f"⏰ {slot.dt.strftime('%H:%M')}\n"
        f"📌 {status}\n"
    )
    if slot.is_booked:
        text += f"\n{DIVIDER}\n⚠️ <i>При удалении запись будет отменена и клиент получит уведомление.</i>"
    await call.message.edit_text(
        text,
        reply_markup=slot_detail_kb(slot.id, slot.is_booked),
    )


@router.callback_query(F.data.startswith("adm_slot_del:"))
async def adm_slot_del(call: CallbackQuery):
    slot_id = int(call.data.split(":")[1])
    result = await delete_slot(slot_id, force=False)
    if not result["deleted"]:
        await call.answer("Не удалось удалить", show_alert=True)
    else:
        await call.answer("✅ Слот удалён")
    await adm_slots(call)


@router.callback_query(F.data.startswith("adm_slot_del_force:"))
async def adm_slot_del_force(call: CallbackQuery):
    slot_id = int(call.data.split(":")[1])
    result = await delete_slot(slot_id, force=True)

    if not result["deleted"]:
        await call.answer("Не удалось удалить", show_alert=True)
        return

    await call.answer("✅ Слот удалён, запись отменена")

    # уведомим клиента, если была запись
    if result["user_id"]:
        try:
            await call.bot.send_message(
                result["user_id"],
                f"❌ <b>Твоя запись отменена мастером</b>\n"
                f"{DIVIDER}\n"
                f"🗓 {fmt_dt(result['dt'])}\n\n"
                f"Приносим извинения 🙏 Свяжись с мастером для перезаписи.",
            )
        except Exception as e:
            print(f"[NOTIFY FAIL] {result['user_id']}: {e}")

    # обновим список слотов
    await adm_slots(call)


@router.callback_query(F.data == "adm_slot_add")
async def adm_slot_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.add_slot_datetime)
    await safe_edit(
        call,
        f"➕ <b>Новый слот</b>\n{DIVIDER}\n"
        "Введи дату и время в формате:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Например: <code>25.12.2025 14:30</code>",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_slot_datetime, F.text)
async def adm_slot_datetime(message: Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M").replace(tzinfo=MSK)
    except ValueError:
        await message.answer("Неверный формат. Пример: <code>25.12.2025 14:30</code>")
        return
    if dt < now():
        await message.answer("Эта дата уже в прошлом. Введи будущую дату.")
        return
    await state.clear()
    slot = await add_slot(dt)
    await message.answer(
        f"✅ <b>Слот добавлен</b>\n{DIVIDER}\n🗓 {fmt_dt(slot.dt)}",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "adm_slot_bulk")
async def adm_slot_bulk(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.add_slot_bulk)
    await safe_edit(
        call,
        f"➕ <b>Массовое добавление слотов</b>\n{DIVIDER}\n"
        "Введи даты и время <b>каждое с новой строки</b>:\n\n"
        "<code>25.12.2025 10:00\n25.12.2025 12:00\n25.12.2025 14:00</code>",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.add_slot_bulk, F.text)
async def adm_slot_bulk_input(message: Message, state: FSMContext):
    lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    dts, errors = [], []
    for line in lines:
        try:
            dt = datetime.strptime(line, "%d.%m.%Y %H:%M").replace(tzinfo=MSK)
            if dt < now():
                errors.append(f"{line} — в прошлом")
                continue
            dts.append(dt)
        except ValueError:
            errors.append(f"{line} — неверный формат")
    if not dts:
        await message.answer("Не удалось распознать ни одной даты. Проверь формат.")
        return
    await state.clear()
    n = await add_slots_bulk(dts)
    text = f"✅ <b>Добавлено слотов: {n}</b>\n{DIVIDER}\n"
    for dt in dts:
        text += f"🟢 {fmt_dt(dt)}\n"
    if errors:
        text += "\n⚠️ <b>Ошибки:</b>\n" + "\n".join(errors)
    await message.answer(text, reply_markup=admin_menu_kb())


# ================== КЛИЕНТЫ ==================
CLIENTS_PER_PAGE = 10


@router.callback_query(F.data == "adm_clients")
async def adm_clients(call: CallbackQuery):
    users = await get_all_users()
    if not users:
        await call.message.edit_text("👥 Клиентов пока нет.", reply_markup=back_admin_kb())
        return
    ids = [u.id for u in users]
    register_pagination("clients_adm", ids, per_page=CLIENTS_PER_PAGE)
    await render_clients_adm(call)


async def render_clients_adm(call: CallbackQuery):
    page_ids, page, total_pages = get_page_info("clients_adm")
    text = f"👥 <b>Клиенты</b> (стр. {page + 1} из {total_pages})\n{DIVIDER}\n\n"
    for i, uid in enumerate(page_ids, 1):
        u = await get_user(uid)
        if not u:
            continue
        uname = f"@{u.username}" if u.username else "—"
        name = u.full_name or "—"
        text += f"{page * CLIENTS_PER_PAGE + i}. <b>{name}</b> • {uname}\n   <code>{u.id}</code>\n\n"

    kb = pagination_kb(
        key="clients_adm",
        page=page,
        total_pages=total_pages,
        back_callback="admin_panel",
    )
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm_search")
async def adm_search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.search_client)
    await safe_edit(
        call,
        f"🔍 <b>Поиск клиента</b>\n{DIVIDER}\n"
        "Введи <b>имя</b>, <b>@username</b> или <b>телефон</b>:",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.search_client, F.text)
async def adm_search_result(message: Message, state: FSMContext):
    q = message.text.strip().lower().lstrip("@")
    users = await get_all_users()
    found = [
        u for u in users
        if (u.username and q in u.username.lower())
        or (u.full_name and q in u.full_name.lower())
        or q in str(u.id)
    ]
    await state.clear()
    if not found:
        await message.answer(
            "😔 Никого не найдено.",
            reply_markup=admin_menu_kb(),
        )
        return
    text = f"🔍 <b>Найдено: {len(found)}</b>\n{DIVIDER}\n\n"
    for u in found[:20]:
        hist = await get_user_history(u.id)
        total = sum(b.service.price for b in hist if b.status in ("active", "done"))
        text += (
            f"👤 <b>{u.full_name or '—'}</b>\n"
            f"   @{u.username or '—'} • <code>{u.id}</code>\n"
            f"   Записей: {len(hist)} • Сумма: {money(total)}\n\n"
        )
    await message.answer(text, reply_markup=admin_menu_kb())


# ================== ОТЗЫВЫ ==================

REVIEWS_PER_PAGE_ADM = 1   # ← один отзыв на страницу с фото


@router.callback_query(F.data == "adm_reviews")
async def adm_reviews(call: CallbackQuery):
    reviews = await get_all_reviews(limit=200)
    if not reviews:
        await call.message.edit_text("⭐ Отзывов пока нет.", reply_markup=back_admin_kb())
        return
    ids = [r.id for r in reviews]
    register_pagination("reviews_adm", ids, per_page=REVIEWS_PER_PAGE_ADM)
    await render_reviews_adm(call)


async def render_reviews_adm(call: CallbackQuery):
    from database.db import get_review_by_id

    page_ids, page, total_pages = get_page_info("reviews_adm")
    if not page_ids:
        await call.message.edit_text("Отзывов больше нет.", reply_markup=back_admin_kb())
        return

    rid = page_ids[0]
    r = await get_review_by_id(rid)
    if not r:
        await call.answer("Отзыв пропал")
        return

    uname = f"@{r.user.username}" if r.user and r.user.username else f"id{r.user_id}"
    full = r.user.full_name if r.user and r.user.full_name else "—"

    text = (
        f"⭐ <b>Отзыв</b>  ·  {page + 1} / {total_pages}\n"
        f"{DIVIDER}\n"
        f"Оценка: {stars(r.rating)}\n"
    )
    if r.text:
        text += f"\n💬 <i>{r.text}</i>\n"
    text += (
        f"\n👤 {full}\n"
        f"🔗 {uname}\n"
        f"🆔 <code>{r.user_id}</code>\n"
    )
    if r.photo_id:
        text += "📷 фото прикреплено"
    else:
        text += "📷 фото нет"

    kb = pagination_kb(
        key="reviews_adm",
        page=page,
        total_pages=total_pages,
        back_callback="admin_panel",
    )

    await safe_render(call, text, photo_id=r.photo_id, reply_markup=kb)


# ================== РАССЫЛКА (с фото) ==================
@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.broadcast_content)
    await safe_edit(
        call,
        f"📢 <b>Рассылка</b>\n{DIVIDER}\n"
        "Отправь <b>текст</b> или <b>фото</b> (можно с подписью).\n\n"
        "<i>Получат все, кто запускал бота.</i>",
        reply_markup=cancel_kb("cancel_admin"),
    )


@router.message(AdminSG.broadcast_content, F.photo)
async def adm_broadcast_photo(message: Message, state: FSMContext):
    await state.update_data(
        photo_id=message.photo[-1].file_id,
        text=message.caption or None,
    )
    preview = message.caption or "<i>(без подписи)</i>"
    await message.answer_photo(
        message.photo[-1].file_id,
        caption=f"👁 <b>Предпросмотр:</b>\n{DIVIDER}\n{preview}",
        reply_markup=broadcast_confirm_kb(),
    )


@router.message(AdminSG.broadcast_content, F.text)
async def adm_broadcast_text(message: Message, state: FSMContext):
    await state.update_data(photo_id=None, text=message.text)
    await message.answer(
        f"👁 <b>Предпросмотр:</b>\n{DIVIDER}\n{message.text}",
        reply_markup=broadcast_confirm_kb(),
    )


@router.callback_query(F.data == "adm_broadcast_send")
async def adm_broadcast_send(call: CallbackQuery, state: FSMContext):
    from utils.safe_edit import safe_edit

    data = await state.get_data()
    await state.clear()
    photo_id = data.get("photo_id")
    text = data.get("text")

    print(f"[BROADCAST] photo_id={photo_id}, text_len={len(text or '')}")

    if not photo_id and not text:
        await safe_edit(call, "⚠️ Нет ни текста, ни фото.", reply_markup=admin_menu_kb())
        return

    users = await get_all_users()
    sent, failed = 0, 0
    errors = []

    # НЕ редактируем фото-сообщение — просто удаляем и шлём новое
    try:
        await call.message.delete()
    except Exception:
        pass

    status_msg = await call.message.answer(
        f"📢 <b>Рассылка запущена...</b>\n{DIVIDER}\nВсего получателей: {len(users)}"
    )

    for u in users:
        try:
            if photo_id:
                await call.bot.send_photo(u.id, photo_id, caption=text or "")
            else:
                await call.bot.send_message(u.id, text or "")
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(f"{u.id}: {e}")
            print(f"[BROADCAST FAIL] {u.id}: {e}")

    try:
        await save_broadcast(text, photo_id, sent, failed)
    except Exception as e:
        print(f"[BROADCAST SAVE FAIL] {e}")

    report = (
        f"✅ <b>Рассылка завершена</b>\n"
        f"{DIVIDER}\n"
        f"📤 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>"
    )
    if errors[:3]:
        report += "\n\n<b>Первые ошибки:</b>\n<code>" + "\n".join(errors[:3]) + "</code>"

    await status_msg.edit_text(report, reply_markup=admin_menu_kb())

