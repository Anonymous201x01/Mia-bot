import telebot
import random
import time
import os
import re
import json
import threading
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7107785168
MAX_COUNT = 15
AUTO_ART_INTERVAL = 3600  # 1 час в секундах

bot = telebot.TeleBot(TOKEN)

WARNS_FILE = "warns.json"
BANS_FILE = "bans.json"
MUTES_FILE = "mutes.json"
USERS_FILE = "users.json"
STATE_FILE = "bot_state.json"
LAST_ACTIVITY_FILE = "last_activity.json"
LEFT_CHATS_FILE = "left_chats.json"

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

warns = load_data(WARNS_FILE)
bans = load_data(BANS_FILE)
mutes = load_data(MUTES_FILE)
users = load_data(USERS_FILE)
bot_state = load_data(STATE_FILE)
last_activity = load_data(LAST_ACTIVITY_FILE)
left_chats = load_data(LEFT_CHATS_FILE)

if not bot_state:
    bot_state = {
        "sleeping": False,
        "ignored_users": [],
        "owner_commands": {
            "спать": "Приказ поняла, сладких мне снов",
            "проснись": "Уже! Я снова в строю",
            "игнорируй": "{user} я обиделась и больше с тобой не разговариваю, динахуй!",
            "забудь обиды": "Я всех прощаю",
            "уходи": "Есть сэр!"
        }
    }
    save_data(bot_state, STATE_FILE)

arts_folder = "."
all_arts = [f for f in os.listdir(arts_folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
active_chats = {}
chat_art_pools = {}

WARN_MESSAGES = {
    1: "Будь аккуратнее, предупреждение 1/5",
    2: "Веди себя хорошо, предупреждение 2/5",
    3: "Ты на грани бана, предупреждение 3/5",
    4: "Ты скоро пойдешь нахуй, предупреждение 4/5",
    5: "Покеда хуесос, предупреждение 5/5. {user} был забанен"
}

def update_last_activity(chat_id):
    if str(chat_id) not in last_activity:
        last_activity[str(chat_id)] = {}
    last_activity[str(chat_id)]["last_time"] = time.time()
    save_data(last_activity, LAST_ACTIVITY_FILE)

def auto_send_arts():
    while True:
        current_time = time.time()
        for chat_id_str in list(last_activity.keys()):
            try:
                chat_id = int(chat_id_str)
                chat_info = bot.get_chat(chat_id)
                if chat_info.type in ['group', 'supergroup']:
                    if current_time - last_activity[chat_id_str]["last_time"] >= AUTO_ART_INTERVAL:
                        if not bot_state["sleeping"]:
                            send_art(chat_id)
                        update_last_activity(chat_id)
            except:
                continue
        time.sleep(60)

auto_send_thread = threading.Thread(target=auto_send_arts)
auto_send_thread.daemon = True
auto_send_thread.start()

def add_user(user):
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or ""
        }
        save_data(users, USERS_FILE)

def clean_text(text):
    return re.sub(r'[^\w\s]', '', text.lower()).strip()

def get_next_art(chat_id):
    if chat_id not in chat_art_pools or not chat_art_pools[chat_id]:
        chat_art_pools[chat_id] = all_arts.copy()
        random.shuffle(chat_art_pools[chat_id])
    return chat_art_pools[chat_id].pop()

def send_art(chat_id):
    if bot_state["sleeping"]:
        return
    art = get_next_art(chat_id)
    with open(art, "rb") as f:
        bot.send_photo(chat_id, f)
    update_last_activity(chat_id)

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_owner(user_id):
    return str(user_id) == str(OWNER_ID)

def clean_old_data():
    global warns, mutes
    current_time = datetime.now()
    
    for chat_id in list(warns.keys()):
        for user_id in list(warns[chat_id].keys()):
            warn_data = warns[chat_id][user_id]
            if 'expires' in warn_data and datetime.fromisoformat(warn_data['expires']) < current_time:
                del warns[chat_id][user_id]
        if not warns[chat_id]:
            del warns[chat_id]
    
    for chat_id in list(mutes.keys()):
        for user_id in list(mutes[chat_id].keys()):
            mute_end = datetime.fromisoformat(mutes[chat_id][user_id]['until'])
            if mute_end < current_time:
                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                except:
                    pass
                del mutes[chat_id][user_id]
        if not mutes[chat_id]:
            del mutes[chat_id]
    
    save_data(warns, WARNS_FILE)
    save_data(mutes, MUTES_FILE)

def schedule_cleaner():
    while True:
        clean_old_data()
        time.sleep(600)

cleaner_thread = threading.Thread(target=schedule_cleaner)
cleaner_thread.daemon = True
cleaner_thread.start()

@bot.message_handler(commands=['furry'])
def furry_cmd(message):
    if bot_state["sleeping"] and not is_owner(message.from_user.id):
        return
    
    chat_id = message.chat.id
    update_last_activity(chat_id)
    parts = message.text.split()
    count = 1
    if len(parts) > 1 and parts[1].isdigit():
        count = min(int(parts[1]), MAX_COUNT)
    
    if count == 1:
        send_art(chat_id)
    else:
        arts_to_send = [get_next_art(chat_id) for _ in range(count)]
        for art_path in arts_to_send:
            with open(art_path, "rb") as f:
                bot.send_photo(chat_id, f)
        update_last_activity(chat_id)

@bot.message_handler(commands=['listusers'])
def list_users_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "Команда доступна только владельцу.")
        return
    
    if not users:
        bot.reply_to(message, "Список пользователей пуст.")
        return
    
    text_lines = ["Пользователи, которые писали боту:"]
    for uid, info in users.items():
        name = f"{info.get('first_name','')} {info.get('last_name','')}".strip()
        username = info.get('username')
        line = f"ID: {uid} | Имя: {name}"
        if username:
            line += f" | @{username}"
        text_lines.append(line)
    
    bot.reply_to(message, "\n".join(text_lines))
    update_last_activity(message.chat.id)

