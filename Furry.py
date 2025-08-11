import telebot
import random
import time
import os
import re
import json
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
OWNER_ID = 7107785168
MAX_COUNT = 15

bot = telebot.TeleBot(TOKEN)

# Файлы для хранения данных
WARNS_FILE = "warns.json"
BANS_FILE = "bans.json"
USERS_FILE = "users.json"
STATE_FILE = "bot_state.json"

# Загрузка данных
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
users = load_data(USERS_FILE)
bot_state = load_data(STATE_FILE)

# Инициализация состояния бота
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

# Галерея артов
arts_folder = "."
all_arts = [f for f in os.listdir(arts_folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
active_chats = {}
chat_art_pools = {}

# Сообщения для варнов
WARN_MESSAGES = {
    1: "Будь аккуратнее, предупреждение 1/5",
    2: "Веди себя хорошо, предупреждение 2/5",
    3: "Ты на грани бана, предупреждение 3/5",
    4: "Ты скоро пойдешь нахуй, предупреждение 4/5",
    5: "Покеда хуесос, предупреждение 5/5. {user} был забанен"
}

# Функции для работы с пользователями
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

# Проверка прав
def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_owner(chat_id, user_id):
    return str(user_id) == str(OWNER_ID)

# Очистка старых варнов
def clean_old_warns():
    global warns
    current_time = datetime.now()
    for chat_id in list(warns.keys()):
        for user_id in list(warns[chat_id].keys()):
            warn_data = warns[chat_id][user_id]
            if 'expires' in warn_data and datetime.fromisoformat(warn_data['expires']) < current_time:
                del warns[chat_id][user_id]
        if not warns[chat_id]:
            del warns[chat_id]
    save_data(warns, WARNS_FILE)

# Обработчики команд владельца
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

# Обработчик извинений
@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ["мия извини", "мия прости"]))
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

# Команда /Miahelp
@bot.message_handler(commands=['miahelp'])
def show_mia_help(message):
    help_text = """<b>Доступные команды для всех:</b>
/furry - Получить случайный фурри-арт
/furry N - Получить N артов (макс. 15)

<b>Мини-игры:</b>
Мия кого <действие> - Выбрать случайного участника
Мия @username <вопрос> - Задать вопрос

<b>Команды для админов:</b>
[ответ] варн - Выдать предупреждение
[ответ] снять варн - Снять 1 варн
[ответ] снять варны - Снять все варны
[ответ] бан - Забанить
разбан @username - Разбанить"""
    
    bot.reply_to(message, help_text, parse_mode="HTML")

# Команда /help (только для владельца в ЛС)
@bot.message_handler(commands=['help'])
def show_owner_help(message):
    if message.chat.type != 'private' or str(message.from_user.id) != str(OWNER_ID):
        return
    
    help_text = """<b>Личные команды:</b>
Мия спать - Спящий режим
Мия проснись - Разбудить
Мия, игнорируй [ответ] - Игнорировать
Мия забудь обиды - Простить всех

<b>Админ-команды:</b>
/listusers - Список пользователей
/miahelp - Помощь для всех

<b>Текстовые триггеры:</b>
мия привет - Приветствие
мия пока - Прощание
мия ты фурри - Ответ про фурри
ирис еблан - Ответ про Ириса
... (и другие триггеры)"""
    
    bot.reply_to(message, help_text, parse_mode="HTML")

# Команды для артов
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

# Админ-команды
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

# Система варнов/банов
@bot.message_handler(func=lambda message: message.reply_to_message and message.text.lower() == "варн")
def warn_user(message):
    clean_old_warns()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    
    if not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if is_admin(chat_id, target_id):
        bot.reply_to(message, "Ой, я не могу забанить другого админа")
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
        except Exception as e:
            bot.reply_to(message, f"Ой, я не могу забанить этого пользователя. Ошибка: {str(e)}")
            return
        
        user_mention = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.first_name
        bot.reply_to(message, WARN_MESSAGES[5].format(user=user_mention))
    else:
        bot.reply_to(message.reply_to_message, WARN_MESSAGES[warn_count])

