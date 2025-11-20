# -*- coding: utf-8 -*-
import sqlite3
import datetime
import pytz

from telegram import Update
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# ====== SOZLAMALAR ======
BOT_TOKEN = "8549875451:AAGsKZm6PmFA55DgKIBoNH8pABehVjLnRE0"             # BotFather'dan oling
TIMEZONE = pytz.timezone("Asia/Tashkent")      # Tashkent vaqti
GIFT_THRESHOLD = 500                           # Haftada 500+ bet o’qiganlar sovg’a oladi
DB_PATH = "reading_stats.db"                   # SQLite fayli

# ====== BAZA TAYYORLASH ======
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS pages_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    date DATE,
    pages INTEGER
)
""")
conn.commit()

# ====== YORDAMCHI FUNKSIYALAR ======
def today_tz() -> datetime.date:
    return datetime.datetime.now(TIMEZONE).date()

def get_week_range_current(reference_date: datetime.date = None):
    if reference_date is None:
        reference_date = today_tz()
    wd = reference_date.weekday()  # Monday=0 ... Sunday=6
    delta_to_saturday = (wd - 5) % 7
    shanba = reference_date - datetime.timedelta(days=delta_to_saturday)
    juma = shanba + datetime.timedelta(days=6)
    return shanba, juma

def get_week_range_previous(reference_date: datetime.date = None):
    if reference_date is None:
        reference_date = today_tz()
    wd = reference_date.weekday()
    juma = reference_date - datetime.timedelta(days=(wd - 4))
    shanba = juma - datetime.timedelta(days=6)
    return shanba, juma

def username_or_name(update: Update):
    user = update.effective_user
    uid = user.id
    uname = user.username or ""
    fname = user.full_name or (user.first_name or "Foydalanuvchi")
    return uid, uname, fname

def insert_log(user_id, username, full_name, date, pages):
    cursor.execute(
        "INSERT INTO pages_log (user_id, username, full_name, date, pages) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, full_name, date.isoformat(), pages)
    )
    conn.commit()

def sum_user_week(user_id, start_date, end_date):
    cursor.execute("""
        SELECT COALESCE(SUM(pages), 0)
        FROM pages_log
        WHERE user_id = ? AND date >= ? AND date <= ?
    """, (user_id, start_date.isoformat(), end_date.isoformat()))
    return cursor.fetchone()[0] or 0

def leaderboard_week(start_date, end_date, limit=10):
    cursor.execute("""
        SELECT full_name, COALESCE(SUM(pages), 0) AS total
        FROM pages_log
        WHERE date >= ? AND date <= ?
        GROUP BY user_id, full_name
        ORDER BY total DESC
        LIMIT ?
    """, (start_date.isoformat(), end_date.isoformat(), limit))
    return cursor.fetchall()

def full_week_totals(start_date, end_date):
    cursor.execute("""
        SELECT full_name, COALESCE(SUM(pages), 0) AS total
        FROM pages_log
        WHERE date >= ? AND date <= ?
        GROUP BY user_id, full_name
        ORDER BY total DESC
    """, (start_date.isoformat(), end_date.isoformat()))
    return cursor.fetchall()

# ====== BUYRUQLAR ======
def start_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Salom! 📚 Bu bot haftalik o‘qish statistikasini yuritadi.\n\n"
        "Asosiy buyruqlar:\n"
        "• /pages <son> — bugungi o‘qigan betlaringizni yuboring.\n"
        "• /my_stats — joriy haftadagi shaxsiy statistika.\n"
        "• /leaderboard — joriy haftaning reytingi.\n"
        "• /report — o‘tgan haftaning yakuniy hisobotini ko‘rish.\n\n"
        "Hafta: shanba → juma. Hisobot: yakshanba."
    )

def pages_cmd(update: Update, context: CallbackContext):
    uid, uname, fname = username_or_name(update)
    try:
        pages = int(context.args[0])
        if pages <= 0 or pages > 2000:
            update.message.reply_text("❗ Iltimos, 1–2000 oralig‘ida ijobiy son kiriting.")
            return
    except (IndexError, ValueError):
        update.message.reply_text("❗ Foydalanish: /pages <betlar soni> (masalan: /pages 45)")
        return

    d = today_tz()
    insert_log(uid, uname, fname, d, pages)
    update.message.reply_text(f"✅ {fname}, bugun {pages} bet o‘qiganingiz saqlandi. Davom eting!")

def my_stats_cmd(update: Update, context: CallbackContext):
    uid, uname, fname = username_or_name(update)
    start_date, end_date = get_week_range_current()
    total = sum_user_week(uid, start_date, end_date)

    msg = (
        f"📖 {fname}, joriy hafta ("
        f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}) bo‘yicha:\n"
        f"• Umumiy: {total} bet"
    )
    if total < GIFT_THRESHOLD:
        msg += f"\n💡 Sovg‘a uchun yana {GIFT_THRESHOLD - total} bet o‘qing!"
    else:
        msg += "\n🎁 Tabriklaymiz! Siz 500+ bet o‘qidiz va sovg‘aga loyiq bo‘ldingiz!"
    update.message.reply_text(msg)

def leaderboard_cmd(update: Update, context: CallbackContext):
    start_date, end_date = get_week_range_current()
    rows = leaderboard_week(start_date, end_date, limit=10)
    if not rows:
        update.message.reply_text("ℹ️ Hali reyting uchun ma’lumot yo‘q.")
        return

    lines = [f"🏆 Haftalik reyting ( {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')} ):"] 
    for i, (name, total) in enumerate(rows, 1):
        badge = " ✅" if total >= GIFT_THRESHOLD else ""
        lines.append(f"{i}. {name} — {total} bet{badge}")
    update.message.reply_text("\n".join(lines))

def report_cmd(update: Update, context: CallbackContext):
    start_date, end_date = get_week_range_previous()
    rows = full_week_totals(start_date, end_date)
    msg = build_week_report_message(rows, start_date, end_date)
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)

def build_week_report_message(rows, start_date, end_date) -> str:
    if not rows:
        return (
            f"📊 O‘tgan hafta ({start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}) uchun ma’lumot topilmadi."
        )
    lines = [
        f"📊 Haftalik yakuniy hisobot ( {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')} ):"
    ]
    winners = []
    for name, total in rows:
        mark = "✅" if total >= GIFT_THRESHOLD else ""
        lines.append(f"• {name}: {total} bet {mark}")
        if total >= GIFT_THRESHOLD:
            winners.append(name)
    if winners:
        lines.append("")
        lines.append(f"🎁 Tabriklaymiz: {', '.join(winners)} — 500+ bet! Sovg‘a kitobga ega bo‘ldingiz!")
    else:
        lines.append("")
        lines.append("💡 Bu hafta 500+ bet o‘qiganlar topilmadi. Keyingi haftada omad!")
    return "\n".join(lines)

# ====== MAIN ======
def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("pages", pages_cmd))
    dp.add_handler(CommandHandler("my_stats", my_stats_cmd))
    dp.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    dp.add_handler(CommandHandler("report", report_cmd))

    print("Bot ishga tushdi. Endi foydalanuvchilar botga shaxsiy xabar yuborishlari mumkin.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
