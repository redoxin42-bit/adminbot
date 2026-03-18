import asyncio
import os
import logging
import sqlite3
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

# --- ПЕРСОНАЛЬНЫЕ ДАННЫЕ (БЕЗ ИЗМЕНЕНИЙ) ---
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"
SUPER_ADMINS = [8624430245, 7893084473]
DB_PATH = "chat_stats.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[\w/]+')

# --- DATABASE ENGINE (ДЛЯ КОМАНДЫ "ТОП") ---
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

# --- ПОЛНЫЙ СПИСОК РП-ДЕЙСТВИЙ ---
RP_ACTIONS = {
    "обнять": "🫂 {user} обнял(а) {target}",
    "поцеловать": "💋 {user} поцеловал(а) {target}",
    "ударить": "👊 {user} отвесил(а) леща {target}",
    "кусь": "🦷 {user} сделал(а) кусь {target}",
    "дать пять": "✋ {user} дал(а) пять {target}",
    "погладить": "👋 {user} погладил(а) по голове {target}"
  "выебать": "{user} выебал(а) {target}
}

# --- SERVER CORE ---
async def handle(request): return web.Response(text="Erafox System Online")
async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000))).start()

async def is_admin(message: types.Message):
    if message.from_user.id in SUPER_ADMINS: return True
    try:
        m = await message.chat.get_member(message.from_user.id)
        return m.status in ["administrator", "creator"]
    except: return False

# --- ОБЪЕДИНЕННЫЙ ОБРАБОТЧИК (ALL-IN-ONE) ---
@dp.message()
async def core_handler(message: types.Message):
    if not message.text: return
    
    msg_text = message.text.lower().strip()
    user_link = message.from_user.mention_html()
    
    # 1. Сбор статистики (для Топа)
    log_message(message.from_user.id, message.from_user.full_name)

    # 2. Команда "Топ" (за неделю)
    if msg_text == "топ":
        top = get_weekly_top()
        if not top: return await message.answer("📉 Статистика пуста.")
        res = "<b>🏆 Топ за 7 дней:</b>\n\n"
        for i, (name, count) in enumerate(top, 1):
            res += f"{i}. {name} — <b>{count}</b>\n"
        return await message.answer(res, parse_mode="HTML")

    # 3. Модерация на русском (Бан, Мут, Разбан, Размут)
    admin_cmd = ["бан", "разбан", "мут", "размут"]
    if msg_text in admin_cmd and await is_admin(message):
        if not message.reply_to_message: return await message.reply("Ответь на сообщение!")
        t_id = message.reply_to_message.from_user.id
        try:
            if msg_text == "бан": await bot.ban_chat_member(message.chat.id, t_id)
            elif msg_text == "разбан": await bot.unban_chat_member(message.chat.id, t_id, only_if_banned=True)
            elif msg_text == "мут": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1))
            elif msg_text == "размут": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
            await message.answer(f"✅ Готово: <b>{msg_text}</b>", parse_mode="HTML")
        except Exception as e: await message.reply(f"Ошибка прав: {e}")
        return

    # 4. РП-команды (Обнять, Кусь и т.д.)
    if msg_text in RP_ACTIONS:
        if message.reply_to_message:
            target_link = message.reply_to_message.from_user.mention_html()
            return await message.answer(RP_ACTIONS[msg_text].format(user=user_link, target=target_link), parse_mode="HTML")
        return await message.reply("Ответь этим словом на чье-то сообщение!")

    # 5. Анти-ссылка
    if URL_PATTERN.search(message.text) and not await is_admin(message):
        try: await message.delete()
        except: pass

# --- STARTUP ---
async def main():
    init_db()
    asyncio.create_task(start_webserver())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
