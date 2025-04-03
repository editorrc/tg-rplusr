
import os
import logging
import random
import json
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
WHITELIST_FILE = "whitelist.json"
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
BASE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID") # Опционально: ID папки на Google Диске

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения состояния (теперь будут загружаться из Google Диска)
user_answers = {}
answer_list = []
roll_pool = []

# Инициализация клиента Google Drive
def get_gdrive_service():
    """Получение сервиса Google Drive API."""
    try:
        creds_json = json.loads(GOOGLE_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(creds_json)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Ошибка при инициализации Google Drive API: {e}")
        return None

def get_filename(chat_id, game_number="default"):
    """Формирование имени файла на Google Диске."""
    return f"answers_chat_{chat_id}_game_{game_number}.json"

def find_file_id(service, filename, parent_folder_id=None):
    """Поиск файла на Google Диске."""
    query = f"name='{filename}' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"
    try:
        results = service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])
        return items[0]['id'] if items else None
    except HttpError as error:
        logger.error(f"Ошибка при поиске файла: {error}")
        return None

def create_empty_json_on_drive(service, filename, parent_folder_id=None):
    """Создает пустой JSON-файл на Google Диске."""
    file_metadata = {'name': filename, 'mimeType': 'application/json'}
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]

    empty_json = io.BytesIO(json.dumps({}).encode('utf-8'))
    media = MediaIoBaseUpload(empty_json, mimetype="application/json")

    try:
        file = service.files().create(body=file_metadata, media_body=media).execute()
        logger.info(f"Создан пустой JSON-файл: {filename}, ID: {file['id']}")
        return file['id']
    except HttpError as error:
        logger.error(f"Ошибка при создании файла: {error}")
        return None

def load_bot_state(chat_id, game_number="default"):
    """Загрузка состояния бота из Google Диска."""
    global user_answers, answer_list, roll_pool
    service = get_gdrive_service()
    if not service:
        logger.error("Не удалось получить доступ к Google Drive.")
        return

    filename = get_filename(chat_id, game_number)
    file_id = find_file_id(service, filename, BASE_FOLDER_ID)

    if not file_id:
        logger.info(f"Файл {filename} не найден. Создаем пустой JSON...")
        file_id = create_empty_json_on_drive(service, filename, BASE_FOLDER_ID)

    if file_id:
        try:
            request = service.files().get_media(fileId=file_id)
            file_content = request.execute()
            state = json.loads(file_content.decode('utf-8'))
            user_answers = state.get("user_answers", {})
            answer_list = state.get("answer_list", [])
            roll_pool = state.get("roll_pool", [])
            logger.info(f"Состояние бота загружено из Google Диска (ID: {file_id}).")
            logger.info(f"Состояние user_answers после загрузки: {user_answers}") # Добавлено логирование
            logger.info(f"Состояние answer_list после загрузки: {answer_list}") # Добавлено логирование
            logger.info(f"Состояние roll_pool после загрузки: {roll_pool}") # Добавлено логирование
        except HttpError as error:
            logger.error(f"Ошибка загрузки файла с Google Диска: {error}")
            user_answers, answer_list, roll_pool = {}, [], []
        except json.JSONDecodeError:
            logger.error(f"Файл {filename} содержит некорректный JSON.")
            user_answers, answer_list, roll_pool = {}, [], []
    else:
        logger.error(f"Не удалось создать файл {filename} на Google Диске.")
        user_answers, answer_list, roll_pool = {}, [], []

def save_bot_state(chat_id, game_number="default"):
    """Сохранение состояния бота на Google Диск."""
    service = get_gdrive_service()
    if not service:
        logger.error("Не удалось получить доступ к Google Drive.")
        return

    filename = get_filename(chat_id, game_number)
    file_id = find_file_id(service, filename, BASE_FOLDER_ID)

    state = {
        "user_answers": user_answers,
        "answer_list": answer_list,
        "roll_pool": roll_pool
    }
    json_data = io.BytesIO(json.dumps(state, ensure_ascii=False, indent=4).encode('utf-8'))
    media = MediaIoBaseUpload(json_data, mimetype="application/json")

    try:
        if file_id:
            request = service.files().update(fileId=file_id, media_body=media)
            updated_file = request.execute()
            logger.info(f"Состояние обновлено на Google Диске (ID: {updated_file.get('id')}).")
            logger.info(f"Состояние user_answers после сохранения: {user_answers}") # Добавлено логирование
            logger.info(f"Состояние answer_list после сохранения: {answer_list}") # Добавлено логирование
            logger.info(f"Состояние roll_pool после сохранения: {roll_pool}") # Добавлено логирование
        else:
            file_metadata = {'name': filename, 'mimeType': 'application/json'}
            if BASE_FOLDER_ID:
                file_metadata['parents'] = [BASE_FOLDER_ID]
            request = service.files().create(body=file_metadata, media_body=media)
            created_file = request.execute()
            logger.info(f"Состояние сохранено на Google Диске (ID: {created_file.get('id')}).")
            logger.info(f"Состояние user_answers после создания: {user_answers}") # Добавлено логирование
            logger.info(f"Состояние answer_list после создания: {answer_list}") # Добавлено логирование
            logger.info(f"Состояние roll_pool после создания: {roll_pool}") # Добавлено логирование
    except HttpError as error:
        logger.error(f"Ошибка сохранения файла на Google Диске: {error}")

