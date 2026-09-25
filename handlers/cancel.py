"""
Единый обработчик отмены любого действия.
Сбрасывает FSM и возвращает в меню (или админку).
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from keyboards.admin_kb import admin_menu_kb
from keyboards.user_kb import main_menu_kb
from utils.safe_edit import safe_edit

router = Router()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(call: CallbackQuery, state: FSMContext):
    """Отмена действия клиента — в главное меню."""
    await state.clear()
    await safe_edit(
        call,
        "❌ <b>Действие отменено</b>\n\nЧем могу помочь?",
        reply_markup=main_menu_kb(call.from_user.id in ADMIN_IDS),
    )
    await call.answer()


@router.callback_query(F.data == "cancel_admin")
async def cancel_admin(call: CallbackQuery, state: FSMContext):
    """Отмена действия админа — в админ-панель."""
    await state.clear()
    await safe_edit(
        call,
        "❌ <b>Действие отменено</b>\n\n⚙️ Админ-панель:",
        reply_markup=admin_menu_kb(),
    )
    await call.answer()
