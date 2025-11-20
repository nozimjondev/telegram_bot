import sqlite3
import csv

# 1. Bazaga ulanish
conn = sqlite3.connect("book_readers.db")
cursor = conn.cursor()

# 2. Jadvaldagi barcha yozuvlarni olish
cursor.execute("SELECT * FROM readers")
rows = cursor.fetchall()

# 3. CSV faylga yozish
with open("readers_export.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    # Ustun nomlarini yozish
    writer.writerow(["user_id", "username", "pages_read", "date"])
    # Ma'lumotlarni yozish
    writer.writerows(rows)

# 4. Ulanishni yopish
conn.close()

print("✅ Ma'lumotlar readers_export.csv fayliga eksport qilindi.")
