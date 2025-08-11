import telebot
import os

TOKEN = os.environ.get("BOT_TOKEN")  # В Railway в переменных укажи BOT_TOKEN
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот работает ✅")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "привет")
def hello(message):
    bot.reply_to(message, "Привет!")

if __name__ == "__main__":
    bot.polling(none_stop=True)
