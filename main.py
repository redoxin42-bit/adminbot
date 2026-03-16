import asyncio
import os
import logging
import re
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Твой токен
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"

# Список ID главных администраторов (теперь ты здесь)
SUPER_ADMINS = [8624430245, 7893084473]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

stats = {"messages": 0, "users": set()}
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|t\.me/[\w/]+')

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is active and running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- УЛУЧШЕННАЯ ПРОВЕРКА АДМИНА ---
async def is_admin(message: types.Message):
    # Если пользователь в списке SuperAdmins — он всегда админ
    if message.from_user.id in SUPER_ADMINS:
        return True
    # Иначе проверяем права в самом чате
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    is_user_admin = await is_admin(message)
    status = "👑 Главный админ" if message.from_user.id in SUPER_ADMINS else "👤 Пользователь"
    
    text = (
        f"👋 **Привет! Я админ-бот.**\n"
        f"Твой статус: {status}\n\n"
        "📍 **Доступные команды:**\n"
        "• `/stats` — статистика чата\n"
        "• `/admin` — панель управления\n\n"
        "📍 **Для модерации (ответом на сообщение):**\n"
        "• `/ban` / `/unban` — бан/разбан\n"
        "• `/mute` / `/unmute` — мут/размут"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not await is_admin(message):
        return await message.reply("❌ Доступ запрещен.")
    
    admin_text = (
        "🛠 **Панель администратора**\n\n"
        "1. Чтобы наказать пользователя, ответьте на его сообщение командой `/ban` или `/mute`.\n"
        "2. Бот автоматически удаляет ссылки от всех, кто не является админом.\n"
        "3. `/stats` показывает активность в реальном времени."
    )
    await message.answer(admin_text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if await is_admin(message):
        await message.reply(
            f"📊 **Статистика чата:**\n"
            f"📩 Сообщений обработано: `{stats['messages']}`\n"
            f"👥 Уникальных пользователей: `{len(stats['users'])}`",
            parse_mode="Markdown"
        )

@dp.message(Command("ban"))
async def ban(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer(f"🚫 {message.reply_to_message.from_user.full_name} забанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("unban"))
async def unban(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            await message.answer(f"🔓 {message.reply_to_message.from_user.full_name} разбанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("mute"))
async def mute(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.restrict_chat_member(
                message.chat.id, 
                message.reply_to_message.from_user.id, 
                types.ChatPermissions(can_send_messages=False), 
                until_date=timedelta(hours=1)
            )
            await message.answer(f"🔇 {message.reply_to_message.from_user.full_name} в муте на 1 час.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("unmute"))
async def unmute(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            permissions = types.ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, 
                can_send_other_messages=True, can_add_web_page_previews=True
            )
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions)
            await message.answer(f"🔊 {message.reply_to_message.from_user.full_name} снова может писать.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message()
async def process(message: types.Message):
    # Считаем статистику
    stats["messages"] += 1
    stats["users"].add(message.from_user.id)
    
    # Анти-ссылка (игнорирует админов из списка SUPER_ADMINS и админов чата)
    if message.text and URL_PATTERN.search(message.text):
        if not await is_admin(message):
            try:
                await message.delete()
            except:
                pass

async def main():
    asyncio.create_task(start_webserver())
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Настройка меню (синяя кнопка)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить/Обновить"),
        BotCommand(command="admin", description="Меню админа"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="ban", description="Бан (reply)"),
        BotCommand(command="unban", description="Разбан (reply)"),
        BotCommand(command="mute", description="Мут (reply)"),
        BotCommand(command="unmute", description="Размут (reply)")
    ])
    
    print("Бот запущен. Супер-админы добавлены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
