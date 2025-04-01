import os
import logging
import random
import json
import io
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # ID чата из переменных окружения

# Настройки логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def summon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение с призывом в целевой чат."""
    if not TARGET_CHAT_ID:
        await update.message.reply_text("Ошибка: не задан ID чата.")
        return

    message_text = "Внимание всем! Просьба заглянуть в чат."
    users_to_tag = ['@username1', '@username2', '@username3']
    full_message = f"{message_text} {' '.join(users_to_tag)}"

    try:
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=full_message)
        await update.message.reply_text(f"Сообщение отправлено в чат {TARGET_CHAT_ID}")
    except Exception as e:
        logger.exception("Ошибка при отправке сообщения в чат:")
        await update.message.reply_text(f"Ошибка при отправке сообщения: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text("Привет! Я бот для призыва пользователей.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text("Используйте команду /summon для призыва пользователей.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Эхо-обработчик для всех текстовых сообщений."""
    await update.message.reply_text(update.message.text)

async def main():
    """Основная функция запуска бота"""
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .build()
    )

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("summon", summon))

    # Добавляем обработчик эхо (для примера)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота в режиме polling
    logger.info("Бот запущен и ожидает команды...")
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