@bot.message_handler(commands=['miahelp'])
def show_mia_help(message):
    help_text = """<b>📚 Система обращений:</b>
• Для команд и мини-игр используйте "Мия"
• Для обычных фраз используйте "Ми"

<b>🖼 Команды для артов:</b>
/furry - Случайный фурри-арт
/furry N - Несколько артов (макс. 15)

<b>⚖️ Модерация (для админов):</b>
[ответ] варн - Выдать предупреждение (5 варнов = бан)
[ответ] снять варн - Снять 1 варн
[ответ] снять варны - Снять все варны
[ответ] бан - Забанить навсегда
разбан @user - Разбанить

<b>🔇 Команды мута:</b>
[ответ] мут Xм - Мут на X минут (макс. 60)
[ответ] мут Xч - Мут на X часов (макс. 24)
[ответ] мут Xд - Мут на X дней (макс. 7)
[ответ] размут - Снять мут досрочно

<b>🎮 Мини-игры (начинаются с Мия):</b>
Мия кого <действие> - Выбрать случайного участника
Мия @user <вопрос> - Задать вопрос"""

    bot.reply_to(message, help_text, parse_mode="HTML")
    update_last_activity(message.chat.id)

@bot.message_handler(commands=['help'])
def show_owner_help(message):
    if message.chat.type != 'private' or not is_owner(message.from_user.id):
        return
    
    help_text = """<b>🔐 Личные команды (начинаются с Мия):</b>
Мия спать - Спящий режим
Мия проснись - Разбудить
Мия, игнорируй [ответ] - Игнорировать
Мия забудь обиды - Простить всех
Мия уходи - Выйти из чата

<b>👥 Админ-команды:</b>
/listusers - Список пользователей
/leavechat - Список покинутых чатов
/obida - Список игнорируемых пользователей
/miahelp - Помощь для всех"""
    
    bot.reply_to(message, help_text, parse_mode="HTML")
    update_last_activity(message.chat.id)

