import os
import logging
import random
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
WHITELIST_FILE = "whitelist.json"
ANSWERS_FILE = "answers_data.json"

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения состояния
user_answers = {}
answer_list = []
roll_pool = []

def load_whitelist():
    """Загрузка белого списка"""
    try:
        with open(WHITELIST_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        # ID администратора по умолчанию
        return {7780504410}

def save_whitelist(whitelist):
    """Сохранение белого списка"""
    with open(WHITELIST_FILE, "w") as f:
        json.dump(list(whitelist), f)

def save_bot_state():
    """Сохранение состояния бота"""
    state = {
        "user_answers": user_answers,
        "answer_list": answer_list,
        "roll_pool": roll_pool
    }
    with open(ANSWERS_FILE, "w") as f:
        json.dump(state, f)

def load_bot_state():
    """Загрузка состояния бота"""
    global user_answers, answer_list, roll_pool
    try:
        with open(ANSWERS_FILE, "r") as f:
            state = json.load(f)
            user_answers = state.get("user_answers", {})
            answer_list = state.get("answer_list", [])
            roll_pool = state.get("roll_pool", [])
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error(f"Ошибка при чтении {ANSWERS_FILE}. Используются пустые значения.")
        user_answers, answer_list, roll_pool = {}, [], []

# Загрузка данных при старте
whitelist = load_whitelist()
load_bot_state()

async def start(update: Update, context: CallbackContext):
    """Стартовая команда"""
    await update.message.reply_text(
        "Привет! Я бот для учета правильных ответов и розыгрыша.\n"
        "Основные команды:\n"
        "++ - добавить ответ\n"
        "/rprlb - показать таблицу лидеров\n"
        "/rnr - розыгрыш победителя"
    )

async def _format_leaderboard():
    """Форматирование таблицы лидеров"""
    if not user_answers:
        return "🏆 Таблица лидеров пуста."

    leaderboard = "🏆 *Таблица лидеров* 🏆\n\n"

    # Перечень всех ответов с номерами
    all_answers = []
    for user_id, answers in user_answers.items():
        username = f"ID {user_id}"  # Имена будут добавлены позже
        for answer in answers:
            all_answers.append((answer, username))

    all_answers.sort()  # Сортируем по номеру ответа
    answer_list_str = "\n".join([f"{num}. {user}" for num, user in all_answers])

    # Сумма баллов для каждого игрока
    user_scores = {}
    for user_id, answers in user_answers.items():
        user_scores[user_id] = len(answers)

    sorted_users = sorted(user_scores.items(), key=lambda item: item[1], reverse=True)
    scores_str = "\n".join([f"@{user_id} — {score} баллов" for user_id, score in sorted_users])

    return f"{leaderboard}{answer_list_str}\n\n📊 *Сводка по баллам:*\n{scores_str}"

async def show_leaderboard(update: Update, context: CallbackContext):
    """Показ таблицы лидеров"""
    if update.effective_user.id not in whitelist:
        return

    leaderboard = await _format_leaderboard()
    await update.message.reply_text(leaderboard, parse_mode='Markdown')
    save_bot_state()

async def add_answer(update: Update, context: CallbackContext):
    """Добавление ответа или показ таблицы лидеров"""
    if update.effective_user.id not in whitelist:
        return

    if update.message.reply_to_message:
        # Добавление балла
        user_id = update.message.reply_to_message.from_user.id
        answer_number = len(answer_list) + 1

        answer_list.append(answer_number)
        roll_pool.append(answer_number)

        if user_id not in user_answers:
            user_answers[user_id] = []
        user_answers[user_id].append(answer_number)

        await update.message.reply_text(f"Балл №{answer_number} добавлен пользователю ID {user_id}")
        save_bot_state()
    else:
        # Если `++` без ответа — показать таблицу лидеров
        await show_leaderboard(update, context)

async def remove_answer(update: Update, context: CallbackContext):
    """Удаление ответа"""
    if update.effective_user.id not in whitelist:
        return

    try:
        answer_number = int(context.args[0])
        if answer_number not in answer_list:
            await update.message.reply_text("Ответ с таким номером не найден.")
            return

        answer_list.remove(answer_number)
        if answer_number in roll_pool:
            roll_pool.remove(answer_number)

        # Удаляем ответ у всех пользователей
        for user_id in list(user_answers.keys()):
            if answer_number in user_answers[user_id]:
                user_answers[user_id].remove(answer_number)
                # Удаляем пользователя, если у него больше нет ответов
                if not user_answers[user_id]:
                    del user_answers[user_id]

        # Корректировка номеров оставшихся ответов
        corrected_answer_list = [num if num < answer_number else num - 1 for num in answer_list]
        answer_list.clear()
        answer_list.extend(corrected_answer_list)

        save_bot_state()
        await update.message.reply_text(f"Ответ №{answer_number} удален.")

    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /минус <номер ответа>")
    except Exception as e:
        logger.error(f"Error in remove_answer: {e}")
        await update.message.reply_text("Произошла ошибка при удалении ответа.")

async def roll_winner(update: Update, context: CallbackContext):
    """Розыгрыш победителя"""
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
        try:
            winner = await context.bot.get_chat(winner_user_id)
            winner_username = f"@{winner.username}" if winner.username else winner.full_name
        except Exception:
            winner_username = f"ID {winner_user_id}"

        await update.message.reply_text(f"Победитель: {winner_number} ({winner_username})")
    else:
        await update.message.reply_text("Не удалось определить победителя.")

async def modify_roll(update: Update, context: CallbackContext):
    """Исключение пользователя из розыгрыша"""
    if update.effective_user.id not in whitelist:
        return

    try:
        target_user_id = int(context.args[0]) if context.args[0].isdigit() else (await context.bot.get_chat_member(update.effective_chat.id, context.args[0][1:])).user.id

        if target_user_id in user_answers:
            # Удаляем все ответы пользователя из roll_pool
            for answer in user_answers[target_user_id]:
                if answer in roll_pool:
                    roll_pool.remove(answer)

            del user_answers[target_user_id]
            save_bot_state()

            await update.message.reply_text("Пользователь исключен из розыгрыша.")
        else:
            await update.message.reply_text("Пользователь не найден.")

    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: !мрр @<tglink> или !мрр <id пользователя>")

async def add_to_whitelist(update: Update, context: CallbackContext):
    """Добавление пользователя в белый список"""
    if update.effective_user.id not in whitelist:
        return

    try:
        user_id = int(context.args[0])
        whitelist.add(user_id)
        save_whitelist(whitelist)
        await update.message.reply_text(f"Пользователь {user_id} добавлен в вайтлист.")
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wladd <id пользователя>")

async def remove_from_whitelist(update: Update, context: CallbackContext):
    """Удаление пользователя из белого списка"""
    if update.effective_user.id not in whitelist:
        return

    try:
        user_id = int(context.args[0])
        whitelist.discard(user_id)
        save_whitelist(whitelist)
        await update.message.reply_text(f"Пользователь {user_id} удален из вайтлиста.")
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wldel <id пользователя>")

async def clear_ratio(update: Update, context: CallbackContext):
    """Очистка всех данных"""
    if update.effective_user.id not in whitelist:
        return

    global user_answers, answer_list, roll_pool
    user_answers.clear()
    answer_list.clear()
    roll_pool.clear()
    save_bot_state()

    await update.message.reply_text("Таблица лидеров и список ответов очищены.")

def main():
    """Основная функция запуска бота"""
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(20)
        .read_timeout(20)
        .build()
    )

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("rprun", start))
    application.add_handler(CommandHandler("rprlb", show_leaderboard))
    application.add_handler(CommandHandler("rpr_table", show_leaderboard))

    # Обработчики для добавления и удаления ответов
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+\+$|^плюс$"), add_answer))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^минус$"), remove_answer))

    # Розыгрыш и управление
    application.add_handler(CommandHandler("rpr", roll_winner))
    application.add_handler(CommandHandler("rpr_modify", modify_roll))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^мрр$"), modify_roll))

    # Управление белым списком
    application.add_handler(CommandHandler("rpr_wladd", add_to_whitelist))
    application.add_handler(CommandHandler("rpr_wldel", remove_from_whitelist))
    application.add_handler(CommandHandler("rpr_clearratio", clear_ratio))

    # Запуск бота
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
