from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import (
    create_booking,
    get_active_services,
    get_free_slots,
    get_or_create_user,
    get_service,
    get_slot,
)
from keyboards.user_kb import (
    cancel_kb,
    main_menu_kb,
    slots_kb,
)
from states.states import BookingSG
from utils.pagination import (
    get_page_info,
    pagination_kb,
    register_pagination,
)
from utils.safe_edit import safe_edit
from utils.texts import DIVIDER, fmt_dt, money

router = Router()


SERVICES_PER_PAGE = 5


@router.callback_query(F.data == "book_start")
async def book_start(call: CallbackQuery, state: FSMContext):
    services = await get_active_services()
    if not services:
        await call.message.edit_text(
            f"😔 <b>Пока нет доступных услуг</b>\n{DIVIDER}\n"
            "Загляни позже!",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return
    await state.set_state(BookingSG.choosing_service)
    ids = [s.id for s in services]
    register_pagination("services_user", ids, per_page=SERVICES_PER_PAGE)
    await render_services_user(call)


async def render_services_user(call: CallbackQuery):
    """Рендер страницы услуг для клиента."""
    from database.db import get_service

    page_ids, page, total_pages = get_page_info("services_user")
    if not page_ids:
        await call.message.edit_text("Услуг больше нет.")
        return

    text = f"💅 <b>Выбери услугу</b> (стр. {page + 1} из {total_pages})\n{DIVIDER}\n\n"
    for i, sid in enumerate(page_ids, 1):
        s = await get_service(sid)
        if not s:
            continue
        text += f"<b>{i}. {s.title}</b>\n"
        if s.description:
            text += f"   <i>{s.description}</i>\n"
        text += f"   💰 {money(s.price)} • ⏱ {s.duration_min} мин\n\n"

    # Кнопки выбора услуги + навигация
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb_builder = InlineKeyboardBuilder()
    for sid in page_ids:
        s = await get_service(sid)
        if not s:
            continue
        kb_builder.button(
            text=f"💅 {s.title} • {s.price}₽",
            callback_data=f"book_svc:{s.id}",
        )
    # добавляем навигацию
    nav = pagination_kb(
        key="services_user",
        page=page,
        total_pages=total_pages,
        back_callback="back_main",
        back_text="⬅️ В меню",
    )
    # объединяем: сначала кнопки услуг, потом навигация
    for row in nav.inline_keyboard:
        kb_builder.row(*row)
    kb_builder.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=kb_builder.as_markup())
    except Exception:
        await call.message.answer(text, reply_markup=kb_builder.as_markup())


@router.callback_query(BookingSG.choosing_service, F.data.startswith("book_svc:"))
async def choose_service(call: CallbackQuery, state: FSMContext):
    service_id = int(call.data.split(":")[1])
    service = await get_service(service_id)
    if not service:
        await call.answer("Услуга недоступна", show_alert=True)
        return
    await state.update_data(service_id=service_id, service_title=service.title)
    slots = await get_free_slots()
    if not slots:
        await call.message.edit_text(
            f"😔 <b>Свободных окошек пока нет</b>\n{DIVIDER}\n"
            "Попробуй позже 🙏",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        await state.clear()
        return
    await state.set_state(BookingSG.choosing_slot)
    text = (
        f"💅 <b>{service.title}</b>\n"
        f"💰 {money(service.price)} • ⏱ {service.duration_min} мин\n"
        f"{DIVIDER}\n"
        "🗓 <b>Выбери удобное время:</b>"
    )
    await call.message.edit_text(text, reply_markup=slots_kb(slots))


# ============ ИМЯ ============
@router.callback_query(BookingSG.choosing_slot, F.data.startswith("book_slot:"))
async def choose_slot(call: CallbackQuery, state: FSMContext):
    slot_id = int(call.data.split(":")[1])
    slot = await get_slot(slot_id)
    if not slot or slot.is_booked:
        await call.answer("Это время уже занято 😔", show_alert=True)
        return
    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingSG.entering_name)
    await safe_edit(
        call,
        f"✏️ <b>Как тебя зовут?</b>\n{DIVIDER}\n"
        "Введи имя, чтобы мастер знала, как к тебе обращаться:",
        reply_markup=cancel_kb("cancel_action"),
    )


