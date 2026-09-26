from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.db import (
    add_review, get_done_bookings_for_review,
    can_leave_review, get_booking,
)
from keyboards.user_kb import (
    rating_kb, main_menu_kb, review_skip_photo_kb,
    review_bookings_kb,
)
from states.states import ReviewSG
from utils.texts import DIVIDER
from utils.safe_edit import safe_edit

router = Router()


# ============ СТАРТ ============
@router.callback_query(F.data == "review_write")
async def review_write_start(call: CallbackQuery, state: FSMContext):
    bookings = await get_done_bookings_for_review(call.from_user.id)

    if not bookings:
        await call.answer(
            "⚠️ Оставить отзыв можно только после посещения.\n"
            "Запишись на услугу, а после визита мастер отметит тебя.",
            show_alert=True,
        )
        return

    if len(bookings) == 1:
        b = bookings[0]
        await state.update_data(booking_id=b.id)
        await state.set_state(ReviewSG.rating)
        await safe_edit(
            call,
            f"⭐ <b>Оцени визит</b>\n{DIVIDER}\n"
            f"💅 {b.service.title}\n"
            f"🗓 {b.slot.dt.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Поставь оценку:",
            reply_markup=rating_kb(),
        )
    else:
        await state.set_state(ReviewSG.choosing_booking)
        await safe_edit(
            call,
            f"⭐ <b>Выбери визит для отзыва</b>\n{DIVIDER}",
            reply_markup=review_bookings_kb(bookings),
        )


@router.callback_query(ReviewSG.choosing_booking, F.data.startswith("review_booking:"))
async def review_choose_booking(call: CallbackQuery, state: FSMContext):
    booking_id = int(call.data.split(":")[1])
    ok, reason = await can_leave_review(call.from_user.id, booking_id)
    if not ok:
        await call.answer(f"⚠️ {reason}", show_alert=True)
        return
    await state.update_data(booking_id=booking_id)
    await state.set_state(ReviewSG.rating)
    b = await get_booking(booking_id)
    await safe_edit(
        call,
        f"⭐ <b>Оцени визит</b>\n{DIVIDER}\n"
        f"💅 {b.service.title}\n"
        f"🗓 {b.slot.dt.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Поставь оценку:",
        reply_markup=rating_kb(),
    )


# ============ БЫСТРЫЙ ПЕРЕХОД ИЗ УВЕДОМЛЕНИЯ ============
@router.callback_query(F.data.startswith("review:"))
async def review_from_button(call: CallbackQuery, state: FSMContext):
    booking_id = int(call.data.split(":")[1])
    ok, reason = await can_leave_review(call.from_user.id, booking_id)
    if not ok:
        await call.answer(f"⚠️ {reason}", show_alert=True)
        return
    await state.update_data(booking_id=booking_id)
    await state.set_state(ReviewSG.rating)
    b = await get_booking(booking_id)
    await safe_edit(
        call,
        f"⭐ <b>Оцени визит</b>\n{DIVIDER}\n"
        f"💅 {b.service.title}\n"
        f"🗓 {b.slot.dt.strftime('%d.%m.%Y %H:%M')}\n\n"
        "Поставь оценку:",
        reply_markup=rating_kb(),
    )


# ============ ОЦЕНКА ============
@router.callback_query(ReviewSG.rating, F.data.startswith("rate:"))
async def review_rating(call: CallbackQuery, state: FSMContext):
    rating = int(call.data.split(":")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewSG.text)
    await safe_edit(
        call,
        f"Оценка: {'⭐' * rating}\n{DIVIDER}\n"
        "Напиши пару слов о визите (или <b>—</b>, чтобы пропустить):",
    )


# ============ ТЕКСТ ============
@router.message(ReviewSG.text, F.text)
async def review_text(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt in ("-", "—", "нет"):
        txt = None
    await state.update_data(text=txt)
    await state.set_state(ReviewSG.photo)
    await message.answer(
        f"📷 <b>Хочешь прикрепить фото?</b>\n{DIVIDER}\n"
        "Отправь фото или нажми «Без фото».",
        reply_markup=review_skip_photo_kb(),
    )


# ============ ФОТО ============
@router.message(ReviewSG.photo, F.photo)
async def review_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await _save_review_and_finish(message, state, photo_id)


@router.callback_query(ReviewSG.photo, F.data == "review_skip_photo")
async def review_skip_photo(call: CallbackQuery, state: FSMContext):
    await _save_review_and_finish(call.message, state, None, from_callback=True)
    await call.answer()


# ============ СОХРАНЕНИЕ ============
async def _save_review_and_finish(message: Message, state: FSMContext,
                                   photo_id: str | None, from_callback: bool = False):
    data = await state.get_data()
    await state.clear()

    booking_id = data.get("booking_id")
    user_id = message.chat.id

    ok, reason = await can_leave_review(user_id, booking_id)
    if not ok:
        text = f"⚠️ <b>Не удалось сохранить отзыв</b>\n{DIVIDER}\n{reason}"
        if from_callback:
            try:
                await message.edit_text(text, reply_markup=main_menu_kb(False))
            except Exception:
                await message.answer(text, reply_markup=main_menu_kb(False))
        else:
            await message.answer(text, reply_markup=main_menu_kb(False))
        return

    await add_review(
        user_id=user_id,
        rating=data["rating"],
        text=data.get("text"),
        booking_id=booking_id,
        photo_id=photo_id,
    )

    text = (
        f"💖 <b>Спасибо за отзыв!</b>\n{DIVIDER}\n"
        f"Оценка: {'⭐' * data['rating']}\n"
    )
    if photo_id:
        text += "📷 Фото прикреплено\n"
    text += "\nМне очень важно твоё мнение 🙏"

    for admin_id in ADMIN_IDS:
        try:
            b = await get_booking(booking_id) if booking_id else None
            service_line = f"💅 {b.service.title}\n" if b and b.service else ""
            admin_text = (
                f"⭐ <b>Новый отзыв!</b>\n{DIVIDER}\n{service_line}"
                f"Оценка: {'⭐' * data['rating']}\n"
            )
            if data.get("text"):
                admin_text += f"💬 <i>{data['text']}</i>\n"
            admin_text += f"👤 id{user_id}"
            if photo_id:
                await message.bot.send_photo(admin_id, photo_id, caption=admin_text)
            else:
                await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            print(f"[REVIEW NOTIFY FAIL] {admin_id}: {e}")

    if from_callback:
        try:
            await message.edit_text(text, reply_markup=main_menu_kb(False))
        except Exception:
            await message.answer(text, reply_markup=main_menu_kb(False))
    else:
        await message.answer(text, reply_markup=main_menu_kb(False))