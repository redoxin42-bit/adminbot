import asyncio
import logging
from datetime import timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Твой токен
TOKEN = "8566060648:AAGAmO6_t3FVnu3ipQ9Ptc7dM8vO6Du928I"

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция проверки админа
async def is_admin(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]

# --- КОМАНДЫ ---

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if not await is_admin(message):
        return
    if message.reply_to_message:
        try:
            await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.answer(f"🚫 {message.reply_to_message.from_user.full_name} забанен.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("mute"))
async def mute_user(message: types.Message):
    if not await is_admin(message):
        return
    if message.reply_to_message:
        try:
            until_date = timedelta(hours=1)
            permissions = types.ChatPermissions(can_send_messages=False)
            await bot.restrict_chat_member(
                message.chat.id, 
                message.reply_to_message.from_user.id, 
                permissions,
                until_date=until_date
            )
            await message.answer(f"🔇 {message.reply_to_message.from_user.full_name} в муте на час.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

@dp.message(Command("unmute", "unban"))
async def unmute_user(message: types.Message):
    if not await is_admin(message):
        return
    if message.reply_to_message:
        try:
            # Снимаем бан
            await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id, only_if_banned=True)
            # Возвращаем права писать сообщения
            permissions = types.ChatPermissions(
                can_send_messages=True, 
                can_send_media_messages=True, 
                can_send_other_messages=True, 
                can_add_web_page_previews=True
            )
            await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions)
            await message.answer(f"✅ Ограничения для {message.reply_to_message.from_user.full_name} сняты.")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

async def main():
    # Важно: удаляем вебхук и старые запросы, чтобы не было ошибки Conflict
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
