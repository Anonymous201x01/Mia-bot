import json
import os

BLACKLIST_FILE = "left_chats.json"

def load_blacklist():
    if not os.path.exists(BLACKLIST_FILE):
        return []
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)

def add_chat(chat_id, chat_title=None):
    blacklist = load_blacklist()
    # сохраняем список в формате [{"id": chat_id, "title": chat_title}, ...]
    if not any(chat["id"] == chat_id for chat in blacklist):
        blacklist.append({"id": chat_id, "title": chat_title or "Без названия"})
        save_blacklist(blacklist)

def remove_chat_by_index(index):
    blacklist = load_blacklist()
    if 0 <= index < len(blacklist):
        removed = blacklist.pop(index)
        save_blacklist(blacklist)
        return removed
    return None

def get_blacklist():
    return load_blacklist()