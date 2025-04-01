import os
import logging
import random
import json
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # Добавьте получение ID чата из env

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def summon(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение с призывом в целевой чат."""
    message_text = "Внимание всем! Просьба заглянуть в чат."
    # Пример упоминания нескольких пользователей по их username (не забудьте добавить @)
    users_to_tag = ['@username1', '@username2', '@username3']
    full_message = f"{message_text} {' '.join(users_to_tag)}"

    try:
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=full_message)
        await update.message.reply_text(f"Сообщение с призывом отправлено в чат с ID {TARGET_CHAT_ID}")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при отправке сообщения: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text("Привет! Я бот для призыва пользователей.")

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    await update.message.reply_text("Используйте команду /summon для призыва пользователей.")

async def echo(update: Update, context: CallbackContext) -> None:
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
    # Добавляем обработчик команды /summon
    application.add_handler(CommandHandler("summon", summon))

    # Добавляем обработчик эхо (для примера)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота в режиме polling
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
