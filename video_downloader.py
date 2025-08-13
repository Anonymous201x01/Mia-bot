import re
import os
import threading
import yt_dlp
import time

# Проверка ссылки
def is_valid_url(url):
    pattern = re.compile(r'^https?://[^\s]+$')
    return bool(pattern.match(url))

# Получение списка форматов видео
def get_video_formats(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                formats.append({
                    'format_id': f['format_id'],
                    'quality': f.get('format_note') or f.get('resolution') or 'unknown',
                    'ext': f['ext']
                })
        if not formats:
            formats.append({
                'format_id': info.get('format_id'),
                'quality': 'default',
                'ext': info.get('ext', 'mp4')
            })
        return formats

    except Exception as e:
        print("Ошибка get_video_formats:", e)
        return []

# Скачивание видео
def download_video(url, format_id, bot, chat_id, waiting_msg_id):
    try:
        filename = "video_download.mp4"
        ydl_opts = {
            'format': format_id,
            'outtmpl': filename,
            'quiet': True,
            'noprogress': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Отправка видео
        with open(filename, "rb") as video:
            bot.send_video(chat_id, video)

        os.remove(filename)

    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при скачивании: {e}")

    # Удаляем сообщение "подождите..."
    try:
        bot.delete_message(chat_id, waiting_msg_id)
    except:
        pass

# --- Обработка входящей ссылки ---
def handle_video_link(bot, message):
    url = message.text.strip()

    if not is_valid_url(url):
        bot.reply_to(message, "Некорректная ссылка")
        return

    if not hasattr(bot, "user_data"):
        bot.user_data = {}

    # Получаем форматы
    formats = get_video_formats(url)
    if not formats:
        bot.send_message(message.chat.id, "Не удалось получить список качеств или сайт не поддерживается.")
        return

    # Сохраняем контекст ожидания подтверждения
    bot.user_data[message.chat.id] = {
        "url": url,
        "awaiting_confirmation": True,
        "formats": formats
    }

    # Сообщение "Скачать видео?"
    msg = bot.send_message(message.chat.id, "Скачать видео? Д/Н")
    bot.user_data[message.chat.id]["confirmation_msg_id"] = msg.message_id

    # Таймер на 5 минут для автоматического удаления
    def timeout():
        time.sleep(300)  # 5 минут
        data = bot.user_data.get(message.chat.id)
        if data and data.get("awaiting_confirmation"):
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
            bot.user_data.pop(message.chat.id, None)

    threading.Thread(target=timeout).start()

# --- Обработка текстового ответа ---
def handle_text_response(bot, message):
    chat_id = message.chat.id
    text = message.text.strip().lower()

    user_data = getattr(bot, "user_data", {}).get(chat_id)
    if not user_data:
        return

    # Если ожидаем подтверждение Д/Н
    if user_data.get("awaiting_confirmation"):
        if text == "н":
            bot.send_message(chat_id, "Отмена")
            bot.user_data.pop(chat_id, None)
            return
        if text == "д":
            # Отправляем список форматов с номерами
            formats = user_data.get("formats", [])
            msg_text = "Выберите качество (напишите номер):\n"
            for i, f in enumerate(formats[:10], 1):  # максимум 10 вариантов
                msg_text += f"{i}. {f['quality']} ({f['ext']})\n"
            msg = bot.send_message(chat_id, msg_text)
            user_data["awaiting_confirmation"] = False
            user_data["awaiting_format_choice"] = True
            user_data["formats_msg_id"] = msg.message_id
            return

    # Если ожидаем выбор формата
    if user_data.get("awaiting_format_choice"):
        if text.isdigit():
            idx = int(text) - 1
            formats = user_data.get("formats", [])
            if 0 <= idx < len(formats):
                format_id = formats[idx]['format_id']
                url = user_data.get("url")
                waiting_msg = bot.send_message(chat_id, "Подождите...")
                threading.Thread(target=download_video, args=(url, format_id, bot, chat_id, waiting_msg.message_id)).start()
                # Удаляем контекст
                try:
                    bot.delete_message(chat_id, user_data.get("formats_msg_id"))
                except:
                    pass
                bot.user_data.pop(chat_id, None)
                return
            else:
                bot.send_message(chat_id, "Неверный номер, попробуйте снова.")
                return
