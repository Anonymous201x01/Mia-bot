import telebot
import random
import time
import threading
import os

TOKEN = "8131759793:AAHrptEdgk64PupEKDLoDrdPhAJ3zXjgfmA"
INTERVAL = 3 * 60 * 60
MAX_COUNT = 15

bot = telebot.TeleBot(TOKEN)

arts_folder = "arts"
all_arts = [os.path.join(arts_folder, f) for f in os.listdir(arts_folder) if f.lower().endswith((".jpg", ".png", ".jpeg"))]

active_chats = {}
chat_art_pools = {}

def get_next_art(chat_id):
    if chat_id not in chat_art_pools or not chat_art_pools[chat_id]:
        chat_art_pools[chat_id] = all_arts.copy()
        random.shuffle(chat_art_pools[chat_id])
    return chat_art_pools[chat_id].pop()

def send_art(chat_id):
    art = get_next_art(chat_id)
    with open(art, "rb") as f:
        bot.send_photo(chat_id, f)
    active_chats[chat_id] = time.time()

@bot.message_handler(commands=['furry'])
def furry_cmd(message):
    chat_id = message.chat.id
    parts = message.text.split()
    count = 1
    if len(parts) > 1 and parts[1].isdigit():
        count = min(int(parts[1]), MAX_COUNT)
    for _ in range(count):
        send_art(chat_id)

def auto_sender():
    while True:
        now = time.time()
        for chat_id, last_time in list(active_chats.items()):
            if now - last_time >= INTERVAL:
                try:
                    send_art(chat_id)
                except Exception:
                    active_chats.pop(chat_id, None)
        time.sleep(300)

threading.Thread(target=auto_sender, daemon=True).start()

bot.polling()