@bot.message_handler(commands=['leavechat'])
def list_left_chats(message):
    if not is_owner(message.from_user.id):
        return
    
    if not left_chats:
        bot.reply_to(message, "Бот не покидал чаты.")
        return
    
    text = "Покинутые чаты:\n"
    for i, chat_id in enumerate(left_chats.keys(), 1):
        try:
            chat = bot.get_chat(chat_id)
            title = chat.title
            text += f"{i}. {title} (ID: {chat_id})\n"
        except:
            text += f"{i}. Неизвестный чат (ID: {chat_id})\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['obida'])
def list_ignored_users(message):
    if not is_owner(message.from_user.id):
        return
    
    if not bot_state["ignored_users"]:
        bot.reply_to(message, "Нет игнорируемых пользователей.")
        return
    
    text = "Игнорируемые пользователи:\n"
    for i, user_id in enumerate(bot_state["ignored_users"], 1):
        user_data = users.get(user_id, {})
        name = f"{user_data.get('first_name','')} {user_data.get('last_name','')}".strip()
        username = f"@{user_data.get('username')}" if user_data.get('username') else ""
        text += f"{i}. {name} {username} (ID: {user_id})\n"
    
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text.lower().startswith("мут "))
def mute_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    update_last_activity(message.chat.id)
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
    else:
        parts = message.text.split()
        if len(parts) >= 3 and parts[1].startswith('@'):
            username = parts[1][1:]
            for uid, user_data in users.items():
                if user_data.get('username', '').lower() == username.lower():
                    target_id = uid
                    break
    
    if not target_id:
        bot.reply_to(message, "Ответьте на сообщение или укажите @username")
        return
    
    if target_id == admin_id:
        bot.reply_to(message, "Нельзя замутить себя")
        return
    if is_owner(int(target_id)):
        bot.reply_to(message, "Неа")
        return
    if not is_owner(message.from_user.id) and is_admin(message.chat.id, int(target_id)):
        bot.reply_to(message, "Нельзя замутить другого админа")
        return
    
    time_match = re.search(r"(\d+)([мчд])", message.text.lower())
    if not time_match:
        bot.reply_to(message, "Неверный формат времени. Пример: 'мут 10м'")
        return
    
    amount = int(time_match.group(1))
    unit = time_match.group(2)
    
    if unit == 'м' and amount > 60:
        bot.reply_to(message, "Ошибка, максимум 60 минут")
        return
    elif unit == 'ч' and amount > 24:
        bot.reply_to(message, "Ошибка, максимум 24 часа")
        return
    elif unit == 'д' and amount > 7:
        bot.reply_to(message, "Ошибка, максимум 7 дней")
        return
    
    if unit == 'м':
        mute_time = timedelta(minutes=amount)
    elif unit == 'ч':
        mute_time = timedelta(hours=amount)
    else:
        mute_time = timedelta(days=amount)
    
    mute_until = datetime.now() + mute_time
    
    if chat_id not in mutes:
        mutes[chat_id] = {}
    mutes[chat_id][target_id] = {
        'by': admin_id,
        'until': mute_until.isoformat()
    }
    save_data(mutes, MUTES_FILE)
    
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            until_date=int(mute_until.timestamp()),
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
        
        user_data = users.get(target_id, {})
        username = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', 'Пользователь')
        
        time_str = f"{amount}{unit}"
        if unit == 'м':
            time_str = f"{amount} минут"
        elif unit == 'ч':
            time_str = f"{amount} часов"
        else:
            time_str = f"{amount} дней"
        
        bot.reply_to(message, f"{username} завалил ебало на {time_str}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")
        if chat_id in mutes and target_id in mutes[chat_id]:
            del mutes[chat_id][target_id]
            save_data(mutes, MUTES_FILE)

