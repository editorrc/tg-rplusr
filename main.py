import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import random
import json

# Получаем токен бота из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Файл для хранения вайтлиста
WHITELIST_FILE = "whitelist.json"

# Загружаем вайтлист при запуске бота
def load_whitelist():
    try:
        with open(WHITELIST_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        # Замените 123456789 на ID администратора
        return {7780504410}

# Сохраняем вайтлист
def save_whitelist(whitelist):
    with open(WHITELIST_FILE, "w") as f:
        json.dump(list(whitelist), f)

# Белый список ID пользователей, которые могут запускать игру
whitelist = load_whitelist()

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_answers = {}
answer_list = []
roll_pool = []

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Я бот для учета правильных ответов и розыгрыша победителя. Используйте команды ++, --, рр, мрр, /rpr_wladd, /rpr_wldel и /rpr_clearratio.")

async def add_answer(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return

        command = update.message.text.strip().lower()

        if command in ["++", "плюс"]:
            if update.message.reply_to_message:
                user_id = update.message.reply_to_message.from_user.id
                answer_number = len(answer_list) + 1
                answer_list.append(answer_number)
                roll_pool.append(answer_number)

                if user_id not in user_answers:
                    user_answers[user_id] = []
                user_answers[user_id].append(answer_number)

                leaderboard = await format_leaderboard(update, context)
                user = await context.bot.get_chat(user_id)
                username = f"@{user.username}" if user.username else user.full_name
                await update.message.reply_text(f"Балл №{answer_number} добавлен пользователю {username}\n\n{leaderboard}")
                logger.info(f"User {user_id} added answer {answer_number}")
            else:
                leaderboard = await format_leaderboard(update, context)
                await update.message.reply_text(leaderboard)

        else:
            await update.message.reply_text("Используйте команду /плюс или ++.")

    except Exception as e:
        logger.error(f"Error in add_answer: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении ответа.")
        
async def remove_answer(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return

        command = update.message.text.strip().lower()
        if command.startswith("--") or command.startswith("минус") or command.startswith("уд"):
            if not context.args:
                await update.message.reply_text("Используйте: /минус <номер ответа>")
                return

            try:
                answer_number = int(context.args[0])
                if answer_number not in answer_list:
                    await update.message.reply_text("Ответ с таким номером не найден.")
                    return

                answer_list.remove(answer_number)
                # Удаляем ответ у всех пользователей
                for user_id, answers in user_answers.items():
                    if answer_number in answers:
                        answers.remove(answer_number)

                # Корректировка номеров оставшихся ответов
                for i in range(len(answer_list)):
                    if answer_list[i] > answer_number:
                        answer_list[i] -= 1

                # Коррекция номеров в user_answers
                for user_id, answers in user_answers.items():
                    for j in range(len(answers)):
                        if answers[j] > answer_number:
                            answers[j] -= 1

                await update.message.reply_text(await format_leaderboard(update, context))
                logger.info(f"User {update.effective_user.id} removed answer {answer_number}")

            except ValueError:
                await update.message.reply_text("Неверный формат. Используйте: /минус <номер ответа>")
        else:
            await update.message.reply_text("Используйте команду /минус, /уд или -- <номер ответа>.")
    except Exception as e:
        logger.error(f"Error in remove_answer: {e}")
        await update.message.reply_text("Произошла ошибка при удалении ответа.")

async def roll_winner(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return

        if not roll_pool:
            await update.message.reply_text("Список ответов пуст.")
            return

        winner_number = random.choice(roll_pool)
        winner_user_id = None
        for user_id, answers in user_answers.items():
            if winner_number in answers:
                winner_user_id = user_id
                break

        if winner_user_id:
            winner_username = (await context.bot.get_chat_member(update.effective_chat.id, winner_user_id)).user.username
            await update.message.reply_text(await format_winner(winner_number, winner_username))
            logger.info(f"User {update.effective_user.id} rolled winner {winner_number}")
        else:
            await update.message.reply_text("Не удалось определить победителя.")
    except Exception as e:
        logger.error(f"Error in roll_winner: {e}")
        await update.message.reply_text("Произошла ошибка при выборе победителя.")

async def modify_roll(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return

        try:
            target_user_id = int(context.args[0]) if context.args[0].isdigit() else (await context.bot.get_chat_member(update.effective_chat.id, context.args[0][1:])).user.id
            if target_user_id in user_answers:
                for answer in user_answers[target_user_id]:
                    if answer in roll_pool:
                        roll_pool.remove(answer)
                del user_answers[target_user_id]
                await update.message.reply_text("Пользователь исключен из розыгрыша.")
                logger.info(f"User {update.effective_user.id} modified roll for user {context.args[0]}")
            else:
                await update.message.reply_text("Пользователь не найден.")
        except (ValueError, IndexError):
            await update.message.reply_text("Используйте: !мрр @<tglink> или !мрр <id пользователя>")
    except Exception as e:
        logger.error(f"Error in modify_roll: {e}")
        await update.message.reply_text("Произошла ошибка при изменении розыгрыша.")

async def format_leaderboard(update: Update, context: CallbackContext):
    if not user_answers:
        return "🏆 Таблица рейтинга пуста."

    leaderboard = "🏆 *Таблица лидеров* 🏆\n\n"
    leaderboard += "№ | Пользователь | Баллы\n"
    leaderboard += "---|--------------|------\n"

    sorted_users = sorted(user_answers.items(), key=lambda item: len(item[1]), reverse=True)

    for i, (user_id, answers) in enumerate(sorted_users, start=1):
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else user.full_name
        except Exception:
            username = f"ID {user_id}"

        leaderboard += f"{i}. {username} - {len(answers)} баллов\n"

    return leaderboard

async def format_winner(winner_number, winner_username):
    return f"Победитель: {winner_number} (@{winner_username})"

async def add_to_whitelist(update: Update, context: CallbackContext):
    if update.effective_user.id not in whitelist:
        return

    try:
        user_id = int(context.args[0])
        whitelist.add(user_id)
        await update.message.reply_text(f"Пользователь {user_id} добавлен в вайтлист.")
        logger.info(f"User {update.effective_user.id} added {user_id} to whitelist")
        save_whitelist(whitelist)
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wladd <id пользователя>")

async def remove_from_whitelist(update: Update, context: CallbackContext):
    if update.effective_user.id not in whitelist:
        return

    try:
        user_id = int(context.args[0])
        whitelist.discard(user_id)
        await update.message.reply_text(f"Пользователь {user_id} удален из вайтлиста.")
        logger.info(f"User {update.effective_user.id} removed {user_id} from whitelist")
        save_whitelist(whitelist)
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wldel <id пользователя>")

async def clear_ratio(update: Update, context: CallbackContext):
    if update.effective_user.id not in whitelist:
        return

    user_answers.clear()
    answer_list.clear()
    roll_pool.clear()

    await update.message.reply_text("Таблица лидеров и список ответов очищены.")
    logger.info(f"User {update.effective_user.id} cleared ratio")

def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .build()
    )

    # Команды (только латиница!)
    application.add_handler(CommandHandler("rnr_toggle", start))
    application.add_handler(CommandHandler("rnr_plus", add_answer))  # ✅ Убрали "плюс"
    application.add_handler(CommandHandler("rnr_minus", remove_answer))
    application.add_handler(CommandHandler("rnr", roll_winner))
    application.add_handler(CommandHandler("rnr_del", modify_roll))
    application.add_handler(CommandHandler("rpr_wladd", add_to_whitelist))
    application.add_handler(CommandHandler("rpr_wldel", remove_from_whitelist))
    application.add_handler(CommandHandler("rpr_clearratio", clear_ratio))

    # Ловим "++" и "плюс" как обычный текст
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+\+$"), add_answer))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)^плюс$"), add_answer))

    application.run_polling()

if __name__ == "__main__":
    main()
