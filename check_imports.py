"""Проверка, что все модули импортируются без ошибок."""
import importlib
import traceback

MODULES = [
    "config",
    "bot",
    "database.db",
    "database.models",
    "handlers.user",
    "handlers.admin",
    "handlers.booking",
    "handlers.reviews",
    "handlers.pagination",
    "keyboards.user_kb",
    "keyboards.admin_kb",
    "filters.is_admin",
    "services.scheduler",
    "states.states",
    "utils.texts",
    "utils.safe_edit",
    "utils.pagination",
    "middlewares.edit_error",
]

ok, fail = 0, 0
for m in MODULES:
    try:
        importlib.import_module(m)
        print(f"✅ {m}")
        ok += 1
    except Exception as e:
        print(f"❌ {m}: {e}")
        traceback.print_exc()
        fail += 1

print(f"\nИтог: {ok} ок, {fail} ошибок")
