import re
import os
import yt_dlp
from telebot import types

# --- Проверка ссылки ---
def is_valid_url(url):
    pattern = re.compile(r'^https?://[^\s]+$')
    return bool(pattern.match(url))

# --- Получение списка форматов видео ---
def get_video_formats(url):
    try:
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = []
        for f in info.get('formats', []):
            # Оставляем только видео с аудио
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                quality = f.get('format_note') or f.get('resolution') or 'unknown'
                if f.get('ext'):
                    formats.append({
                        'format_id': f['format_id'],
                        'quality': quality,
                        'ext': f['ext']
                    })
        return formats
    except Exception:
        return []

# --- Скачивание видео ---
def download_video(url, format_id):
    filename = "video_download.mp4"
    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'quiet': True,
        'noprogress': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return filename

# --- Обработка входящей ссылки ---
def handle_video_link(bot, message):
    url = message.text.strip()

    if not is_valid_url(url):
        bot.reply_to(message, "Некорректная ссылка")
        return

    # Сохраняем ссылку в память
    if not hasattr(bot, "user_data"):
        bot.user_data = {}
    bot.user_data[message.chat.id] = {"url": url}

    # Спрашиваем у пользователя подтверждение
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да", callback_data="confirm_download_yes"),
        types.InlineKeyboardButton("❌ Нет", callback_data="confirm_download_no")
    )
    bot.send_message(message.chat.id, "Хочешь, чтобы я скачала видео с сайта?", reply_markup=markup)

# --- Обработка нажатий кнопок ---
def handle_callback(bot, call):
    chat_id = call.message.chat.id
    user_data = bot.user_data.get(chat_id, {})

    if call.data == "confirm_download_no":
        bot.send_message(chat_id, "Поняла")
        bot.user_data.pop(chat_id, None)
        return

    if call.data == "confirm_download_yes":
        url = user_data.get("url")
        formats = get_video_formats(url)
        if not formats:
            bot.send_message(chat_id, "Не удалось получить список качеств или сайт не поддерживается.")
            bot.user_data.pop(chat_id, None)
            return

        # Создаем кнопки для выбора качества
        markup = types.InlineKeyboardMarkup()
        for f in formats[:10]:  # Показываем максимум 10 вариантов
            btn_text = f"{f['quality']} ({f['ext']})"
            callback_data = f"download_format_{f['format_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))

        bot.send_message(chat_id, "Выбери качество:", reply_markup=markup)
        bot.user_data[chat_id]["formats"] = formats

    elif call.data.startswith("download_format_"):
        format_id = call.data.replace("download_format_", "")
        url = user_data.get("url")

        bot.send_message(chat_id, "Скачиваю, подожди...")

        try:
            filename = download_video(url, format_id)

            with open(filename, "rb") as video:
                bot.send_video(chat_id, video)

            os.remove(filename)
        except Exception as e:
            bot.send_message(chat_id, f"Ошибка при скачивании: {e}")

        bot.user_data.pop(chat_id, None)