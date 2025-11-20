import sqlite3

# Bazaga ulanish
conn = sqlite3.connect("book_readers.db")
cursor = conn.cursor()

# Jadvaldagi barcha yozuvlarni olish
cursor.execute("SELECT * FROM readers")
rows = cursor.fetchall()

# Natijani chiqarish
for row in rows:
    print(row)

# Ulanishni yopish
conn.close()
