import logging
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram.ext.filters import Filters  # Исправили импорт

# Получаем токен и ID администратора из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка наличия токена и ID администратора
if not TOKEN:
    raise ValueError("Необходимо установить TELEGRAM_BOT_TOKEN в переменных окружения")
if not ADMIN_CHAT_ID:
    raise ValueError("Необходимо установить TELEGRAM_ADMIN_CHAT_ID в переменных окружения")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise ValueError("TELEGRAM_ADMIN_CHAT_ID должен быть числом")

# Функция для проверки, является ли пользователь администратором
def is_admin(chat_id: int) -> bool:
    return chat_id == ADMIN_CHAT_ID

# Функция стартового сообщения
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Я бот для рассылки сообщений. Используйте /broadcast для рассылки.')

# Функция для команды /broadcast
def broadcast(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.chat_id):
        update.message.reply_text('У вас нет прав на выполнение этой команды.')
        return
    update.message.reply_text('Введите сообщение для рассылки:')
    return  # ожидаем ввода сообщения для рассылки

# Функция обработки ввода сообщения для рассылки
def process_broadcast(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if not text:
        update.message.reply_text('Сообщение не может быть пустым!')
        return
    send_broadcast(update, context, text)

# Функция для отправки рассылки
def send_broadcast(update: Update, context: CallbackContext, text: str) -> None:
    try:
        context.bot.send_message(ADMIN_CHAT_ID, text)
        update.message.reply_text('Рассылка завершена!')
        logger.info(f"Сообщение отправлено: {text}")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")
        update.message.reply_text('Произошла ошибка при отправке рассылки.')

# Основная функция для запуска бота
def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast))

    # Обработчик сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_broadcast))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
