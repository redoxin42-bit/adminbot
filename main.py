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

# --- СПИСОК РП-ДЕЙСТВИЙ (БЕЗ СЛЭШЕЙ) ---
# Ключ - это то, что пишет юзер. Значение - это то, что пишет бот.
RP_ACTIONS = {
    "обнять": "🫂 {user} обнял(а) {target}",
    "поцеловать": "💋 {user} поцеловал(а) {target}",
    "ударить": "👊 {user} отвесил(а) леща {target}",
    "кусь": "🦷 {user} сделал(а) кусь {target}",
    "дать пять": "✋ {user} дал(а) пять {target}",
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

# --- ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ---
@dp.message()
async def main_handler(message: types.Message):
    # 1. Сбор статистики
    stats["messages"] += 1
    stats["users"].add(message.from_user.id)

    # 2. Проверка на РП-команду (без слэша)
    if message.text:
        msg_text = message.text.lower().strip()
        
        # Проверяем, есть ли такое слово в нашем списке РП
        if msg_text in RP_ACTIONS:
            user_link = message.from_user.mention_html() # Ссылка на того, кто пишет
            
            # Если это ответ на сообщение (Reply)
            if message.reply_to_message:
                target_link = message.reply_to_message.from_user.mention_html()
                response = RP_ACTIONS[msg_text].format(user=user_link, target=target_link)
                return await message.answer(response, parse_mode="HTML")
            
            # Если просто написано слово без реплая
            else:
                return await message.reply("Чтобы совершить действие, ответь этим словом на сообщение другого человека!")

    # 3. Админ-команды (если начинаются на /)
    if message.text and message.text.startswith("/"):
        cmd = message.text.split()[0][1:].lower()
        
        if cmd == "start":
            await message.answer("✅ Бот активен! Просто ответь на сообщение словом 'Обнять', 'Кусь' или 'Поцеловать'.")
        
        elif cmd == "stats" and await is_admin(message):
            await message.answer(f"📊 Сообщений: {stats['messages']}\n👥 Юзеров: {len(stats['users'])}")
        
        elif cmd in ["ban", "mute"] and await is_admin(message) and message.reply_to_message:
            try:
                if cmd == "ban":
                    await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
                    await message.answer("🚫 Пользователь забанен.")
                else:
                    await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, types.ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1))
                    await message.answer("🔇 Мут на 1 час.")
            except Exception as e:
                await message.reply(f"Ошибка прав: {e}")
        return

    # 4. Анти-ссылка
    if message.text and URL_PATTERN.search(message.text) and not await is_admin(message):
        try:
            await message.delete()
        except:
            pass

async def main():
    asyncio.create_task(start_webserver())
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
