from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database.db import add_review
from keyboards.user_kb import (
    main_menu_kb,
    rating_kb,
    review_skip_photo_kb,
)
from states.states import ReviewSG
from utils.safe_edit import safe_edit
from utils.texts import DIVIDER

router = Router()


# ============ СТАРТ ОТЗЫВА ============
@router.callback_query(F.data == "review_write")
async def review_write_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(booking_id=None)
    await state.set_state(ReviewSG.rating)
    await safe_edit(
        call,
        f"⭐ <b>Оцени визит</b>\n{DIVIDER}\nПоставь оценку:",
        reply_markup=rating_kb(),
    )


@router.callback_query(F.data.startswith("review:"))
async def review_start(call: CallbackQuery, state: FSMContext):
    booking_id = int(call.data.split(":")[1])
    await state.update_data(booking_id=booking_id)
    await state.set_state(ReviewSG.rating)
    await safe_edit(
        call,
        f"⭐ <b>Оцени визит</b>\n{DIVIDER}\nПоставь оценку:",
        reply_markup=rating_kb(),
    )


# ============ ОЦЕНКА ============
@router.callback_query(ReviewSG.rating, F.data.startswith("rate:"))
async def review_rating(call: CallbackQuery, state: FSMContext):
    rating = int(call.data.split(":")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewSG.text)

    # отмена прямо под текстом
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="cancel_action")

    await safe_edit(
        call,
        f"Оценка: {'⭐' * rating}\n{DIVIDER}\n"
        "Напиши пару слов о визите (или <b>—</b>, чтобы пропустить):",
        reply_markup=kb.as_markup(),
    )


# ============ ТЕКСТ ОТЗЫВА ============
@router.message(ReviewSG.text, F.text)
async def review_text(message: Message, state: FSMContext):
    txt = message.text.strip()
    if txt in ("-", "—", "нет"):
        txt = None
    await state.update_data(text=txt)
    await state.set_state(ReviewSG.photo)

    kb = review_skip_photo_kb()   # там уже будет 2 кнопки: «Без фото» + «Отмена»

    await message.answer(
        f"📷 <b>Хочешь прикрепить фото?</b>\n{DIVIDER}\n"
        "Отправь фото (например, как получился маникюр) "
        "или нажми кнопку ниже, чтобы пропустить.",
        reply_markup=kb,
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
async def _save_review_and_finish(
    message: Message,
    state: FSMContext,
    photo_id: str | None,
    from_callback: bool = False,
):
    data = await state.get_data()
    await state.clear()

    await add_review(
        user_id=message.chat.id,
        rating=data["rating"],
        text=data.get("text"),
        booking_id=data.get("booking_id"),
        photo_id=photo_id,
    )

    text = (
        f"💖 <b>Спасибо за отзыв!</b>\n"
        f"{DIVIDER}\n"
        f"Оценка: {'⭐' * data['rating']}\n"
    )
    if photo_id:
        text += "📷 Фото прикреплено\n"
    text += "\nМне очень важно твоё мнение 🙏"

    # уведомим админов
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                f"⭐ <b>Новый отзыв!</b>\n"
                f"{DIVIDER}\n"
                f"Оценка: {'⭐' * data['rating']}\n"
            )
            if data.get("text"):
                admin_text += f"💬 <i>{data['text']}</i>\n"
            admin_text += f"👤 id{message.chat.id}"

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
