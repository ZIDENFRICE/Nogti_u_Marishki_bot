import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

try:
    cur.execute("ALTER TABLE reviews ADD COLUMN photo_id VARCHAR(256)")
    con.commit()
    print("✅ Колонка photo_id добавлена")
except sqlite3.OperationalError as e:
    print(f"⚠️ {e}")

con.close()