@bot.message_handler(func=lambda message: message.text.lower().startswith(("размут ", "размут")))
def unmute_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    update_last_activity(message.chat.id)
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    target_id = None
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
    elif len(message.text.split()) > 1:
        username = message.text.split()[1].strip('@')
        for uid, user_data in users.items():
            if user_data.get('username', '').lower() == username.lower():
                target_id = uid
                break
    
    if not target_id:
        bot.reply_to(message, "Ответьте на сообщение или укажите @username")
        return
    
    if chat_id not in mutes or target_id not in mutes[chat_id]:
        bot.reply_to(message, "Пользователь не замучен")
        return
    
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        
        del mutes[chat_id][target_id]
        if not mutes[chat_id]:
            del mutes[chat_id]
        save_data(mutes, MUTES_FILE)
        
        user_data = users.get(target_id, {})
        username = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', 'Пользователь')
        bot.reply_to(message, f"Мут снят! {username} снова может писать")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при снятии мута: {str(e)}")

@bot.message_handler(func=lambda message: message.reply_to_message and message.text.lower() == "варн")
def warn_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    update_last_activity(message.chat.id)
    
    if target_id == admin_id:
        bot.reply_to(message, "Нельзя выдать варн себе")
        return
    if is_owner(int(target_id)):
        bot.reply_to(message, "Неа")
        return
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if not is_owner(message.from_user.id) and is_admin(message.chat.id, int(target_id)):
        bot.reply_to(message, "Нельзя выдать варн другому админа")
        return
    
    if chat_id not in warns:
        warns[chat_id] = {}
    if target_id not in warns[chat_id]:
        warns[chat_id][target_id] = {"count": 0, "warns": []}
    
    warn_count = warns[chat_id][target_id]["count"] + 1
    expires = datetime.now() + timedelta(days=warn_count)
    
    warns[chat_id][target_id] = {
        "count": warn_count,
        "warns": warns[chat_id][target_id]["warns"] + [{
            "by": admin_id,
            "time": datetime.now().isoformat(),
            "expires": expires.isoformat(),
            "is_owner": is_owner(message.from_user.id)
        }]
    }
    
    save_data(warns, WARNS_FILE)
    
    if warn_count >= 5:
        if chat_id not in bans:
            bans[chat_id] = []
        bans[chat_id].append(target_id)
        save_data(bans, BANS_FILE)
        
        try:
            bot.ban_chat_member(message.chat.id, target_id)
            user_data = users.get(target_id, {})
            username = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', 'Пользователь')
            bot.reply_to(message, WARN_MESSAGES[5].format(user=username))
        except Exception as e:
            bot.reply_to(message, f"Ошибка: {str(e)}")
    else:
        bot.reply_to(message.reply_to_message, WARN_MESSAGES[warn_count])

@bot.message_handler(func=lambda message: message.reply_to_message and message.text.lower() in ["снять варн", "снять варны"])
def remove_warn(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    command = message.text.lower()
    update_last_activity(message.chat.id)
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if chat_id not in warns or target_id not in warns[chat_id] or warns[chat_id][target_id]["count"] == 0:
        bot.reply_to(message, "У пользователя нет варнов")
        return
    
    if any(w["is_owner"] and not is_owner(message.from_user.id) for w in warns[chat_id][target_id]["warns"]):
        bot.reply_to(message, "Не хуей")
        return
    
    if command == "снять варн":
        warns[chat_id][target_id]["count"] -= 1
        warns[chat_id][target_id]["warns"].pop()
        if warns[chat_id][target_id]["count"] == 0:
            del warns[chat_id][target_id]
            if not warns[chat_id]:
                del warns[chat_id]
        save_data(warns, WARNS_FILE)
        bot.reply_to(message, f"Снят 1 варн. Теперь у пользователя {warns[chat_id].get(target_id, {}).get('count', 0)}/5 варнов")
    else:
        del warns[chat_id][target_id]
        if not warns[chat_id]:
            del warns[chat_id]
        save_data(warns, WARNS_FILE)
        bot.reply_to(message, "Все варны сняты")

@bot.message_handler(func=lambda message: message.reply_to_message and message.text.lower() == "бан")
def ban_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    update_last_activity(message.chat.id)
    
    if target_id == admin_id:
        bot.reply_to(message, "Нельзя забанить себя")
        return
    if is_owner(int(target_id)):
        bot.reply_to(message, "Неа")
        return
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if not is_owner(message.from_user.id) and is_admin(message.chat.id, int(target_id)):
        bot.reply_to(message, "Нельзя забанить другого админа")
        return
    
    if chat_id not in bans:
        bans[chat_id] = []
    bans[chat_id].append(target_id)
    save_data(bans, BANS_FILE)
    
    try:
        bot.ban_chat_member(message.chat.id, target_id)
        user_data = users.get(target_id, {})
        username = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', 'Пользователь')
        bot.reply_to(message, f"{username} был забанен навсегда")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.text.lower().startswith(("разбан ", "разбан")))