@router.message(BookingSG.entering_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("Имя должно быть от 2 до 60 символов. Попробуй снова:")
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingSG.entering_phone)
    await message.answer(
        f"📞 <b>Введи номер телефона</b>\n{DIVIDER}\n"
        "Например: <code>+79991234567</code>",
        reply_markup=cancel_kb("cancel_action"),
    )


# ============ ТЕЛЕФОН ============
@router.message(BookingSG.entering_phone, F.text)
async def enter_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("Похоже, номер некорректный. Попробуй снова:")
        return
    await state.update_data(client_phone=phone)
    await state.set_state(BookingSG.entering_note)
    await message.answer(
        f"📝 <b>Пожелания к визиту?</b>\n{DIVIDER}\n"
        "Например: «хочу френч», «короткая длина» и т.п.\n"
        "Или напиши <b>—</b> чтобы пропустить.",
        reply_markup=cancel_kb("cancel_action"),
    )



# ============ ПОЖЕЛАНИЯ ============
@router.message(BookingSG.entering_note, F.text)
async def enter_note(message: Message, state: FSMContext):
    note = message.text.strip()
    if note in ("-", "—", "нет", "Нет"):
        note = None
    await state.update_data(note=note)

    data = await state.get_data()
    service = await get_service(data["service_id"])
    slot = await get_slot(data["slot_id"])

    text = (
        f"🔎 <b>Проверь запись</b>\n"
        f"{DIVIDER}\n"
        f"💅 <b>{service.title}</b>\n"
        f"💰 {money(service.price)} • ⏱ {service.duration_min} мин\n"
        f"🗓 {fmt_dt(slot.dt)}\n"
        f"👤 {data['client_name']}\n"
        f"📞 {data['client_phone']}\n"
    )
    if note:
        text += f"📝 <i>{note}</i>\n"
    text += f"\n{DIVIDER}\nВсё верно?"

    await state.set_state(BookingSG.confirming)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="book_confirm")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2)

    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(BookingSG.confirming, F.data == "book_confirm")
async def confirm_booking(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    await get_or_create_user(call.from_user.id, call.from_user.username, call.from_user.full_name)

    booking = await create_booking(
        user_id=call.from_user.id,
        service_id=data["service_id"],
        slot_id=data["slot_id"],
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        note=data.get("note"),
    )
    if not booking:
        await call.message.edit_text(
            "😔 Упс, это время только что заняли.\nПопробуй выбрать другое.",
            reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
        )
        return

    service = await get_service(data["service_id"])
    slot = await get_slot(data["slot_id"])

    await call.message.edit_text(
        f"🎉 <b>Ты записана!</b>\n"
        f"{DIVIDER}\n"
        f"💅 {service.title}\n"
        f"🗓 {fmt_dt(slot.dt)}\n"
        f"💰 {money(service.price)}\n"
        f"📍 {data.get('address', 'ул. Примерная, 10')}\n"
        f"{DIVIDER}\n"
        "За день до визита придёт напоминание ⏰\n"
        "Ждём тебя! 💖",
        reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
    )

    # уведомление админам
    admin_text = (
        f"🔔 <b>НОВАЯ ЗАПИСЬ!</b>\n"
        f"{DIVIDER}\n"
        f"💅 <b>{service.title}</b>\n"
        f"🗓 {fmt_dt(slot.dt)}\n"
        f"💰 {money(service.price)} • ⏱ {service.duration_min} мин\n"
        f"👤 {booking.client_name}\n"
        f"📞 <code>{booking.client_phone}</code>\n"
    )
    if booking.note:
        admin_text += f"📝 <i>{booking.note}</i>\n"
    uname = f"@{call.from_user.username}" if call.from_user.username else f"id{call.from_user.id}"
    admin_text += f"🔗 {uname}"

    for admin_id in ADMIN_IDS:
        try:
            await call.bot.send_message(admin_id, admin_text)
        except Exception:
            pass
