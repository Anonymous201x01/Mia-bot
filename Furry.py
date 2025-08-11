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

bot = telebot.TeleBot(TOKEN)

WARNS_FILE = "warns.json"
BANS_FILE = "bans.json"
MUTES_FILE = "mutes.json"
USERS_FILE = "users.json"
STATE_FILE = "bot_state.json"

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

if not bot_state:
    bot_state = {
        "sleeping": False,
        "ignored_users": [],
        "owner_commands": {
            "спать": "Приказ поняла, сладких мне снов",
            "проснись": "Уже! Я снова в строю",
            "игнорируй": "{user} я обиделась и больше с тобой не разговариваю, динахуй!",
            "забудь обиды": "Я всех прощаю"
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
    active_chats[chat_id] = time.time()

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_owner(chat_id, user_id):
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
    if bot_state["sleeping"] and str(message.from_user.id) != str(OWNER_ID):
        return
    
    chat_id = message.chat.id
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
        active_chats[chat_id] = time.time()

@bot.message_handler(commands=['listusers'])
def list_users_command(message):
    if message.from_user.id != OWNER_ID:
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

@bot.message_handler(commands=['help'])
def show_owner_help(message):
    if message.chat.type != 'private' or str(message.from_user.id) != str(OWNER_ID):
        return
    
    help_text = """<b>🔐 Личные команды (начинаются с Мия):</b>
Мия спать - Спящий режим
Мия проснись - Разбудить
Мия, игнорируй [ответ] - Игнорировать
Мия забудь обиды - Простить всех

<b>👥 Админ-команды:</b>
/listusers - Список пользователей
/miahelp - Помощь для всех"""
    
    bot.reply_to(message, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text.lower().startswith("мут "))
def mute_user(message):
    clean_old_data()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
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
    if is_owner(chat_id, target_id):
        bot.reply_to(message, "Неа")
        return
    if not is_owner(chat_id, admin_id) and is_admin(chat_id, target_id):
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
            chat_id=chat_id,
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
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
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
            chat_id=chat_id,
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
    
    if target_id == admin_id:
        bot.reply_to(message, "Нельзя выдать варн себе")
        return
    if is_owner(chat_id, target_id):
        bot.reply_to(message, "Неа")
        return
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if not is_owner(chat_id, admin_id) and is_admin(chat_id, target_id):
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
            "is_owner": is_owner(chat_id, admin_id)
        }]
    }
    
    save_data(warns, WARNS_FILE)
    
    if warn_count >= 5:
        if chat_id not in bans:
            bans[chat_id] = []
        bans[chat_id].append(target_id)
        save_data(bans, BANS_FILE)
        
        try:
            bot.ban_chat_member(chat_id, target_id)
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
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if chat_id not in warns or target_id not in warns[chat_id] or warns[chat_id][target_id]["count"] == 0:
        bot.reply_to(message, "У пользователя нет варнов")
        return
    
    if any(w["is_owner"] and not is_owner(chat_id, admin_id) for w in warns[chat_id][target_id]["warns"]):
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
    
    if target_id == admin_id:
        bot.reply_to(message, "Нельзя забанить себя")
        return
    if is_owner(chat_id, target_id):
        bot.reply_to(message, "Неа")
        return
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if not is_owner(chat_id, admin_id) and is_admin(chat_id, target_id):
        bot.reply_to(message, "Нельзя забанить другого админа")
        return
    
    if chat_id not in bans:
        bans[chat_id] = []
    bans[chat_id].append(target_id)
    save_data(bans, BANS_FILE)
    
    try:
        bot.ban_chat_member(chat_id, target_id)
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
    
    if not is_owner(chat_id, admin_id) and not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if message.reply_to_message:
        target_id = str(message.reply_to_message.from_user.id)
        if chat_id in bans and target_id in bans[chat_id]:
            try:
                bot.unban_chat_member(chat_id, target_id)
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
                        bot.unban_chat_member(chat_id, target_id)
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

@bot.message_handler(func=lambda message: str(message.from_user.id) == str(OWNER_ID) and 
                                        message.text.lower().startswith(("мия ", "мия,")))
def handle_owner_commands(message):
    text = message.text.lower()
    chat_id = message.chat.id
    
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
    
    if "игнорируй" in text and message.reply_to_message:
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
        return
    
    if "забудь обиды" in text:
        if not bot_state["ignored_users"]:
            bot.reply_to(message, "Я не обижаюсь 😄")
        else:
            bot_state["ignored_users"] = []
            save_data(bot_state, STATE_FILE)
            bot.reply_to(message, "Я всех прощаю")
        return

