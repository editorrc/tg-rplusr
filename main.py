import logging
import os
import telebot
from telebot import types

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Токен бота из переменных окружения
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")  # ID чата для рассылки

if not TOKEN:
    raise ValueError("Необходимо установить TELEGRAM_BOT_TOKEN в переменных окружения")
if not ADMIN_CHAT_ID:
    raise ValueError("Необходимо установить TELEGRAM_ADMIN_CHAT_ID в переменных окружения")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise ValueError("TELEGRAM_ADMIN_CHAT_ID должен быть числом")

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

def is_admin(chat_id):
    return chat_id == ADMIN_CHAT_ID

@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.send_message(message.chat.id, "Привет! Я бот для рассылки сообщений. Используйте /broadcast для рассылки.")

@bot.message_handler(commands=["broadcast"])
def manual_broadcast(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "У вас нет прав на выполнение этой команды.")
        return
    bot.send_message(message.chat.id, "Введите сообщение для рассылки:")
    bot.register_next_step_handler(message, process_broadcast)

def process_broadcast(message):
    if not message.text:
        bot.send_message(message.chat.id, "Сообщение не может быть пустым!")
        return
    send_broadcast(message.text)
    bot.send_message(message.chat.id, "Рассылка завершена!")

def send_broadcast(text):
    try:
        bot.send_message(ADMIN_CHAT_ID, text)
        logging.info("Сообщение успешно отправлено!")
    except telebot.apihelper.ApiException as e:
        logging.error(f"Ошибка при отправке: {e}")

def main():
    logging.info("Бот запущен")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        logging.error(f"Ошибка в работе бота: {e}")

if __name__ == "__main__":
    main()