def load_whitelist():
    """Загрузка белого списка (локально)"""
    try:
        with open(WHITELIST_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return {7780504410}

def save_whitelist(whitelist):
    """Сохранение белого списка (локально)"""
    with open(WHITELIST_FILE, "w") as f:
        json.dump(list(whitelist), f)

# Загрузка белого списка при старте
whitelist = load_whitelist()

async def start(update: Update, context: CallbackContext):
    """Стартовая команда"""
    await update.message.reply_text(
        "Привет! Я бот для учета правильных ответов и розыгрыша. "
        "Основные команды: ++ - добавить ответ /rprlb - показать таблицу лидеров /rpr - розыгрыш победителя"
    )

async def _format_leaderboard(user_answers, context):
    """Форматирование таблицы лидеров"""
    logger.info(f"Состояние user_answers в _format_leaderboard: {user_answers}") # Добавлено логирование
    if not user_answers:
        return "🏆 Таблица лидеров пуста."

    leaderboard = "🏆 *Таблица лидеров* 🏆\n\n"

    # Создаем список всех ответов с текстом и пользователем
    all_answers_with_text = []
    for user_id, answers in user_answers.items():
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else user.full_name
        except Exception:
            username = f"ID {user_id}"
        for answer in answers:
            all_answers_with_text.append((answer["number"], username, answer["text"]))

    all_answers_with_text.sort(key=lambda item: item[0])  # Сортируем по номеру

    for number, username, text in all_answers_with_text:
        leaderboard += f"{number}. {username} - {text}\n"

    leaderboard += "\n📊 *Сводка по баллам:*\n"
    user_scores = {}
    for user_id, answers in user_answers.items():
        try:
            user = await context.bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else user.full_name
        except Exception:
            username = f"ID {user_id}"
        user_scores[username] = len(answers)

    sorted_scores = sorted(user_scores.items(), key=lambda item: item[1], reverse=True)
    for username, score in sorted_scores:
        leaderboard += f"{username} — {score} балл{'а' if 2 <= score <= 4 else 'ов' if score >= 5 or score == 0 else ''}\n"

    return leaderboard

async def show_leaderboard(update: Update, context: CallbackContext):
    """Показ таблицы лидеров"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)
    logger.info(f"Состояние user_answers в show_leaderboard после загрузки: {user_answers}") # Добавлено логирование
    leaderboard = await _format_leaderboard(user_answers, context)
    await update.message.reply_text(leaderboard, parse_mode='Markdown')
    save_bot_state(chat_id)

async def add_answer(update: Update, context: CallbackContext):
    """Добавление ответа"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)

    try:
        command = update.message.text.strip().lower()

        if command in ["++", "плюс", "/add", "/plus"]:
            if update.message.reply_to_message:
                if len(answer_list) >= 100:
                    await update.message.reply_text("Достигнут лимит в 100 ответов.")
                    return

                user_id = update.message.reply_to_message.from_user.id
                answer_number = len(answer_list) + 1
                message_text = update.message.reply_to_message.text
                answer_data = {"number": answer_number, "text": message_text}
                answer_list.append(answer_data)
                roll_pool.append(answer_number)

                if user_id not in user_answers:
                    user_answers[user_id] = []
                user_answers[user_id].append(answer_data)

                try:
                    user = await context.bot.get_chat(user_id)
                    username = f"@{user.username}" if user.username else user.full_name
                except Exception:
                    username = f"ID {user_id}"

                total_answers = len(user_answers[user_id])
                await update.message.reply_text(f"Ответ пользователя {username} добавлен. Всего ответов: {total_answers} балл{'а' if total_answers == 1 else 'а' if 2 <= total_answers <= 4 else 'ов'}.")
                logger.info(f"Состояние user_answers перед сохранением: {user_answers}") # Добавлено логирование
                await show_leaderboard(update, context)
                save_bot_state(chat_id)
                logger.info(f"Состояние user_answers после сохранения: {user_answers}") # Добавлено логирование
            else:
                await show_leaderboard(update, context)

        elif command in ["/rprlb", "/rpr_table"]:
            await show_leaderboard(update, context)

        else:
            await update.message.reply_text("Используйте команду /плюс или ++.")

    except Exception as e:
        logger.error(f"Ошибка в add_answer: {e}")
        await update.message.reply_text("Ошибка при добавлении ответа.")

async def remove_answer(update: Update, context: CallbackContext):
    """Удаление ответа"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)

    try:
        if not context.args:
            await update.message.reply_text("Используйте: /минус <номер ответа>")
            return

        answer_number_to_remove = int(context.args[0])

        # Удаляем ответ из answer_list
        answer_list[:] = [item for item in answer_list if item["number"] != answer_number_to_remove]

        # Удаляем ответ из roll_pool
        if answer_number_to_remove in roll_pool:
            roll_pool.remove(answer_number_to_remove)

        # Удаляем ответ у всех пользователей
        for user_id in list(user_answers.keys()):
            user_answers[user_id] = [item for item in user_answers[user_id] if item["number"] != answer_number_to_remove]
            if not user_answers[user_id]:
                del user_answers[user_id]

        # Корректировка номеров оставшихся ответов (необязательно при новой структуре)

        save_bot_state(chat_id)
        await update.message.reply_text(f"Ответ №{answer_number_to_remove} удален.")

    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /минус <номер ответа>")
    except Exception as e:
        logger.error(f"Error in remove_answer: {e}")
        await update.message.reply_text("Произошла ошибка при удалении ответа.")

async def roll_winner(update: Update, context: CallbackContext):
    """Розыгрыш победителя"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)

    if not roll_pool:
        await update.message.reply_text("Список ответов пуст.")
        return

    winner_number = random.choice(roll_pool)
    winner_user_id = None
    for user_id, answers in user_answers.items():
        for answer in answers:
            if answer["number"] == winner_number:
                winner_user_id = user_id
                break
        if winner_user_id:
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

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)

    try:
        target_user_id = int(context.args[0]) if context.args[0].isdigit() else (await context.bot.get_chat_member(update.effective_chat.id, context.args[0][1:])).user.id

        if target_user_id in user_answers:
            # Удаляем все ответы пользователя из roll_pool
            for answer in user_answers[target_user_id]:
                if answer["number"] in roll_pool:
                    roll_pool.remove(answer["number"])

            del user_answers[target_user_id]
            save_bot_state(chat_id)

            await update.message.reply_text("Пользователь исключен из розыгрыша.")
        else:
            await update.message.reply_text("Пользователь не найден.")

    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: !мрр @<tglink> или !мрр <id пользователя>")