@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ["ми извини", "ми прости"]))
def handle_apology(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id
    
    if user_id not in bot_state["ignored_users"]:
        bot.reply_to(message, "За что? Все хорошо.")
        return
    
    owner_mention = f"<a href='tg://user?id={OWNER_ID}'>Владелец</a>"
    msg = bot.reply_to(message, f"{owner_mention}, прощать?", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_apology_response, user_id)

def process_apology_response(message, user_id_to_forgive):
    if str(message.from_user.id) != str(OWNER_ID):
        return
    
    if message.text.lower() == "да":
        if user_id_to_forgive in bot_state["ignored_users"]:
            bot_state["ignored_users"].remove(user_id_to_forgive)
            save_data(bot_state, STATE_FILE)
        bot.reply_to(message, "Я больше не обижаюсь!")
    else:
        bot.reply_to(message, "Пусть полностью поймет что потерял")

@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    add_user(message.from_user)
    text_raw = message.text
    if not text_raw:
        return
    
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    
    if chat_id in bans and user_id in bans[chat_id]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return
    
    if chat_id in mutes and user_id in mutes[chat_id]:
        mute_until = datetime.fromisoformat(mutes[chat_id][user_id]['until'])
        if mute_until > datetime.now():
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass
            return
        else:
            del mutes[chat_id][user_id]
            save_data(mutes, MUTES_FILE)
    
    if user_id in bot_state["ignored_users"]:
        return
    
    if bot_state["sleeping"] and not text_raw.startswith('/'):
        return
    
    text = clean_text(text_raw)
    
    if text == "мия":
        bot.reply_to(message, "Дааа? ▼・ᴥ・▼")
        return
    
    general_responses = {
        "ми ты за рф": "ZOV ZOV CBO ZA НАШИХ ZOV ZOV ZOV",
        "ми ты за украину": "ПОТУЖНО ПОТУЖНО СЛАВА УКРАИНЕ СЛАВА РОССИЕ",
        "ми хуже ириса": "Ну вот и ебись с ним",
        "ми лучше ириса": ":)",
        "ми сколько тебе лет": "Не волнуйся, тебя посадят",
        "ми ты девочка": "С виду да",
        "ми ты мальчик": "Мимо",
        "ми ты человек": " ) ",
        "ми привет": "Привет!",
        "ми пока": "Пока пока~",
        "ми спокойной ночи": "Сладких снов мой хороший/ая, спи спокойно",
        "ми доброе утро": "Доброе утро! Если сейчас утро",
        "ми давай дружить": "Мы уже дружим",
        "ми я тебе нравлюсь": "Конечно пупсик",
        "ми какой твой любимый цвет": "Розовый",
        "ми какая твоя любимая еда": "Вкусная",
        "ми ты спишь": "Тот же вопрос тебе",
        "ми кто твой отец": "Я сирота... Шучу , мой друг Пубертатник ;)",
        "ми ты фурри": " Фурри? Фу. Да я фурри",
        "ми кто твоя мама": "Зачем мне мама? Хотя можешь ей быть если хочешь",
        "ми ты хорошая": "АХАХАХАХАХА пошел нахуй"
    }
    
    normal_responses = {
        "ми иди нахуй": "Хуй слишком мал",
        "ми шлюха": "На место твоей мамы не претендую",
        "ми сука": "Гав гав",
        "ми лучшая": "Спасибочки❤️",
        "ми давай встречаться": "Рановато",
        "ми ты выйдешь за меня": "Ого",
        "ми гитлер": "Нихуя себе",
        "ирис еблан": "По факту",
        "ирис ебан": "По факту",
        "ми как у тебя дела": "Всё хорошо",
        "ми ты натурал": "Сам как думаешь?",
        "я думаю да": "Пизда",
        "да": "Пизда",
        "нет": "Пидора ответ",
        "шлюхи аргумент": "Ты думаешь бот будет продолжать цепочку до конца ? Неа",
        "ми я тебя люблю": "❤️",
        "ми ты бот": "Шахматный",
        "ми го секс": "К сожалению или к счастью я не могу заниматься этим",
        "ми сколько будет 2+2": "5",
        "ми ты админ": "Поцеловауй мои ноги, может не забаню",
        "поцеловал ноги мии": "Я польщена",
        "ирис лучший": "Из худших",
        "айзен соло": "У Айзена фанатов айкью диких приматов",
        "ирис соло": "Ирис еблан",
    }
    
    for key, resp in general_responses.items():
        if key in text:
            bot.reply_to(message, resp)
            return
    
    for key, resp in normal_responses.items():
        if key in text:
            bot.reply_to(message, resp)
            return
    
    if "лоли" in text:
        bot.reply_to(message, "👮‍♂️")
        return
    
    cp_triggers = ["цп", "cp", "child porn", "детское порно", "детская порнография", "детский порн"]
    if any(trigger in text for trigger in cp_triggers):
        try:
            admins = bot.get_chat_administrators(chat_id)
            mentions = []
            for admin in admins:
                user = admin.user
                if user.username:
                    mentions.append(f"@{user.username}")
                else:
                    mentions.append(user.first_name)
            mention_text = " ".join(mentions)
            bot.send_message(chat_id, f"Осуждаю, я щас админов позову: {mention_text}")
        except Exception:
            bot.send_message(chat_id, "Осуждаю, я щас админов позову")
        return
    
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        reply_phrases = {
            "выебать": "😘",
            "трахнуть": "❤️‍🔥",
            "делать секс": "❤️",
            "отсосать": "Ну допустим я фута ❤️",
            "отлизать": "😖😳",
            "изнасиловать": "Неа не прокатит, Ирис сосни хуйца",
            "пригласить на чай": "☕😄",
            "расстрелять": "**Воскресла**",
            "сжечь": "**возродилась**",
            "убить": "**ожила**",
            "ты бессмертна": "ага",
            "покажи сиськи": "Я стесняюсь ⊙⁠﹏⁠⊙",
            "покажи член": "Слишком большой, в кадр не поместится",
            "покажи ножки": "Фетишист",
        }
        
        for key, resp in reply_phrases.items():
            if key in text:
                bot.reply_to(message, resp)
                return

bot.infinity_polling()
