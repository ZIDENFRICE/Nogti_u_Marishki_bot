"""Безопасное редактирование сообщений."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputMediaPhoto


async def safe_edit(call: CallbackQuery, text: str, reply_markup=None):
    """
    Пытается отредактировать сообщение.
    Если не получается (медиа, идентичный текст) — удаляет и шлёт новое.
    """
    try:
        await call.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        err = str(e).lower()
        if (
            "no text in the message" in err
            or "message is not modified" in err
            or "message can't be edited" in err
            or "message to edit not found" in err
        ):
            try:
                await call.message.delete()
            except Exception:
                pass
            try:
                await call.message.answer(text, reply_markup=reply_markup)
            except Exception:
                await call.bot.send_message(
                    call.from_user.id, text, reply_markup=reply_markup
                )
        else:
            raise



async def safe_render(call: CallbackQuery, text: str, photo_id: str | None = None,
                      reply_markup=None):
    """
    Универсальный рендер сообщения:
    - Если photo_id передан → показываем фото с подписью.
    - Если нет → показываем текст.
    - Пытается отредактировать текущее сообщение, если тип совпадает.
    - Иначе удаляет и отправляет новое.
    """
    current = call.message

    has_photo_now = bool(current.photo)

    try:
        if photo_id and has_photo_now:
            # фото → фото
            media = InputMediaPhoto(media=photo_id, caption=text)
            await current.edit_media(media, reply_markup=reply_markup)
            return
        if photo_id and not has_photo_now:
            # текст → фото
            await current.delete()
            await current.answer_photo(photo_id, caption=text, reply_markup=reply_markup)
            return
        if not photo_id and not has_photo_now:
            # текст → текст
            await current.edit_text(text, reply_markup=reply_markup)
            return
        if not photo_id and has_photo_now:
            # фото → текст
            await current.delete()
            await current.answer(text, reply_markup=reply_markup)
            return
    except TelegramBadRequest as e:
        err = str(e).lower()
        # "message is not modified" — просто игнор
        if "message is not modified" in err:
            return
        # остальные — удаляем и отправляем заново
        try:
            await current.delete()
        except Exception:
            pass
        if photo_id:
            await current.answer_photo(photo_id, caption=text, reply_markup=reply_markup)
        else:
            await current.answer(text, reply_markup=reply_markup)
