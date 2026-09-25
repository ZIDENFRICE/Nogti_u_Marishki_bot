"""
Универсальная пагинация для inline-кнопок.

Как работает:
- Ключ пагинации (например, "reviews", "services_adm") — уникален для каждого раздела.
- В памяти бота храним список ID элементов и текущую страницу.
- Кнопки ◀️ ▶️ несут callback вида: pag:{key}:{page}
"""
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
# Хранилище: {key: {"ids": [...], "page": int, "per_page": int}}
# ============================================================
_PAGINATION_CACHE: dict[str, dict[str, Any]] = {}


def register_pagination(key: str, ids: list[Any], per_page: int = 5) -> int:
    """
    Регистрирует список для пагинации. Возвращает кол-во страниц.
    Если список изменился — сбрасывает страницу в 0.
    """
    total_pages = max(1, (len(ids) + per_page - 1) // per_page)
    old = _PAGINATION_CACHE.get(key)
    same = old and old["ids"] == ids and old["per_page"] == per_page
    _PAGINATION_CACHE[key] = {
        "ids": ids,
        "page": old["page"] if same else 0,
        "per_page": per_page,
    }
    return total_pages


def get_page_info(key: str) -> tuple[list[Any], int, int]:
    """Возвращает (ids текущей страницы, номер страницы, всего страниц)."""
    data = _PAGINATION_CACHE.get(key)
    if not data:
        return [], 0, 1
    ids = data["ids"]
    per_page = data["per_page"]
    page = data["page"]
    total_pages = max(1, (len(ids) + per_page - 1) // per_page)
    start = page * per_page
    end = start + per_page
    return ids[start:end], page, total_pages


def set_page(key: str, page: int) -> bool:
    """Устанавливает страницу. Возвращает True, если что-то изменилось."""
    data = _PAGINATION_CACHE.get(key)
    if not data:
        return False
    ids = data["ids"]
    per_page = data["per_page"]
    total_pages = max(1, (len(ids) + per_page - 1) // per_page)
    if page < 0 or page >= total_pages:
        return False
    data["page"] = page
    return True


def clear_pagination(key: str):
    _PAGINATION_CACHE.pop(key, None)


# ============================================================
# Клавиатура навигации
# ============================================================
def pagination_kb(
    key: str,
    page: int,
    total_pages: int,
    extra_buttons: list[tuple[str, str]] | None = None,
    back_callback: str | None = None,
    back_text: str = "⬅️ Назад",
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура пагинации.

    key            — ключ раздела (совпадает с register_pagination)
    page           — текущая страница (0-indexed)
    total_pages    — всего страниц
    extra_buttons  — список доп. кнопок ДО навигации (text, callback)
    back_callback  — куда вернуться по «Назад»
    """
    kb = InlineKeyboardBuilder()

    if extra_buttons:
        for text, cb in extra_buttons:
            kb.button(text=text, callback_data=cb)

    # навигация
    if total_pages > 1:
        if page > 0:
            kb.button(text="⬅️", callback_data=f"pag:{key}:{page - 1}")
        else:
            kb.button(text="⏺", callback_data="pag_noop")

        kb.button(text=f"{page + 1} / {total_pages}", callback_data="pag_noop")

        if page < total_pages - 1:
            kb.button(text="➡️", callback_data=f"pag:{key}:{page + 1}")
        else:
            kb.button(text="⏺", callback_data="pag_noop")

    if back_callback:
        kb.button(text=back_text, callback_data=back_callback)

    # раскладка: доп кнопки по одной, потом навигация в строке
    if extra_buttons:
        rows = [1] * len(extra_buttons)
        if total_pages > 1:
            rows.append(3)
        if back_callback:
            rows.append(1)
        kb.adjust(*rows)
    else:
        if total_pages > 1 and back_callback:
            kb.adjust(3, 1)
        elif total_pages > 1:
            kb.adjust(3)
        else:
            kb.adjust(1)

    return kb.as_markup()
