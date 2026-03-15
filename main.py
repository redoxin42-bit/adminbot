import asyncio
import os
import logging
import re
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Токен
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

stats = {"messages": 0, "users": set()}
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[\w/]+')

# --- ЗАГЛУШКА ДЛЯ RENDER ---
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

# --- ПРОВЕРКА АДМИНА ---
async def is_admin(message: types.Message):
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# --- КОМАНДА START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 **Привет! Я твой админ-бот.**\n\n"
        "🔧 **Мои возможности:**\n"
        "1️⃣ Удаляю ссылки от обычных пользователей.\n"
        "2️⃣ Веду статистику чата.\n"
        "3️⃣ Помогаю админам банить и мутить нарушителей.\n\n"
        "📍 Команды (используй Reply):\n"
        "• `/ban` — забанить\n"
        "• `/mute` — мут на час\n"
        "• `/stats` — статистика чата"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# --- ОСТАЛЬНЫЕ КОМАНДЫ ---
@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if await is_admin(message):
        await message.reply(f"📊 Статистика:\n📩 Сообщений: {stats['messages']}\n👥 Уникальных юзеров: {len(stats['users'])}")

@dp.message(Command("ban"))
async def ban(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer("🚫 Пользователь забанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message()
async def process(message: types.Message):
    # Считаем статистику
    stats["messages"] += 1
    stats["users"].add(message.from_user.id)
    
    # Анти-ссылка
    if message.text and URL_PATTERN.search(message.text) and not await is_admin(message):
        try: 
            await message.delete()
        except: 
            pass

async def main():
    # Запуск веб-сервера фоном
    asyncio.create_task(start_webserver())
    
    # Очистка очереди (убирает Conflict, если бот долго был оффлайн)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Регистрация меню в кнопке "Меню"
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="ban", description="Бан (reply)")
    ])
    
    print("Бот успешно запущен на Render!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
