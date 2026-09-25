"""Проверка, что все нужные файлы и папки на месте."""
import os

REQUIRED = [
    "bot.py",
    "config.py",
    ".env",
    "database/__init__.py",
    "database/db.py",
    "database/models.py",
    "handlers/__init__.py",
    "handlers/user.py",
    "handlers/admin.py",
    "handlers/booking.py",
    "handlers/reviews.py",
    "handlers/pagination.py",
    "keyboards/__init__.py",
    "keyboards/user_kb.py",
    "keyboards/admin_kb.py",
    "filters/__init__.py",
    "filters/is_admin.py",
    "services/__init__.py",
    "services/scheduler.py",
    "states/__init__.py",
    "states/states.py",
    "utils/__init__.py",
    "utils/texts.py",
    "utils/safe_edit.py",
    "utils/pagination.py",
    "middlewares/__init__.py",
    "middlewares/edit_error.py",
]

missing = [f for f in REQUIRED if not os.path.exists(f)]
if missing:
    print("❌ Отсутствуют файлы:")
    for m in missing:
        print(f"   - {m}")
else:
    print("✅ Все файлы на месте")

# проверка .env
if os.path.exists(".env"):
    with open(".env", encoding="utf-8") as f:
        env = f.read()
    for key in ["BOT_TOKEN", "ADMIN_IDS"]:
        if key not in env:
            print(f"⚠️ В .env нет {key}")
        else:
            print(f"✅ .env содержит {key}")