import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def summon(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение в целевой чат."""
    message_text = "Внимание всем! Просьба заглянуть в чат."
    users_to_tag = ["@username1", "@username2", "@username3"]
    full_message = f"{message_text} {' '.join(users_to_tag)}"

    try:
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=full_message)
        await update.message.reply_text(f"Сообщение отправлено в чат с ID {TARGET_CHAT_ID}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text("Привет! Я бот для призыва пользователей.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text("Используйте /summon для призыва пользователей.")

async def echo(update: Update, context: CallbackContext) -> None:
    """Эхо-обработчик."""
    await update.message.reply_text(update.message.text)

async def main():
    """Создание и запуск бота."""
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("summon", summon))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.initialize()
    await application.start()
    await application.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())  # Запускаем main в текущем event loop
