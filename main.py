import asyncio
import logging
from datetime import timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# Твой токен вставлен сюда
TOKEN = "8566060648:AAGAmO6_t3FVnu3ipQ9Ptc7dM8vO6Du928I"

# Включаем логирование, чтобы видеть ошибки в консоли Render
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Проверка прав администратора
async def is_admin(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]

# --- КОМАНДЫ ---

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if not await is_admin(message):
        return await message.reply("У тебя нет прав администратора.")
    
    if not message.reply_to_message:
        return await message.reply("Эта команда должна быть ответом на сообщение пользователя.")

    try:
        await bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.answer(f"🚫 Пользователь {message.reply_to_message.from_user.full_name} забанен.")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    if not await is_admin(message): return
    
    if not message.reply_to_message:
        return await message.reply("Ответь на сообщение, чтобы разбанить.")

    await bot.unban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
    await message.answer(f"✅ Пользователь {message.reply_to_message.from_user.full_name} разбанен.")

@dp.message(Command("mute"))
async def mute_user(message: types.Message):
    if not await is_admin(message): return

    if not message.reply_to_message:
        return await message.reply("Ответь на сообщение для мута.")

    # Мут на 1 час
    until_date = timedelta(hours=1)
    permissions = types.ChatPermissions(can_send_messages=False)
    
    try:
        await bot.restrict_chat_member(
            message.chat.id, 
            message.reply_to_message.from_user.id, 
            permissions,
            until_date=until_date
        )
        await message.answer(f"🔇 {message.reply_to_message.from_user.full_name} в муте на 1 час.")
    except Exception as e:
        await message.reply(f"Не удалось замутить: {e}")

@dp.message(Command("unmute"))
async def unmute_user(message: types.Message):
    if not await is_admin(message): return

    permissions = types.ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    
    await bot.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, permissions)
    await message.answer(f"🔊 Пользователь {message.reply_to_message.from_user.full_name} снова может писать.")

async def main():
    # Удаляем вебхуки перед запуском (полезно при перезапусках)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
