import asyncio
import os
import logging
import re
from datetime import timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"
SUPER_ADMINS = [8624430245, 7893084473]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

stats = {"messages": 0, "users": set()}
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[\w/]+')

# --- СПИСОК РП-КОМАНД ---
RP_ACTIONS = {
    "обнять": "🫂 {user} обнял(а) {target}",
    "поцеловать": "💋 {user} поцеловал(а) {target}",
    "ударить": "👊 {user} отвесил(а) леща {target}",
    "кусь": "🦷 {user} сделал(а) кусь {target}",
    "дать_пять": "✋ {user} дал(а) пять {target}",
    "погладить": "👋 {user} погладил(а) по голове {target}"
}

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def is_admin(message: types.Message):
    if message.from_user.id in SUPER_ADMINS: return True
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

# --- ИСПРАВЛЕННЫЙ ОБРАБОТЧИК (РЕПЛАЙ + ТЕКСТ / @USERNAME) ---
@dp.message(F.text.regexp(r'^/(?i)(' + '|'.join(RP_ACTIONS.keys()) + r')'))
async def handle_rp(message: types.Message):
    # Очищаем команду от "/" и юзернейма бота
    parts = message.text.split()
    cmd_raw = parts[0][1:].lower()
    cmd = cmd_raw.split('@')[0]
    
    if cmd not in RP_ACTIONS:
        return

    user = message.from_user.mention_html()
    target = None

    # Вариант 1: Ответ на сообщение (Reply)
    if message.reply_to_message:
        target = message.reply_to_message.from_user.mention_html()
    
    # Вариант 2: Указание цели текстом (@username или имя) после команды
    elif len(parts) > 1:
        target = " ".join(parts[1:])
        # Если это просто @username, оставляем как есть, если нет - можно обернуть в HTML если нужно
    
    else:
        return await message.reply("❕ Ответь на сообщение или напиши имя/юзернейм после команды (например: /обнять @user)")

    text = RP_ACTIONS[cmd].format(user=user, target=target)
    await message.answer(text, parse_mode="HTML")

# --- АДМИН-КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 Бот готов! Работает по реплаю и по @username.\nПример: `/обнять @user` или просто `/обнять` в ответ на сообщение.", parse_mode="Markdown")

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if await is_admin(message):
        await message.reply(f"📊 Статистика:\n📩 Сообщений: `{stats['messages']}`\n👥 Юзеров: `{len(stats['users'])}`", parse_mode="Markdown")

@dp.message(Command("ban", "unban", "mute", "unmute"))
async def admin_mod(message: types.Message):
    if not await is_admin(message) or not message.reply_to_message: return
    cmd = message.text.split()[0][1:].lower()
    t_id = message.reply_to_message.from_user.id
    try:
        if cmd == "ban": await bot.ban_chat_member(message.chat.id, t_id); msg = "забанен"
        if cmd == "unban": await bot.unban_chat_member(message.chat.id, t_id, only_if_banned=True); msg = "разбанен"
        if cmd == "mute": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1)); msg = "в муте на час"
        if cmd == "unmute": await bot.restrict_chat_member(message.chat.id, t_id, types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)); msg = "размучен"
        await message.answer(f"✅ Пользователь {msg}.")
    except Exception as e: await message.reply(f"Ошибка: {e}")

# --- ФИЛЬТР ---
@dp.message()
async def main_filter(message: types.Message):
    stats["messages"] += 1
    stats["users"].add(message.from_user.id)
    if message.text and URL_PATTERN.search(message.text) and not await is_admin(message):
        try: await message.delete()
        except: pass

async def main():
    asyncio.create_task(start_webserver())
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Меню"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="обнять", description="РП: Обнять"),
        BotCommand(command="кусь", description="РП: Кусь"),
        BotCommand(command="ban", description="Бан")
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
