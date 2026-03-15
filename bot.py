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
FORBIDDEN_LINKS = True      # Удалять ссылки от обычных юзеров
WELCOME_NEW = True          # Приветствовать новеньких
DELETE_SERVICE_MSGS = True  # Удалять служебные сообщения (вошел/вышел)

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Устанавливаем вебхук для Render
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
if RENDER_URL:
    webhook_url = f"{RENDER_URL}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен на {webhook_url}")

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
# ФУНКЦИИ БОТА
# ============================================

# ----- ПРИВЕТСТВИЕ НОВЫХ УЧАСТНИКОВ -----
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    if DELETE_SERVICE_MSGS:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
    
    if not WELCOME_NEW:
        return
        
    for user in message.new_chat_members:
        if user.id == bot.get_me().id:
            return
            
        # Добавляем в базу данных
        cursor.execute('''INSERT OR IGNORE INTO users 
                          (user_id, username, first_name, join_date, messages, last_active) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                      (user.id, 
                       user.username, 
                       user.first_name,
                       datetime.now().strftime("%Y-%m-%d %H:%M"), 
                       0,
                       datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        
        bot.send_message(message.chat.id, 
                        f"👋 Добро пожаловать, {user.first_name}!\n"
                        f"Правила чата в закрепе. Бот следит за порядком.")

# ----- УДАЛЕНИЕ СООБЩЕНИЙ О ВЫХОДЕ -----
@bot.message_handler(content_types=['left_chat_member'])
def delete_left(message):
    if DELETE_SERVICE_MSGS:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass

# ----- АНТИ-СПАМ (УДАЛЕНИЕ ССЫЛОК) -----
@bot.message_handler(func=lambda m: True)
def anti_spam(message):
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    # Проверяем, админ ли
    is_admin = False
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]
        if message.from_user.id in admin_ids:
            is_admin = True
    except:
        pass
    
    # Если админ - пропускаем
    if is_admin:
        return
    
    # Обновляем статистику пользователя
    cursor.execute('''UPDATE users SET messages = messages + 1, 
                      last_active = ? WHERE user_id = ?''',
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), message.from_user.id))
    conn.commit()
    
    # Проверка на ссылки
    if FORBIDDEN_LINKS and message.text:
        if any(x in message.text.lower() for x in ['http://', 'https://', 't.me/', 'www.']):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                warning = bot.send_message(
                    message.chat.id, 
                    f"⚠️ {message.from_user.first_name}, ссылки только для админов!"
                )
                # Автоудаление предупреждения через 5 секунд
                time.sleep(5)
                bot.delete_message(warning.chat.id, warning.message_id)
            except:
                pass

# ----- КОМАНДА /START (МЕНЮ) -----
@bot.message_handler(commands=['start'])
def start_command(message):
    menu_text = f"""
╔══════════════════════════╗
║     🤖 **АДМИН-БОТ**     ║
╚══════════════════════════╝

**Что я умею:**

🔹 **Для всех пользователей:**
• /id — узнать свой Telegram ID
• /help — список всех команд

🔹 **Для админов:**
• /ban — забанить пользователя (ответом)
• /unban — разбанить (ответом)
• /mute [мин] — замутить (ответом)
• /unmute — размутить (ответом)
• /stats — статистика чата

🔹 **Автоматически:**
• Удаляю ссылки от обычных юзеров
• Приветствую новичков
• Убираю служебные сообщения

✅ **Статус:** Работаю 24/7 на Render
👑 **Твой ID:** `{message.from_user.id}`
"""
    bot.send_message(message.chat.id, menu_text, parse_mode='Markdown')

# ----- КОМАНДА /ID -----
@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"🆔 **Твой Telegram ID:** `{message.from_user.id}`", parse_mode='Markdown')

# ----- КОМАНДА /HELP -----
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📚 **ПОЛНЫЙ СПИСОК КОМАНД:**

👤 **Для всех:**
/id — показать твой ID
/help — это сообщение

👑 **Для админов (только для тебя):**
/ban — забанить (ответь на сообщение)
/unban — разбанить (ответь на сообщение)
/mute [минуты] — замутить (по умолчанию 60 мин)
/unmute — размутить (ответь на сообщение)
/stats — статистика чата

⚙️ **Автоматические функции:**
• Удаление ссылок от обычных пользователей
• Приветствие новых участников
• Удаление служебных сообщений (вошел/вышел)
• База данных всех участников

❓ **Как пользоваться командами админа:**
1. Найди сообщение нарушителя
2. Ответь на него командой /ban или /mute
3. Для /mute можно указать время: /mute 30

🛡 **Бот работает 24/7 на облачном сервере**
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# ----- КОМАНДА /BAN -----
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Эта команда только для главного админа!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение пользователя, которого хочешь забанить")
        return
    
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    
    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ **{user_name}** забанен навсегда", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: нет прав администратора или я не могу забанить этого пользователя")

# ----- КОМАНДА /UNBAN -----
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Эта команда только для главного админа!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение пользователя, которого хочешь разбанить")
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
        bot.reply_to(message, "⛔ Эта команда только для главного админа!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение пользователя, которого хочешь замутить")
        return
    
    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name
    
    # Получаем время из команды (по умолчанию 60 минут)
    args = message.text.split()
    mute_minutes = 60  # по умолчанию
    
    if len(args) > 1:
        try:
            mute_minutes = int(args[1])
        except:
            bot.reply_to(message, "❌ Неправильный формат. Используй: /mute [минуты]")
            return
    
    mute_seconds = mute_minutes * 60
    
    try:
        until = int(time.time()) + mute_seconds
        bot.restrict_chat_member(
            message.chat.id, 
            user_id, 
            until_date=until,
            can_send_messages=False
        )
        
        bot.reply_to(message, f"🔇 **Замутил {user_name}** на {mute_minutes} мин", parse_mode='Markdown')
    except:
        bot.reply_to(message, f"❌ Ошибка: нет прав администратора")

# ----- КОМАНДА /UNMUTE -----
@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Эта команда только для главного админа!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение пользователя, которого хочешь размутить")
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
        bot.reply_to(message, f"🔊 **Размутил {user_name}**", parse_mode='Markdown')
    except:
        bot.reply_to(message, f"❌ Ошибка")

# ----- КОМАНДА /STATS (ПОЛНАЯ СТАТИСТИКА) -----
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Статистика только для главного админа")
        return
    
    # Общая статистика по базе
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE messages > 0")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(messages) FROM users")
    total_msgs = cursor.fetchone()[0] or 0
    
    # Топ-5 самых активных
    cursor.execute("SELECT first_name, messages FROM users ORDER BY messages DESC LIMIT 5")
    top_users = cursor.fetchall()
    
    top_text = ""
    for i, (name, msgs) in enumerate(top_users, 1):
        top_text += f"{i}. {name} — {msgs} сообщ.\n"
    
    # Информация о чате
    chat_info = ""
    try:
        chat = bot.get_chat(message.chat.id)
        chat_title = chat.title or "Личные сообщения"
        chat_info = f"📌 **Чат:** {chat_title}\n"
    except:
        pass
    
    stats_text = f"""
╔══════════════════════════╗
║     📊 **СТАТИСТИКА**    ║
╚══════════════════════════╝

{chat_info}
👥 **Всего в базе:** {total_users} чел.
💬 **Активных:** {active_users} чел.
✉️ **Всего сообщений:** {total_msgs}

🏆 **Топ-5 по активности:**
{top_text}

📅 **Дата:** {datetime.now().strftime("%d.%m.%Y %H:%M")}
🤖 **Бот работает на Render**
"""
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# ============================================
# ВЕБХУК И ЗАПУСК
# ============================================

@app.route('/webhook', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def home():
    return "✅ Админ-бот работает на Render!"

@app.route('/health')
def health():
    return "OK", 200

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 АДМИН-БОТ НА RENDER")
    print("=" * 50)
    print(f"✅ Твой Admin ID: {ADMIN_IDS[0]}")
    print(f"✅ База данных: users.db")
    print(f"✅ Вебхук: {RENDER_URL}/webhook")
    print("=" * 50)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