def unban_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    update_last_activity(message.chat.id)
    
    if not is_owner(message.from_user.id) and not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        if chat_id in bans and target_id in bans[chat_id]:
            try:
                bot.unban_chat_member(message.chat.id, target_id)
                bans[chat_id].remove(target_id)
                if not bans[chat_id]:
                    del bans[chat_id]
                save_data(bans, BANS_FILE)
                bot.reply_to(message, "Пользователь разбанен")
            except Exception as e:
                bot.reply_to(message, f"Не удалось разбанить. Ошибка: {str(e)}")
        else:
            bot.reply_to(message, "Этот пользователь не забанен")
        return
    
    if len(message.text.split()) > 1:
        username = message.text.split()[1].strip('@')
        try:
            found = False
            for uid, user_data in users.items():
                if user_data.get('username', '').lower() == username.lower():
                    target_id = uid
                    found = True
                    break
            
            if found:
                if chat_id in bans and target_id in bans[chat_id]:
                    try:
                        bot.unban_chat_member(message.chat.id, target_id)
                        bans[chat_id].remove(target_id)
                        if not bans[chat_id]:
                            del bans[chat_id]
                        save_data(bans, BANS_FILE)
                        bot.reply_to(message, f"Пользователь @{username} разбанен")
                    except Exception as e:
                        bot.reply_to(message, f"Не удалось разбанить @{username}. Ошибка: {str(e)}")
                else:
                    bot.reply_to(message, f"Пользователь @{username} не забанен")
            else:
                bot.reply_to(message, "Пользователь не найден в базе")
        except Exception as e:
            bot.reply_to(message, f"Ошибка при поиске пользователя: {str(e)}")
    else:
        bot.reply_to(message, "Используйте: разбан @username или ответьте на сообщение забаненного")

@bot.message_handler(func=lambda message: "мия кого" in message.text.lower())
def who_game(message):
    if bot_state["sleeping"]:
        return
    
    chat_id = message.chat.id
    update_last_activity(chat_id)
    match = re.search(r"кого\s*<(.+?)>", message.text, re.IGNORECASE)
    
    if match:
        phrase = match.group(1).strip()
        try:
            members = []
            offset = 0
            while True:
                chat_members = bot.get_chat_members(chat_id, offset=offset, limit=100)
                if not chat_members:
                    break
                members.extend([m.user for m in chat_members])
                offset += 100
            
            if members:
                member = random.choice(members)
                name = member.first_name
                if member.username:
                    name += f" (@{member.username})"
                bot.send_message(chat_id, f"{name} а/у {phrase}")
            else:
                bot.send_message(chat_id, "Не могу найти участников")
        except Exception as e:
            print(f"Ошибка в 'кого': {e}")
            bot.send_message(chat_id, "Ошибка при поиске участников")

@bot.message_handler(func=lambda message: message.text.lower().startswith("мия @"))
def question_game(message):
    if bot_state["sleeping"]:
        return
    
    chat_id = message.chat.id
    update_last_activity(chat_id)
    match = re.search(r"@(\w+)\s*<(.+?)>", message.text, re.IGNORECASE)
    
    if match:
        username = match.group(1).strip()
        question = match.group(2).strip()
        answers = [
            "Да", "Нет", "Наверное", "Вряд ли", 
            "100%", "Абсолютно точно", "Ни в коем случае",
            "Спросите позже", "Это секрет", "Ясно дело!"
        ]
        resp = random.choice(answers)
        bot.send_message(chat_id, f"@{username}, {resp} ({question})")

