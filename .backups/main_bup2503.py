import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, filters
import random

# Получаем токен бота из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Белый список ID пользователей, которые могут запускать игру
whitelist = {7780504410}  # Замените YOUR_ADMIN_USER_ID на свой ID

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_answers = {}
answer_list = []
roll_pool = []

async def add_answer(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return
        
        user_id = update.effective_user.id
        answer_number = len(answer_list) + 1
        answer_list.append(answer_number)
        roll_pool.append(answer_number)
        
        if user_id not in user_answers:
            user_answers[user_id] = []
        user_answers[user_id].append(answer_number)
        
        await update.message.reply_text(format_leaderboard(update, context))
        logger.info(f"User {update.effective_user.id} added answer {answer_number}")
    except Exception as e:
        logger.error(f"Error in add_answer: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении ответа.")

async def remove_answer(update: Update, context: CallbackContext):
    try:
        if update.effective_user.id not in whitelist:
            return
        
        try:
            answer_number = int(context.args[0])
            if answer_number in answer_list:
                answer_list.remove(answer_number)
                for user_id, answers in user_answers.items():
                    if answer_number in answers:
                        answers.remove(answer_number)
                await update.message.reply_text(format_leaderboard(update, context))
                logger.info(f"User {update.effective_user.id} removed answer {context.args[0]}")
            else:
                await update.message.reply_text("Ответ с таким номером не найден.")
        except (ValueError, IndexError):
            await update.message.reply_text("Используйте: -- <номер ответа>")
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
            await update.message.reply_text(format_winner(winner_number, winner_username))
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
    leaderboard = " *Таблица лидеров* \n\n"
    leaderboard += "№ | Пользователь | Баллы | Ответы\n"
    leaderboard += "---|---|---|---\n"
    
    for i, (user_id, answers) in enumerate(sorted(user_answers.items(), key=lambda item: len(item[1]), reverse=True)):
        username = (await context.bot.get_chat_member(update.effective_chat.id, user_id)).user.username
        answer_numbers = ", ".join(str(answer) for answer in answers)
        leaderboard += f"{i + 1} | @{username} | {len(answers)} | {answer_numbers}\n"
