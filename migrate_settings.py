import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]

if "settings" not in tables:
    cur.execute("""
    CREATE TABLE settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key VARCHAR(64) NOT NULL UNIQUE,
        value TEXT,
        photo_id VARCHAR(256),
        updated_at DATETIME
    )
    """)
    print("✅ Таблица settings создана")
else:
    print("— таблица settings уже есть")

con.commit()
con.close()
print("✅ Готово")