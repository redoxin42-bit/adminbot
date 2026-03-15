import asyncio
import logging
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand

# Твой токен
TOKEN = "8728187843:AAEHVOaKegbtKv4uVhA1m_x_Zc8tfMWzYts"

# Настройка логов
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Простейшая статистика в памяти (сбросится при перезагрузке)
stats = {
    "messages_processed": 0,
    "users_seen": set()
}

# Функция проверки прав администратора
async def is_admin(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]

# --- ОБРАБОТЧИК СТАТИСТИКИ ---

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    # Статистику обычно смотрят только админы
    if not await is_admin(message):
        return await message.reply("Эта команда только для администраторов.")
    
    text = (
        "📊 **Статистика бота (с момента запуска):**\n\n"
        f"📩 Сообщений обработано: `{stats['messages_processed']}`\n"
        f"👥 Уникальных пользователей: `{len(stats['users_seen'])}`"
    )
    await message.answer(text, parse_mode="Markdown")

# --- КОМАНДЫ АДМИНИСТРАТОРА ---

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if not await is_admin(message): return
    if message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer(f"🚫 {message.reply_to_message.from_user.full_name} забанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("mute"))
async def mute_user(message: types.Message):
    if not await is_admin(message): return
    if message.reply_to_message:
        try:
            until_date = timedelta(hours=1)
            await bot.restrict_chat_member(
                message.chat.id, 
                message.reply_to_message.from_user.id, 
                types.ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            await message.answer(f"🔇 {message.reply_to_message.from_user.full_name} в муте на 1 час.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("unmute", "unban"))
async def unmute_user(message: types.Message):
    if not await is_admin(message): return
    if message.reply_to_message:
        try:
            await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            permissions = types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions)
            await message.answer(f"✅ Ограничения для {message.reply_to_message.from_user.full_name} сняты.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

# --- СЧЕТЧИК СООБЩЕНИЙ ---

@dp.message()
async def count_messages(message: types.Message):
    # Увеличиваем счетчик для каждого сообщения
    stats["messages_processed"] += 1
    stats["users_seen"].add(message.from_user.id)
    # Этот обработчик не мешает другим командам, так как они выше в коде

# --- ЗАПУСК ---

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="stats", description="Показать статистику"),
        BotCommand(command="ban", description="Забанить (нужен Reply)"),
        BotCommand(command="mute", description="Замутить на час (нужен Reply)"),
        BotCommand(command="unmute", description="Разбанить/размутить (нужен Reply)")
    ]
    await bot.set_my_commands(commands)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot) # Установка меню
    
    me = await bot.get_me()
    print(f"Бот @{me.username} успешно запущен!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
