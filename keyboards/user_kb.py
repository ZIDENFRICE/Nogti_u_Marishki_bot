from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Booking, Service, Slot
from utils.texts import fmt_dt


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💅 Записаться", callback_data="book_start")
    kb.button(text="📋 Мои записи", callback_data="my_bookings")
    kb.button(text="📸 Примеры работ", callback_data="portfolio_view")
    kb.button(text="🕓 История", callback_data="my_history")
    kb.button(text="ℹ️ О мастере", callback_data="about")
    kb.button(text="⭐ Отзывы", callback_data="reviews_view")
    kb.button(text="✍️ Написать отзыв", callback_data="review_write")
    if is_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin_panel")
    kb.adjust(2, 1, 2, 2, 1)
    return kb.as_markup()


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services:
        kb.button(
            text=f"💅 {s.title} • {s.price}₽",
            callback_data=f"book_svc:{s.id}",
        )
    kb.button(text="⬅️ В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def slots_kb(slots: list[Slot]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in slots:
        kb.button(
            text=f"🕐 {fmt_dt(s.dt)}",
            callback_data=f"book_slot:{s.id}",
        )
    kb.button(text="⬅️ Назад", callback_data="book_start")
    kb.adjust(2)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="book_confirm")
    kb.button(text="❌ Отмена", callback_data="back_main")
    kb.adjust(2)
    return kb.as_markup()


def my_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(
            text=f"❌ Отменить #{b.id} • {b.slot.dt.strftime('%d.%m %H:%M')}",
            callback_data=f"cancel_booking:{b.id}",
        )
    kb.button(text="⬅️ В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def after_visit_kb(booking_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Оставить отзыв", callback_data=f"review:{booking_id}")
    kb.button(text="⬅️ В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def rating_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"rate:{i}")
    kb.adjust(5)
    return kb.as_markup()

def review_skip_photo_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Без фото", callback_data="review_skip_photo")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2)
    return kb.as_markup()

def cancel_kb(callback: str = "cancel_action") -> InlineKeyboardMarkup:
    """Универсальная кнопка Отмена. callback — что делать при нажатии."""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data=callback)
    return kb.as_markup()

def skip_photo_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Без фото", callback_data="booking_skip_photo")
    kb.button(text="❌ Отмена", callback_data="cancel_action")
    kb.adjust(2)
    return kb.as_markup()


def review_bookings_kb(bookings) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(
            text=f"💅 {b.service.title} • {b.slot.dt.strftime('%d.%m %H:%M')}",
            callback_data=f"review_booking:{b.id}",
        )
    kb.button(text="⬅️ В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def booking_photo_skip_kb() -> InlineKeyboardMarkup:
    return skip_photo_kb()