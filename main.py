import os, time
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from utils import *


TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
game_status = GameStatus.IDLE
players = []
chat_id = None


async def help(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=help_message, 
                                   parse_mode='MarkdownV2')



async def start(update, context):
    global game_status
    global chat_id

    if game_status == GameStatus.IDLE:
        game_status = GameStatus.REGISTRATION
        chat_id = update.effective_chat.id
        message_text = game_start_message
        context.job_queue.run_once(finish_registration, 10)
    else:
        message_text = game_in_progress_message
    
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=message_text, 
                                   parse_mode='MarkdownV2')


async def stop(update, context):
    global game_status
    global players
    global chat_id

    if game_status == GameStatus.IDLE:
        message_text = game_running_message
    else:
        game_status = GameStatus.IDLE
        players = []
        chat_id = None
        message_text = game_stopped_message
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message_text)

    
async def register(update, context):
    global players

    user_id = update.message.from_user.id
    if game_status == GameStatus.REGISTRATION:
        players.append(user_id)
        message_text = successfull_register_message
    elif game_status == GameStatus.IDLE:
        message_text = early_register_message
    else:
        message_text = late_register_message
    await context.bot.send_message(chat_id=user_id, text=message_text)


async def finish_registration(context):
    global game_status

    game_status = GameStatus.RUNNING
    for p in players:
        await context.bot.send_message(chat_id=p, text=greetings[0])

    context.job_queue.run_once(night, 5)


async def night(context):
    await context.bot.send_message(chat_id=chat_id, text='Night 1 begins')


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reg', register))
    application.add_handler(CommandHandler('stop', stop))

    application.run_polling()