async def add_to_whitelist(update: Update, context: CallbackContext):
    """Добавление пользователя в белый список"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)
    try:
        user_id = int(context.args[0])
        whitelist.add(user_id)
        save_whitelist(whitelist)
        await update.message.reply_text(f"Пользователь {user_id} добавлен в вайтлист.")
        save_bot_state(chat_id)
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wladd <id пользователя>")

async def remove_from_whitelist(update: Update, context: CallbackContext):
    """Удаление пользователя из белого списка"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)
    try:
        user_id = int(context.args[0])
        whitelist.discard(user_id)
        save_whitelist(whitelist)
        await update.message.reply_text(f"Пользователь {user_id} удален из вайтлиста.")
        save_bot_state(chat_id)
    except (ValueError, IndexError):
        await update.message.reply_text("Используйте: /rpr_wldel <id пользователя>")

async def clear_ratio(update: Update, context: CallbackContext):
    """Очистка всех данных"""
    if update.effective_user.id not in whitelist:
        return

    chat_id = update.effective_chat.id
    load_bot_state(chat_id)
    global user_answers, answer_list, roll_pool
    user_answers.clear()
    answer_list.clear()
    roll_pool.clear()
    save_bot_state(chat_id)

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
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+\+$|^плюс$|^/add$|^/plus$"), add_answer))
    application.add_handler(CommandHandler("minus", remove_answer))
    application.add_handler(CommandHandler("remove", remove_answer))
    application.add_handler(CommandHandler("del", remove_answer))

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
