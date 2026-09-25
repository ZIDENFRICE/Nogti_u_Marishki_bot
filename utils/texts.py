"""
Красивые тексты и разделители для бота.
"""

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"
DIVIDER_SHORT = "━━━━━━━━━━━━━"
DIVIDER_STAR = "✦ ─────────── ✦"


def money(v: int) -> str:
    return f"{v:,}".replace(",", " ") + " ₽"


def fmt_dt(dt) -> str:
    months = ["янв", "фев", "мар", "апр", "мая", "июн",
              "июл", "авг", "сен", "окт", "ноя", "дек"]
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    return f"{weekdays[dt.weekday()]}, {dt.day} {months[dt.month-1]} • {dt.strftime('%H:%M')}"


def fmt_date(dt) -> str:
    months = ["января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    weekdays = ["Понедельник", "Вторник", "Среда", "Четверг",
                "Пятница", "Суббота", "Воскресенье"]
    return f"{weekdays[dt.weekday()]}, {dt.day} {months[dt.month-1]} {dt.year}"


def stars(n: int) -> str:
    return "⭐" * n + "☆" * (5 - n)


def booking_card(b, for_admin: bool = False, index: int | None = None) -> str:
    """Красивая карточка записи."""
    head = f"#{b.id}"
    if index is not None:
        head = f"{index}. Запись #{b.id}"

    lines = [
        f"<b>{head}</b>",
        DIVIDER_SHORT,
        f"💅 <b>{b.service.title}</b>",
        f"🗓 {fmt_dt(b.slot.dt)}",
        f"⏱ {b.service.duration_min} мин • 💰 {money(b.service.price)}",
        f"👤 {b.client_name}",
        f"📞 <code>{b.client_phone}</code>",
    ]
    if b.note:
        lines.append(f"📝 <i>{b.note}</i>")

    if for_admin and b.user:
        uname = f"@{b.user.username}" if b.user.username else f"id{b.user_id}"
        lines.append(f"🔗 {uname}")
    return "\n".join(lines)


def service_card(s, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    text = f"{prefix}<b>{s.title}</b>\n"
    if s.description:
        text += f"   <i>{s.description}</i>\n"
    text += f"   💰 {money(s.price)} • ⏱ {s.duration_min} мин"
    return text
