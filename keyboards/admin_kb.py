from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Booking, Service, Slot
from utils.texts import fmt_dt


def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data="adm_stats")
    kb.button(text="📅 Сегодня", callback_data="adm_today")
    kb.button(text="📅 Завтра", callback_data="adm_tomorrow")
    kb.button(text="📋 Все записи", callback_data="adm_bookings")
    kb.button(text="💅 Услуги", callback_data="adm_services")
    kb.button(text="🕐 Слоты", callback_data="adm_slots")
    kb.button(text="📸 Примеры работ", callback_data="adm_portfolio")   # 👈 НОВОЕ
    kb.button(text="👥 Клиенты", callback_data="adm_clients")
    kb.button(text="🔍 Поиск клиента", callback_data="adm_search")
    kb.button(text="⭐ Отзывы", callback_data="adm_reviews")
    kb.button(text="📢 Рассылка", callback_data="adm_broadcast")
    kb.button(text="⬅️ В меню", callback_data="back_main")
    kb.adjust(2, 2, 2, 2, 2, 1)
    return kb.as_markup()


def admin_services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить услугу", callback_data="adm_service_add")
    for s in services:
        kb.button(text=f"🗑 {s.title} ({s.price}₽)", callback_data=f"adm_service_del:{s.id}")
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def admin_slots_kb(slots: list[Slot]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить слот", callback_data="adm_slot_add")
    kb.button(text="➕ Добавить несколько", callback_data="adm_slot_bulk")
    for s in slots:
        mark = "🔴" if s.is_booked else "🟢"
        kb.button(text=f"{mark} {fmt_dt(s.dt)}", callback_data=f"adm_slot_view:{s.id}")
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def slot_detail_kb(slot_id: int, is_booked: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if is_booked:
        kb.button(text="🗑 Удалить (с отменой записи)", callback_data=f"adm_slot_del_force:{slot_id}")
    else:
        kb.button(text="🗑 Удалить слот", callback_data=f"adm_slot_del:{slot_id}")
    kb.button(text="⬅️ К слотам", callback_data="adm_slots")
    kb.adjust(1)
    return kb.as_markup()


def admin_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(
            text=f"📌 #{b.id} • {b.slot.dt.strftime('%d.%m %H:%M')} • {b.client_name}",
            callback_data=f"adm_booking:{b.id}",
        )
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def admin_booking_detail_kb(booking_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнено", callback_data=f"adm_booking_done:{booking_id}")
    kb.button(text="❌ Отменить", callback_data=f"adm_booking_cancel:{booking_id}")
    kb.button(text="⬅️ К записям", callback_data="adm_bookings")
    kb.adjust(2, 1)
    return kb.as_markup()


def back_admin_kb(target: str = "admin_panel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=target)
    return kb.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Отправить всем", callback_data="adm_broadcast_send")
    kb.button(text="❌ Отмена", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def bulk_slots_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Создать", callback_data="adm_slot_bulk_confirm")
    kb.button(text="❌ Отмена", callback_data="adm_slots")
    kb.adjust(1)
    return kb.as_markup()

def admin_portfolio_kb(photos_count: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить фото", callback_data="adm_portfolio_add")
    if photos_count > 0:
        kb.button(text="🗑 Управлять / удалить", callback_data="adm_portfolio_list")
    kb.button(text="⬅️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def admin_portfolio_list_kb(photos: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(photos, 1):
        short = (p.caption[:30] + "…") if p.caption and len(p.caption) > 30 else (p.caption or "без подписи")
        kb.button(text=f"🗑 {i}. {short}", callback_data=f"adm_portfolio_del:{p.id}")
    kb.button(text="⬅️ Назад", callback_data="adm_portfolio")
    kb.adjust(1)
    return kb.as_markup()