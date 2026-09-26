import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(users)")]

if "terms_accepted" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN terms_accepted BOOLEAN DEFAULT 0")
    print("✅ terms_accepted добавлен")

if "terms_accepted_at" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN terms_accepted_at DATETIME")
    print("✅ terms_accepted_at добавлен")

con.commit()
con.close()
print("✅ Готово")