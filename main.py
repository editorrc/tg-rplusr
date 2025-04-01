import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def send_message_command(update: Update, context: CallbackContext) -> None:
    """Отправляет сообщение в целевой чат по команде /send."""
    message_text = "Это тестовое сообщение от упрощенного бота."
    try:
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=message_text)
        await update.message.reply_text("Сообщение отправлено!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при отправке: {e}")

async def main():
    """Создание и запуск бота."""
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .build()
    )

    # Добавляем обработчик для команды /send
    application.add_handler(CommandHandler("send", send_message_command))

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
