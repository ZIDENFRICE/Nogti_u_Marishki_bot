"""Проверка базы данных и её целостности."""
import sqlite3
import os

DB = "data/bot.db"

if not os.path.exists(DB):
    print(f"❌ База не найдена: {DB}")
    exit(1)

con = sqlite3.connect(DB)
cur = con.cursor()

print("=== ТАБЛИЦЫ ===")
tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
)]
for t in tables:
    print(" -", t)

expected = ["users", "services", "slots", "bookings", "broadcasts", "reviews"]
for t in expected:
    if t not in tables:
        print(f"❌ НЕТ таблицы: {t}")

print("\n=== КОЛИЧЕСТВО ЗАПИСЕЙ ===")
for t in expected:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f" - {t}: {n}")
    except sqlite3.OperationalError:
        print(f" - {t}: ❌ НЕТ ТАБЛИЦЫ")

print("\n=== СТРУКТУРА КЛЮЧЕВЫХ ТАБЛИЦ ===")
for t in ["bookings", "reviews"]:
    print(f"\n{t}:")
    for row in cur.execute(f"PRAGMA table_info({t})"):
        print(f"   {row[1]} ({row[2]})")

# ПРОВЕРКА КОНСИСТЕНТНОСТИ
print("\n=== ПРОВЕРКА КОНСИСТЕНТНОСТИ ===")

# 1. Слоты, помеченные занятыми, но без активных записей
bad1 = cur.execute("""
    SELECT s.id, s.dt FROM slots s
    LEFT JOIN bookings b ON b.slot_id = s.id AND b.status = 'active'
    WHERE s.is_booked = 1 AND b.id IS NULL
""").fetchall()
if bad1:
    print(f"⚠️ Занятых слотов без записи: {len(bad1)}")
    for r in bad1[:5]:
        print(f"   слот {r[0]} на {r[1]}")
else:
    print("✅ Все занятые слоты имеют активные записи")

# 2. Слоты свободные, но с активной записью
bad2 = cur.execute("""
    SELECT s.id, s.dt, b.id FROM slots s
    JOIN bookings b ON b.slot_id = s.id AND b.status = 'active'
    WHERE s.is_booked = 0
""").fetchall()
if bad2:
    print(f"⚠️ Свободных слотов с записью: {len(bad2)}")
else:
    print("✅ Все слоты с записями помечены занятыми")

# 3. Записи без пользователя
bad3 = cur.execute("""
    SELECT b.id FROM bookings b
    LEFT JOIN users u ON u.id = b.user_id
    WHERE u.id IS NULL
""").fetchall()
if bad3:
    print(f"⚠️ Записей без пользователя: {len(bad3)}")
else:
    print("✅ Все записи имеют пользователя")

# 4. Записи без услуги
bad4 = cur.execute("""
    SELECT b.id FROM bookings b
    LEFT JOIN services s ON s.id = b.service_id
    WHERE s.id IS NULL
""").fetchall()
if bad4:
    print(f"⚠️ Записей без услуги: {len(bad4)}")
else:
    print("✅ Все записи имеют услугу")

con.close()