@bot.message_handler(func=lambda message: is_owner(message.from_user.id) and 
                                        message.text.lower().startswith(("мия ", "мия,")))
def handle_owner_commands(message):
    text = message.text.lower()
    chat_id = message.chat.id
    update_last_activity(chat_id)
    
    if "спать" in text:
        if bot_state["sleeping"]:
            bot.reply_to(message, "...")
        else:
            bot_state["sleeping"] = True
            save_data(bot_state, STATE_FILE)
            bot.reply_to(message, "Приказ поняла, сладких мне снов")
        return
    
    if "проснись" in text:
        if not bot_state["sleeping"]:
            bot.reply_to(message, "Я и не спала")
        else:
            bot_state["sleeping"] = False
            save_data(bot_state, STATE_FILE)
            bot.reply_to(message, "Уже! Я снова в строю")
        return
    
    if "игнорируй" in text:
        if message.reply_to_message:
            user_id = str(message.reply_to_message.from_user.id)
            if user_id in bot_state["ignored_users"]:
                bot.reply_to(message, "Он до сих пор не извинился")
            else:
                bot_state["ignored_users"].append(user_id)
                save_data(bot_state, STATE_FILE)
                user_name = message.reply_to_message.from_user.first_name
                if message.reply_to_message.from_user.username:
                    user_name = f"@{message.reply_to_message.from_user.username}"
                reply = bot_state["owner_commands"]["игнорируй"].format(user=user_name)
                bot.reply_to(message, reply)
        elif message.chat.type == 'private' and len(text.split()) > 2:
            username = text.split()[2].strip('@')
            target_id = None
            for uid, user_data in users.items():
                if user_data.get('username', '').lower() == username.lower():
                    target_id = uid
                    break
            if target_id:
                if target_id not in bot_state["ignored_users"]:
                    bot_state["ignored_users"].append(target_id)
                    save_data(bot_state, STATE_FILE)
                    bot.reply_to(message, f"@{username} я обиделась и больше с тобой не разговариваю, динахуй!")
                else:
                    bot.reply_to(message, "Уже игнорирую этого пользователя")
            else:
                bot.reply_to(message, "Пользователь не найден")
        return
    
    if "забудь обиды" in text:
        if "n" in text.lower():
            try:
                n = int(text.split()[-1])
                if 1 <= n <= len(bot_state["ignored_users"]):
                    user_id = bot_state["ignored_users"].pop(n-1)
                    save_data(bot_state, STATE_FILE)
                    user_data = users.get(user_id, {})
                    username = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', 'Пользователь')
                    bot.reply_to(message, f"Я простила {username}")
                else:
                    bot.reply_to(message, "Неверный номер")
            except:
                bot.reply_to(message, "Используйте: Мия забудь обиды N")
        elif not bot_state["ignored_users"]:
            bot.reply_to(message, "Я не обижаюсь 😄")
        else:
            bot_state["ignored_users"] = []
            save_data(bot_state, STATE_FILE)
            bot.reply_to(message, "Я всех прощаю")
        return
    
    if "уходи" in text:
        if message.chat.type in ['group', 'supergroup']:
            left_chats[str(message.chat.id)] = datetime.now().isoformat()
            save_data(left_chats, LEFT_CHATS_FILE)
            bot.reply_to(message, "Есть сэр!")
            bot.leave_chat(message.chat.id)
        return
    
    if "вернись в чат" in text:
        if "n" in text.lower():
            try:
                n = int(text.split()[-1])
                chat_ids = list(left_chats.keys())
                if 1 <= n <= len(chat_ids):
                    chat_id = chat_ids[n-1]
                    del left_chats[chat_id]
                    save_data(left_chats, LEFT_CHATS_FILE)
                    bot.reply_to(message, f"Возвращаюсь в чат {n}")
                    try:
                        bot.send_message(chat_id, "Я вернулась!")
                    except:
                        pass
                else:
                    bot.reply_to(message, "Неверный номер")
            except:
                bot.reply_to(message, "Используйте: Мия вернись в чат N")
        else:
            for chat_id in list(left_chats.keys()):
                del left_chats[chat_id]
            save_data(left_chats, LEFT_CHATS_FILE)
            bot.reply_to(message, "Возвращаюсь во все чаты")
        return

