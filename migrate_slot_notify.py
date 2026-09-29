import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(users)")]

if "marketing_accepted" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN marketing_accepted BOOLEAN DEFAULT 1")
    print("✅ marketing_accepted добавлен")
else:
    print("— уже есть")

con.commit()
con.close()
print("✅ Готово")