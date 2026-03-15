import telebot
import time
import sqlite3
from datetime import datetime
import os
import json

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "8566060648:AAGAmO6_t3FVnu3ipQ9Ptc7dM8vO6Du928I"
ADMIN_IDS = [8624430245]

# ===== НАСТРОЙКИ =====
FORBIDDEN_LINKS = True
WELCOME_NEW = True
DELETE_SERVICE_MSGS = True

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = telebot.TeleBot(TOKEN)

# TeleBotHost сам даст URL вебхука
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
if WEBHOOK_URL:
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Вебхук установлен на {WEBHOOK_URL}")

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   username TEXT, 
                   first_name TEXT,
                   join_date TEXT, 
                   messages INTEGER DEFAULT 0,
                   last_active TEXT)''')
conn.commit()

# ===== ОБРАБОТЧИКИ КОМАНД =====
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "🤖 Админ-бот запущен на TeleBotHost!")

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"🆔 Твой ID: `{message.from_user.id}`", parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📚 **Команды:**

👤 **Для всех:**
/id — узнать свой ID
/help — помощь

👑 **Для админов:**
/ban — забанить (ответом)
/unban — разбанить (ответом)
/mute [мин] — замутить (ответом)
/unmute — размутить (ответом)
/stats — статистика
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Ты не главный админ!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    
    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ {user_name} забанен")
    except:
        bot.reply_to(message, f"❌ Ошибка: нет прав")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Ты не главный админ!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    
    user_id = message.reply_to_message.from_user.id
    
    try:
        bot.unban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ Пользователь разбанен")
    except:
        bot.reply_to(message, f"❌ Ошибка")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Ты не главный админ!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    
    args = message.text.split()
    mute_time = 3600
    
    if len(args) > 1:
        try:
            minutes = int(args[1])
            mute_time = minutes * 60
        except:
            pass
    
    try:
        until = int(time.time()) + mute_time
        bot.restrict_chat_member(
            message.chat.id, 
            user_id, 
            until_date=until,
            can_send_messages=False
        )
        
        hours = mute_time // 3600
        minutes = (mute_time % 3600) // 60
        
        if hours > 0:
            bot.reply_to(message, f"🔇 Замутил {user_name} на {hours} ч {minutes} мин")
        else:
            bot.reply_to(message, f"🔇 Замутил {user_name} на {minutes} мин")
    except:
        bot.reply_to(message, f"❌ Ошибка")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Ты не главный админ!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    
    try:
        bot.restrict_chat_member(
            message.chat.id, 
            user_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        bot.reply_to(message, f"🔊 Размутил {user_name}")
    except:
        bot.reply_to(message, f"❌ Ошибка")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Только для админов")
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE messages > 0")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(messages) FROM users")
    total_msgs = cursor.fetchone()[0] or 0
    
    stats_text = f"""
📊 **Статистика:**
👥 Всего: {total_users}
💬 Активных: {active_users}
✉️ Сообщений: {total_msgs}
    """
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# ===== ТОЧКА ВХОДА ДЛЯ TELEBOTHOST =====
def handler(event, context):
    """Функция, которую вызывает TeleBotHost"""
    try:
        update = telebot.types.Update.de_json(json.loads(event['body']))
        bot.process_new_updates([update])
        return {'statusCode': 200}
    except Exception as e:
        print(f"Ошибка: {e}")
        return {'statusCode': 200}