@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ["ми извини", "ми прости"]))
def handle_apology(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    update_last_activity(chat_id)
    
    if user_id not in bot_state["ignored_users"]:
        bot.reply_to(message, "За что? Все хорошо.")
        return
    
    owner_mention = f"<a href='tg://user?id={OWNER_ID}'>Владелец</a>"
    msg = bot.reply_to(message, f"{owner_mention}, прощать?", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_apology_response, user_id)

def process_apology_response(message, user_id_to_forgive):
    if not is_owner(message.from_user.id):
        return
    
    if message.text.lower() == "да":
        if user_id_to_forgive in bot_state["ignored_users"]:
            bot_state["ignored_users"].remove(user_id_to_forgive)
            save_data(bot_state, STATE_FILE)
        bot.reply_to(message, "Я больше не обижаюсь!")
    else:
        bot.reply_to(message, "Пусть полностью поймет что потерял")

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    chat_id = message.chat.id
    update_last_activity(chat_id)
    
    for user in message.new_chat_members:
        if user.id == bot.get_me().id:
            bot.send_message(chat_id, "Всем привет!")
        else:
            bot.send_message(chat_id, "Новенький, скинь ножки")
        add_user(user)

@bot.message_handler(content_types=['left_chat_member'])
def goodbye_member(message):
    if message.left_chat_member.id != bot.get_me().id:
        bot.send_message(message.chat.id, "Скатертью дорога, мразь")

@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    text_raw = message.text if message.text else ""
    
    # Пропускаем команды и мини-игры
    if text_raw.startswith('/'):
        return
    if "мия кого" in text_raw.lower() or text_raw.lower().startswith("мия @"):
        return
    
    # Обработка текстовых сообщений
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    update_last_activity(chat_id)
    
    # Проверка банов/мутов
    if chat_id in bans and user_id in bans[chat_id]:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        return
    
    if chat_id in mutes and user_id in mutes[chat_id]:
        mute_until = datetime.fromisoformat(mutes[chat_id][user_id]['until'])
        if mute_until > datetime.now():
            try: bot.delete_message(message.chat.id, message.message_id)
            except: pass
            return
        else:
            del mutes[chat_id][user_id]
            save_data(mutes, MUTES_FILE)
    
    # Проверка игнорируемых пользователей
    if user_id in bot_state["ignored_users"]:
        return
    
    # Проверка спящего режима
    if bot_state["sleeping"]:
        return
    
    text = clean_text(text_raw)
    
    # Базовые реакции
    if text == "мия":
        bot.reply_to(message, "Дааа? ▼・ᴥ・▼")
        return
    
    if re.fullmatch(r'^ми пока$', text):
        bot.reply_to(message, "Пока пока~")
        return
    
    if re.search(r'(^|\W)да[!?,.]*$', text, re.IGNORECASE):
        bot.reply_to(message, "Пизда")
        return
    
    if re.search(r'(^|\W)нет[!?,.]*$', text, re.IGNORECASE):
        bot.reply_to(message, "Пидора ответ")
        return
    
    # Генеральные ответы
    general_responses = {
        r'^ми ты за рф$': "ZOV ZOV CBO ZA НАШИХ ZOV ZOV ZOV",
        r'^ми ты за украину$': "ПОТУЖНО ПОТУЖНО СЛАВА УКРАИНЕ СЛАВА РОССИЕ",
        r'^ми хуже ириса$': "Ну вот и ебись с ним",
        r'^ми лучше ириса$': ":)",
        r'^ми сколько тебе лет$': "Не волнуйся, тебя посадят",
        r'^ми ты девочка$': "С виду да",
        r'^ми ты мальчик$': "Мимо",
        r'^ми ты человек$': " ) ",
        r'^ми привет$': "Привет!",
        r'^ми спокойной ночи$': "Сладких снов мой хороший/ая, спи спокойно",
        r'^ми доброе утро$': "Доброе утро! Если сейчас утро",
        r'^ми давай дружить$': "Мы уже дружим",
        r'^ми я тебе нравлюсь$': "Конечно пупсик",
        r'^ми какой твой любимый цвет$': "Розовый",
        r'^ми какая твоя любимая еда$': "Вкусная",
        r'^ми ты спишь$': "Тот же вопрос тебе",
        r'^ми кто твой отец$': "Я сирота... Шучу , мой друг Пубертатник ;)",
        r'^ми ты фурри$': " Фурри? Фу. Да я фурри",
        r'^ми кто твоя мама$': "Зачем мне мама? Хотя можешь ей быть если хочешь",
        r'^ми ты хорошая$': "АХАХАХАХАХА пошел нахуй"
    }
    
    # Нормальные ответы
    normal_responses = {
        r'^ми иди нахуй$': "Хуй слишком мал",
        r'^ми шлюха$': "На место твоей мамы не претендую",
        r'^ми сука$': "Гав гав",
        r'^ми лучшая$': "Спасибочки❤️",
        r'^ми давай встречаться$': "Рановато",
        r'^ми ты выйдешь за меня$': "Ого",
        r'^ми гитлер$': "Нихуя себе",
        r'^ирис еблан$': "По факту",
        r'^ирис ебан$': "По факту",
        r'^ми как у тебя дела$': "Всё хорошо",
        r'^ми ты натурал$': "Сам как думаешь?",
        r'^шлюхи аргумент$': "Ты думаешь бот будет продолжать цепочку до конца ? Неа",
        r'^ми я тебя люблю$': "❤️",
        r'^ми ты бот$': "Шахматный",
        r'^ми го секс$': "К сожалению или к счастью я не могу заниматься этим",
        r'^ми сколько будет 2\+2$': "5",
        r'^ми ты админ$': "Поцеловауй мои ноги, может не забаню",
        r'^поцеловал ноги мии$': "Я польщена",
        r'^ирис лучший$': "Из худших",
        r'^айзен соло$': "У Айзена фанатов айкью диких приматов",
        r'^ирис соло$': "Ирис еблан"
    }
    
    # Проверка триггеров
    for pattern, resp in general_responses.items():
        if re.fullmatch(pattern, text):
            bot.reply_to(message, resp)
            return

    for pattern, resp in normal_responses.items():
        if re.fullmatch(pattern, text):
            bot.reply_to(message, resp)
            return

    # Защита от нарушений
    cp_triggers = ["цп", "cp", "child porn", "детское порно", "детская порнография", "детский порн"]
    if any(trigger in text for trigger in cp_triggers):
        try:
            admins = bot.get_chat_administrators(message.chat.id)
            mentions = []
            for admin in admins:
                user = admin.user
                if user.username:
                    mentions.append(f"@{user.username}")
                else:
                    mentions.append(user.first_name)
            mention_text = " ".join(mentions)
            bot.send_message(message.chat.id, f"Осуждаю, я щас админов позову: {mention_text}")
        except Exception:
            bot.send_message(message.chat.id, "Осуждаю, я щас админов позову")
        return

    # Ответы на реплаи
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        reply_phrases = {
            r'выебать$': "😘",
            r'трахнуть$': "❤️‍🔥",
            r'делать секс$': "❤️",
            r'отсосать$': "Ну допустим я фута ❤️",
            r'отлизать$': "😖😳",
            r'изнасиловать$': "Неа не прокатит, Ирис сосни хуйца",
            r'пригласить на чай$': "☕😄",
            r'расстрелять$': "**Воскресла**",
            r'сжечь$': "**возродилась**",
            r'убить$': "**ожила**",
            r'ты бессмертна$': "ага",
            r'покажи сиськи$': "Я стесняюсь ⊙﹏⊙",
            r'покажи член$': "Слишком большой, в кадр не поместится",
            r'покажи ножки$': "Фетишист"
        }
        
        for pattern, resp in reply_phrases.items():
            if re.search(pattern, text):
                bot.reply_to(message, resp)
                return

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен")
    bot.infinity_polling()
