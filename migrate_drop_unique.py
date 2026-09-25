"""Убирает UNIQUE с bookings.slot_id, пересоздавая таблицу."""
import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

print("Старая схема bookings:")
for row in cur.execute("PRAGMA table_info(bookings)"):
    print(f"   {row[1]} {row[2]}")

# 1. Создаём новую таблицу БЕЗ UNIQUE
cur.execute("""
CREATE TABLE bookings_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NOT NULL,
    service_id INTEGER NOT NULL,
    slot_id INTEGER,
    client_name VARCHAR(128) NOT NULL,
    client_phone VARCHAR(32) NOT NULL,
    note TEXT,
    status VARCHAR(16),
    reminder_sent BOOLEAN DEFAULT 0,
    created_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(service_id) REFERENCES services(id),
    FOREIGN KEY(slot_id) REFERENCES slots(id)
)
""")

# 2. Переносим данные
cur.execute("""
INSERT INTO bookings_new (id, user_id, service_id, slot_id, client_name,
                          client_phone, note, status, reminder_sent, created_at)
SELECT id, user_id, service_id, slot_id, client_name,
       client_phone, note, status, reminder_sent, created_at
FROM bookings
""")

# 3. Удаляем старую, переименовываем
cur.execute("DROP TABLE bookings")
cur.execute("ALTER TABLE bookings_new RENAME TO bookings")

con.commit()

print("\nНовая схема bookings:")
for row in cur.execute("PRAGMA table_info(bookings)"):
    print(f"   {row[1]} {row[2]}")

print("\n✅ Готово. UNIQUE constraint удалён.")
con.close()