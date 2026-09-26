import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

# 1. photo_id в bookings
cols_b = [r[1] for r in cur.execute("PRAGMA table_info(bookings)")]
if "photo_id" not in cols_b:
    cur.execute("ALTER TABLE bookings ADD COLUMN photo_id VARCHAR(256)")
    print("✅ bookings.photo_id добавлен")

# 2. booking_id в reviews
cols_r = [r[1] for r in cur.execute("PRAGMA table_info(reviews)")]
if "booking_id" not in cols_r:
    cur.execute("ALTER TABLE reviews ADD COLUMN booking_id INTEGER")
    print("✅ reviews.booking_id добавлен")

# 3. Таблица portfolio_photos
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
if "portfolio_photos" not in tables:
    cur.execute("""
    CREATE TABLE portfolio_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        photo_id VARCHAR(256) NOT NULL,
        caption TEXT,
        created_at DATETIME
    )
    """)
    print("✅ Таблица portfolio_photos создана")

con.commit()
con.close()
print("\n✅ Миграция завершена")