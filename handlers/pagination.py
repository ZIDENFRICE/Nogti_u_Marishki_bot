"""
Единый обработчик нажатия ◀️ ▶️ для всех разделов.
Он обновляет страницу и вызывает хендлер рендера по ключу.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery

from utils.pagination import set_page

router = Router()


@router.callback_query(F.data == "pag_noop")
async def pag_noop(call: CallbackQuery):
    """Кнопка-заглушка по центру (номер страницы)."""
    await call.answer()


@router.callback_query(F.data.startswith("pag:"))
async def pag_switch(call: CallbackQuery):
    _, key, page = call.data.split(":")
    page = int(page)
    set_page(key, page)

    # Каждый раздел сам знает, что перерисовать
    RENDERERS = {
        "reviews_user": "handlers.user:render_reviews_user",
        "reviews_adm": "handlers.admin:render_reviews_adm",
        "services_user": "handlers.booking:render_services_user",
        "services_adm": "handlers.admin:render_services_adm",
        "bookings_adm": "handlers.admin:render_bookings_adm",
        "clients_adm": "handlers.admin:render_clients_adm",
        "slots_adm": "handlers.admin:render_slots_adm",
    }

    path = RENDERERS.get(key)
    if not path:
        await call.answer("Раздел устарел, открой заново")
        return

    module_name, func_name = path.split(":")
    import importlib
    module = importlib.import_module(module_name)
    render_func = getattr(module, func_name)

    await render_func(call)
    await call.answer()
