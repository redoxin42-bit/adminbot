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

# --- СЕРВЕР ДЛЯ RENDER (АНТИ-СПЯЧКА) ---
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

# --- ПРОВЕРКА ПРАВ ---
async def is_admin(message: types.Message):
    if message.from_user.id in SUPER_ADMINS:
        return True
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# --- УЛУЧШЕННЫЙ ОБРАБОТЧИК РП-КОМАНД ---
@dp.message(Command(*RP_ACTIONS.keys(), ignore_case=True))
async def handle_rp(message: types.Message):
    # Извлекаем команду, убираем слэш и юзернейм бота если он есть
    cmd_text = message.text.split()[0].lower()
    cmd = cmd_text.split('@')[0][1:] 
    
    user = message.from_user.mention_html()
    target = ""

    if message.reply_to_message:
        target = message.reply_to_message.from_user.mention_html()
    elif len(message.text.split()) > 1:
        target = " ".join(message.text.split()[1:])
    else:
        return await message.reply("❕ Ответь на сообщение или напиши имя/юзернейм после команды.")

    if cmd in RP_ACTIONS:
        text = RP_ACTIONS[cmd].format(user=user, target=target)
        await message.answer(text, parse_mode="HTML")

# --- АДМИН-КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    status = "👑 Главный админ" if message.from_user.id in SUPER_ADMINS else "👤 Участник"
    await message.answer(
        f"👋 **Привет! Я админ-бот.**\nТвой статус: {status}\n\n"
        "🎭 **РП-команды работают!** Просто напиши `/обнять` или `/кусь`.\n"
        "🛡 **Модерация:** /ban, /unban, /mute, /unmute\n"
        "📊 **Статистика:** /stats",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if await is_admin(message):
        await message.reply(f"📊 Статистика:\n📩 Сообщений: `{stats['messages']}`\n👥 Юзеров: `{len(stats['users'])}`", parse_mode="Markdown")

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer(f"🚫 {message.reply_to_message.from_user.full_name} забанен.")
        except Exception as e: await message.reply(f"Ошибка: {e}")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            await message.answer(f"🔓 {message.reply_to_message.from_user.full_name} разбанен.")
        except Exception as e: await message.reply(f"Ошибка: {e}")

@dp.message(Command("mute"))
async def mute_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1))
            await message.answer(f"🔇 {message.reply_to_message.from_user.full_name} в муте на 1 час.")
        except Exception as e: await message.reply(f"Ошибка: {e}")

@dp.message(Command("unmute"))
async def unmute_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            perms = types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, perms)
            await message.answer(f"🔊 {message.reply_to_message.from_user.full_name} снова может писать.")
        except Exception as e: await message.reply(f"Ошибка: {e}")

# --- МОДЕРАЦИЯ И СБОР ДАННЫХ ---
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
