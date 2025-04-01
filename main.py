import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

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
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Я бот для рассылки сообщений. Используйте /broadcast для рассылки.')

# Функция для команды /broadcast
async def broadcast(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.chat_id):
        await update.message.reply_text('У вас нет прав на выполнение этой команды.')
        return
    await update.message.reply_text('Введите сообщение для рассылки:')
    return  # ожидаем ввода сообщения для рассылки

# Функция обработки ввода сообщения для рассылки
async def process_broadcast(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if not text:
        await update.message.reply_text('Сообщение не может быть пустым!')
        return
    await send_broadcast(update, context, text)

# Функция для отправки рассылки
async def send_broadcast(update: Update, context: CallbackContext, text: str) -> None:
    try:
        await context.bot.send_message(ADMIN_CHAT_ID, text)
        await update.message.reply_text('Рассылка завершена!')
        logger.info(f"Сообщение отправлено: {text}")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")
        await update.message.reply_text('Произошла ошибка при отправке рассылки.')

# Основная функция для запуска бота
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))

    # Обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
