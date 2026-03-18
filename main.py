import asyncio
import os
import logging
import re
from datetime import timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiohttp import web

# Твой токен и список главных админов
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"
SUPER_ADMINS = [8624430245, 7893084473]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная статистика (сбрасывается при перезагрузке)
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

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (АНТИ-СПЯЧКА) ---
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

# --- ФУНКЦИЯ ПРОВЕРКИ ПРАВ ---
async def is_admin(message: types.Message):
    if message.from_user.id in SUPER_ADMINS:
        return True
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# --- ОБРАБОТЧИК РП-КОМАНД ---
@dp.message(Command(*RP_ACTIONS.keys()))
async def handle_rp(message: types.Message):
    # Извлекаем саму команду (например, /обнять -> обнять)
    cmd = message.text.split()[0][1:].lower()
    user = message.from_user.mention_html()
    target = ""

    if message.reply_to_message:
        target = message.reply_to_message.from_user.mention_html()
    elif len(message.text.split()) > 1:
        target = " ".join(message.text.split()[1:])
    else:
        return await message.reply("❕ Ответь на сообщение или напиши имя после команды.")

    text = RP_ACTIONS[cmd].format(user=user, target=target)
    await message.answer(text, parse_mode="HTML")

# --- АДМИН-КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    status = "👑 Главный админ" if message.from_user.id in SUPER_ADMINS else "👤 Участник"
    await message.answer(
        f"👋 **Привет! Я админ-бот.**\nТвой статус: {status}\n\n"
        "🎭 **РП-команды:** /обнять, /кусь, /поцеловать, /ударить, /дать_пять\n"
        "🛡 **Модерация:** /ban, /unban, /mute, /unmute (через reply)\n"
        "📊 **Статистика:** /stats",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if await is_admin(message):
        await message.reply(
            f"📊 **Статистика чата:**\n📩 Сообщений: `{stats['messages']}`\n👥 Юзеров: `{len(stats['users'])}`",
            parse_mode="Markdown"
        )

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer(f"🚫 {message.reply_to_message.from_user.full_name} забанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            await message.answer(f"🔓 {message.reply_to_message.from_user.full_name} разбанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("mute"))
async def mute_user(message: types.Message):
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
async def unmute_user(message: types.Message):
    if await is_admin(message) and message.reply_to_message:
        try:
            perms = types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, perms)
            await message.answer(f"🔊 {message.reply_to_message.from_user.full_name} снова может писать.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

# --- ОБЩИЙ ОБРАБОТЧИК (АНТИ-ССЫЛКА И СТАТИСТИКА) ---
@dp.message()
async def filter_messages(message: types.Message):
    # Считаем сообщение
    stats["messages"] += 1
    stats["users"].add(message.from_user.id)
    
    # Удаляем ссылки от не-админов
    if message.text and URL_PATTERN.search(message.text):
        if not await is_admin(message):
            try:
                await message.delete()
            except:
                pass

# --- ЗАПУСК ---
async def main():
    # Запускаем сервер для Render фоном
    asyncio.create_task(start_webserver())
    
    # Сбрасываем очередь сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Настраиваем меню команд в Телеграм
    await bot.set_my_commands([
        BotCommand(command="start", description="Старт/Меню"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="ban", description="Бан (reply)"),
        BotCommand(command="mute", description="Мут (reply)"),
        BotCommand(command="обнять", description="РП: Обнять"),
        BotCommand(command="кусь", description="РП: Кусь")
    ])
    
    print("Бот запущен на Render! Команды готовы.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
