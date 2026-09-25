import sqlite3

con = sqlite3.connect("data/bot.db")
cur = con.cursor()

def show(title, query):
    print(f"\n=== {title} ===")
    try:
        rows = cur.execute(query).fetchall()
        if not rows:
            print("  (пусто)")
        for r in rows:
            print("  ", r)
    except sqlite3.OperationalError as e:
        print(f"  ❌ {e}")

show("Пользователи", "SELECT id, username, full_name FROM users LIMIT 10")
show("Услуги", "SELECT id, title, price, duration_min FROM services")
show("Слоты", "SELECT id, dt, is_booked FROM slots ORDER BY dt LIMIT 20")
show("Записи", """
    SELECT b.id, b.client_name, b.client_phone, s.title, sl.dt, b.status
    FROM bookings b
    JOIN services s ON s.id = b.service_id
    JOIN slots sl ON sl.id = b.slot_id
    ORDER BY b.id DESC LIMIT 10
""")
show("Отзывы", "SELECT id, user_id, rating, substr(text,1,40), photo_id FROM reviews ORDER BY id DESC LIMIT 10")
show("Рассылки", "SELECT id, substr(text,1,30), sent_count, failed_count FROM broadcasts ORDER BY id DESC LIMIT 5")

con.close()