@bot.message_handler(func=lambda message: message.reply_to_message and message.text.lower() in ["снять варн", "снять варны"])
def remove_warn(message):
    clean_old_warns()
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    command = message.text.lower()
    
    if not is_admin(chat_id, admin_id):
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
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    target_id = str(message.reply_to_message.from_user.id)
    
    if not is_admin(chat_id, admin_id):
        bot.reply_to(message, "Недостаточно прав")
        return
    
    if is_admin(chat_id, target_id):
        bot.reply_to(message, "Ой, я не могу забанить другого админа")
        return
    
    if chat_id not in bans:
        bans[chat_id] = []
    bans[chat_id].append(target_id)
    save_data(bans, BANS_FILE)
    
    try:
        bot.ban_chat_member(chat_id, target_id)
        user_mention = f"@{message.reply_to_message.from_user.username}" if message.reply_to_message.from_user.username else message.reply_to_message.from_user.first_name
        bot.reply_to(message, f"{user_mention} был забанен навсегда")
    except Exception as e:
        bot.reply_to(message, f"Ой, я не могу забанить этого пользователя. Ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.text.lower().startswith(("разбан ", "разбан")))
def unban_user(message):
    chat_id = str(message.chat.id)
    admin_id = str(message.from_user.id)
    
    if not is_admin(chat_id, admin_id):
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
            # Для разбана по юзернейму не требуется, чтобы пользователь был в чате
            # Просто пытаемся разбанить по ID из базы
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

# Мини-игры
@bot.message_handler(func=lambda message: "мия кого" in message.text.lower())
def who_game(message):
    if bot_state["sleeping"]:
        return
    
    chat_id = message.chat.id
    match = re.search(r"кого\s*<(.+?)>", message.text, re.IGNORECASE)
    
    if match:
        phrase = match.group(1).strip()
        try:
            # Получаем список участников чата
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
            print(f"Ошибка в мини-игре 'кого': {e}")
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

# Текстовые триггеры
# ... (предыдущий код остается без изменений до функции handle_text_messages)

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    # Проверка на бан и добавление пользователя
    add_user(message.from_user)
    text_raw = message.text
    if not text_raw:
        return
    
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    
    # Проверка бана
    if chat_id in bans and user_id in bans[chat_id]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return
    
    # Проверка на игнор
    if user_id in bot_state["ignored_users"]:
        return
    
    # Проверка на спящий режим (кроме команд)
    if bot_state["sleeping"] and not text_raw.startswith('/'):
        return
    
    # Приводим текст к нижнему регистру и чистим от лишних символов
    cleaned_text = clean_text(text_raw)
    active_chats[chat_id] = time.time()
print(f"cleaned_text: '{cleaned_text}'")
    # Сначала проверяем точные совпадения
    exact_responses = {
        "мия ты за рф": "ZOV ZOV CBO ZA НАШИХ ZOV ZOV ZOV",
        "мия ты за украину": "ПОТУЖНО ПОТУЖНО СЛАВА УКРАИНЕ СЛАВА РОССИЕ",
        "мия хуже ириса": "Ну вот и ебись с ним",
        "мия лучше ириса": ":)",
        "мия сколько тебе лет": "Не волнуйся, тебя посадят",
        "мия ты девочка": "С виду да",
        "мия ты мальчик": "Мимо",
        "мия ты человек": " ) ",
        "мия привет": "Привет!",
        "мия пока": "Пока пока~",
        "мия спокойной ночи": "Сладких снов мой хороший/ая, спи спокойно",
        "мия доброе утро": "Доброе утро! Если сейчас утро",
        "мия давай дружить": "Мы уже дружим",
        "мия я тебе нравлюсь": "Конечно пупсик",
        "мия какой твой любимый цвет": "Розовый",
        "мия какая твоя любимая еда": "Вкусная",
        "мия ты спишь": "Тот же вопрос тебе",
        "мия кто твой отец": "Я сирота... Шучу , мой друг Пубертатник ;)",
        "мия ты фурри": " Фурри? Фу. Да я фурри",
        "мия кто твоя мама": "Зачем мне мама? Хотя можешь ей быть если хочешь",
        "мия ты хорошая": "АХАХАХАХАХА пошел нахуй",
        "мия иди нахуй": "Хуй слишком мал",
        "мия шлюха": "На место твоей мамы не претендую",
        "мия сука": "Гав гав",
        "мия лучшая": "Спасибочки❤️",
        "мия давай встречаться": "Рановато",
        "мия ты выйдешь за меня": "Ого",
        "мия гитлер": "Нихуя себе",
        "ирис еблан": "По факту",
        "мия как у тебя дела": "Всё хорошо",
        "мия ты натурал": "Сам как думаешь?",
        "я думаю да": "Пизда",
        "да": "Пизда",
        "нет": "Пидора ответ",
        "шлюхи аргумент": "Ты думаешь бот будет продолжать цепочку до конца ? Неа",
        "мия я тебя люблю": "❤️",
        "мия ты бот": "Шахматный",
        "мия го секс": "К сожалению или к счастью я не могу заниматься этим",
        "мия сколько будет 2+2": "5",
        "мия ты админ": "Поцеловауй мои ноги, может не забаню",
        "поцеловал ноги мии": "Я польщена",
        "ирис лучший": "Из худших",
        "айзен соло": "У Айзена фанатов айкью диких приматов",
        "ирис соло": "Ирис еблан",
    }

    # Проверяем точные совпадения
    if cleaned_text in exact_responses:
        bot.reply_to(message, exact_responses[cleaned_text])
        return
    for key, resp in general_responses.items():
        if key in cleaned_text:
            bot.reply_to(message, resp)
            return

    for key, resp in normal_responses.items():
        if key in cleaned_text:
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

    # Ответы при реплае на бота
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

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
        for key, resp in reply_phrases.items():
            if key in text:
                bot.reply_to(message, resp)
                return

bot.infinity_polling()
