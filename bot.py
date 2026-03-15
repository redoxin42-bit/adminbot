from flask import Flask, request
import telebot
import time
import sqlite3
import os
from datetime import datetime

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "8566060648:AAGAmO6_t3FVnu3ipQ9Ptc7dM8vO6Du928I"
ADMIN_IDS = [8624430245]

# ===== НАСТРОЙКИ =====
FORBIDDEN_LINKS = True      # Удалять ссылки
WELCOME_NEW = True          # Приветствовать новичков
DELETE_SERVICE_MSGS = True  # Удалять "вошел/вышел"

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Определяем URL для вебхука
RENDER_URL = "https://adminbothow.onrender.com"  # Твой точный URL
WEBHOOK_URL = f"{RENDER_URL}/webhook"

# Устанавливаем вебхук при старте
try:
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Вебхук установлен на {WEBHOOK_URL}")
except Exception as e:
    print(f"❌ Ошибка установки вебхука: {e}")

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

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

# ----- КОМАНДА /START -----
@bot.message_handler(commands=['start'])
def start_command(message):
    text = """
🤖 **АДМИН-БОТ ЗАПУЩЕН**

**Доступные команды:**
/id — узнать свой ID
/help — список всех команд

👑 **Для админа:**
/ban — забанить (ответом)
/unban — разбанить (ответом)
/mute [мин] — замутить (ответом)
/unmute — размутить (ответом)
/stats — статистика

✅ Работаю на Render 24/7
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ----- КОМАНДА /ID -----
@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"🆔 Твой ID: `{message.from_user.id}`", parse_mode='Markdown')

# ----- КОМАНДА /HELP -----
@bot.message_handler(commands=['help'])
def help_command(message):
    text = """
📚 **ПОЛНЫЙ СПИСОК КОМАНД:**

👤 **Для всех:**
/id — показать твой ID
/help — это сообщение

👑 **Для админа:**
/ban — забанить (ответь на сообщение)
/unban — разбанить (ответь на сообщение)
/mute [минуты] — замутить (по умолчанию 60)
/unmute — размутить (ответь на сообщение)
/stats — статистика чата

⚙️ **Автоматически:**
• Удаление ссылок от обычных пользователей
• Приветствие новых участников
• Удаление служебных сообщений
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ----- КОМАНДА /BAN -----
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS:
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
        bot.reply_to(message, "❌ Ошибка бана")

# ----- КОМАНДА /UNBAN -----
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_IDS:
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

# ----- КОМАНДА /MUTE -----
@bot.message_handler(commands=['mute'])
def mute_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    args = message.text.split()
    mute_min = 60
    if len(args) > 1:
        try:
            mute_min = int(args[1])
        except:
            pass
    try:
        until = int(time.time()) + (mute_min * 60)
        bot.restrict_chat_member(message.chat.id, user_id, until_date=until, can_send_messages=False)
        bot.reply_to(message, f"🔇 {user_name} замучен на {mute_min} мин")
    except:
        bot.reply_to(message, f"❌ Ошибка")

# ----- КОМАНДА /UNMUTE -----
@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение")
        return
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    try:
        bot.restrict_chat_member(message.chat.id, user_id,
                                 can_send_messages=True,
                                 can_send_media_messages=True,
                                 can_send_other_messages=True,
                                 can_add_web_page_previews=True)
        bot.reply_to(message, f"🔊 {user_name} размучен")
    except:
        bot.reply_to(message, f"❌ Ошибка")

# ----- КОМАНДА /STATS -----
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Только для админа")
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE messages > 0")
    active = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(messages) FROM users")
    msgs = cursor.fetchone()[0] or 0
    text = f"""
📊 **СТАТИСТИКА:**
👥 Всего пользователей: {total}
💬 Активных: {active}
✉️ Сообщений: {msgs}
"""
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ----- ПРИВЕТСТВИЕ НОВЫХ -----
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    if DELETE_SERVICE_MSGS:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    if not WELCOME_NEW: return
    for user in message.new_chat_members:
        if user.id == bot.get_me().id: return
        cursor.execute('''INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)''',
                      (user.id, user.username, user.first_name,
                       datetime.now().strftime("%Y-%m-%d %H:%M"), 0,
                       datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        bot.send_message(message.chat.id, f"👋 Добро пожаловать, {user.first_name}!")

# ----- УДАЛЕНИЕ СООБЩЕНИЙ О ВЫХОДЕ -----
@bot.message_handler(content_types=['left_chat_member'])
def delete_left(message):
    if DELETE_SERVICE_MSGS:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass

# ----- АНТИ-СПАМ -----
@bot.message_handler(func=lambda m: True)
def anti_spam(message):
    if message.text and message.text.startswith('/'): return
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        if message.from_user.id in [a.user.id for a in admins]: return
    except: pass
    cursor.execute('''UPDATE users SET messages = messages + 1, last_active = ? WHERE user_id = ?''',
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), message.from_user.id))
    conn.commit()
    if FORBIDDEN_LINKS and message.text:
        if any(x in message.text.lower() for x in ['http://', 'https://', 't.me/', 'www.']):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, f"⚠️ {message.from_user.first_name}, ссылки только для админов!")
            except: pass

# ============================================
# ВЕБХУК И ЗАПУСК
# ============================================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'OK', 200

@app.route('/')
def home():
    return "✅ Admin bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 ЗАПУСК АДМИН-БОТА")
    print("=" * 50)
    print(f"Бот: @{bot.get_me().username}")
    print(f"Вебхук: {WEBHOOK_URL}")
    print("=" * 50)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
