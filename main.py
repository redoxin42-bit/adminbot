import asyncio
import os
import logging
import sqlite3
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

# --- CONFIG ---
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"
SUPER_ADMINS = [8624430245, 7893084473]
DB_PATH = "howhelper_stats.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[\w/]+')

# --- DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS messages 
                   (user_id INTEGER, full_name TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

def log_message(user_id, full_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO messages VALUES (?, ?, ?)", (user_id, full_name, datetime.now()))
    conn.commit()
    conn.close()

def get_weekly_top():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    week_ago = datetime.now() - timedelta(days=7)
    cur.execute('''SELECT full_name, COUNT(*) as cnt FROM messages 
                   WHERE timestamp > ? GROUP BY user_id 
                   ORDER BY cnt DESC LIMIT 10''', (week_ago,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_profile(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(timestamp), full_name FROM messages WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res # (count, first_seen, name)

# --- RP ACTIONS ---
RP_ACTIONS = {
    "обнять": "🫂 {user} обнял(а) {target}",
    "поцеловать": "💋 {user} поцеловал(а) {target}",
    "ударить": "👊 {user} отвесил(а) леща {target}",
    "кусь": "🦷 {user} сделал(а) кусь {target}",
    "дать пять": "✋ {user} дал(а) пять {target}",
    "погладить": "👋 {user} погладил(а) по голове {target}"
}

# --- RENDER SERVER ---
async def handle(request): return web.Response(text="HowHelper Online")
async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000))).start()

async def is_admin(user_id, chat_id):
    if user_id in SUPER_ADMINS: return True
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ["administrator", "creator"]
    except: return False

# --- MAIN HANDLER ---
@dp.message()
async def global_handler(message: types.Message):
    if not message.text: return
    
    msg_text = message.text.lower().strip()
    
    # 1. Логирование
    log_message(message.from_user.id, message.from_user.full_name)

    # 2. Команда "Профиль"
    if msg_text == "профиль":
        # Если ответ на сообщение - смотрим профиль того, на кого ответили. Иначе - свой.
        target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        count, first_seen, name = get_user_profile(target_user.id)
        
        date_str = datetime.strptime(first_seen, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y') if first_seen else "Неизвестно"
        
        prof_msg = (
            f"👤 <b>Профиль пользователя:</b> {target_user.mention_html()}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Сообщений в базе: <b>{count}</b>\n"
            f"📅 Впервые замечен: <b>{date_str}</b>\n"
            f"🆔 ID: <code>{target_user.id}</code>"
        )
        return await message.answer(prof_msg, parse_mode="HTML")

    # 3. Команда "Топ"
    if msg_text == "топ":
        top_data = get_weekly_top()
        if not top_data: return await message.answer("📊 Статистика пуста.")
        res = "<b>🏆 Топ активности за 7 дней:</b>\n\n"
        for i, (name, count) in enumerate(top_data, 1):
            res += f"{i}. {name} — <b>{count}</b>\n"
        return await message.answer(res, parse_mode="HTML")

    # 4. Модерация (бан, мут, разбан, размут)
    admin_cmds = ["бан", "мут", "разбан", "размут"]
    if msg_text in admin_cmds and await is_admin(message.from_user.id, message.chat.id):
        if not message.reply_to_message: return await message.reply("Ответь на сообщение!")
        t_id = message.reply_to_message.from_user.id
        t_name = message.reply_to_message.from_user.full_name
        try:
            if msg_text == "бан": await bot.ban_chat_member(message.chat.id, t_id)
            elif msg_text == "разбан": await bot.unban_chat_member(message.chat.id, t_id, only_if_banned=True)
            elif msg_text == "мут": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1))
            elif msg_text == "размут": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            await message.answer(f"✅ Исполнено: <b>{msg_text}</b> для {t_name}", parse_mode="HTML")
        except Exception as e: await message.reply(f"Ошибка: {e}")
        return

    # 5. РП-команды
    if msg_text in RP_ACTIONS and message.reply_to_message:
        u_link = message.from_user.mention_html()
        t_link = message.reply_to_message.from_user.mention_html()
        return await message.answer(RP_ACTIONS[msg_text].format(user=u_link, target=t_link), parse_mode="HTML")

    # 6. Старт
    if msg_text == "/start":
        return await message.answer("Здравствуйте, Я HowHelper!")

    # 7. Анти-ссылка
    if URL_PATTERN.search(message.text) and not await is_admin(message.from_user.id, message.chat.id):
        try: await message.delete()
        except: pass

async def main():
    init_db()
    asyncio.create_task(start_webserver())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
