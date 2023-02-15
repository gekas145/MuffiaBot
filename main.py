import os, asyncio, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from config import *
from utils import *


TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
MAX_PLAYERS = 2
MIN_PLAYERS = 2
game_status = GameStatus.IDLE
players = []
mafioso = []
chat_id = None
max_voters = 0
voted = 0


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
        context.job_queue.run_once(finish_registration, 10, name=str(chat_id))
    else:
        message_text = game_in_progress_message
    
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=message_text, 
                                   parse_mode='MarkdownV2')


async def stop(update, context):
    if game_status == GameStatus.IDLE:
        message_text = game_running_message
    else:
        reset_globals()
        message_text = game_stopped_message
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message_text)
    # await asyncio.sleep(5)
    # await context.bot.edit_message_text(chat_id=update.effective_chat.id, text='New text', message_id=message.message_id)

    
async def register(update, context):
    global players

    user_id = update.message.from_user.id
    if game_status == GameStatus.REGISTRATION:
        if user_id in players:
            message_text = double_register_message
        else:
            name = update.message.from_user.first_name #+ ' ' + update.message.from_user.last_name
            players.append(Player(user_id, name))
            message_text = successfull_register_message
    elif game_status == GameStatus.IDLE:
        message_text = early_register_message
    else:
        message_text = late_register_message
    await context.bot.send_message(chat_id=user_id, text=message_text)
    
    if len(players) == MAX_PLAYERS:
        remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(finish_registration, 0)


async def finish_registration(context):
    global game_status

    if len(players) < MIN_PLAYERS:
        await context.bot.send_message(chat_id=chat_id, text=not_enough_players_message)
        reset_globals()
        return

    game_status = GameStatus.RUNNING
    assign_roles()
    for p in players:
        await context.bot.send_message(chat_id=p.id, text=greetings[p.role])

    context.job_queue.run_once(night, 5)


def assign_roles():
    global mafioso
    mafiosi_ind = random.randint(0, len(players) - 1)

    for i in range(len(players)):
        if i == mafiosi_ind:
            players[i].role = PlayerRole.MAFIOSO
            mafioso.append(players[i])
        else:
            players[i].role = PlayerRole.INNOCENT


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return
    for job in current_jobs:
        job.schedule_removal()


def reset_globals():
    global game_status
    global players
    global chat_id
    global mafioso
    global max_voters
    global voted

    game_status = GameStatus.IDLE
    players = []
    mafioso = []
    chat_id = None
    max_voters = 0
    voted = 0


async def night(context):
    global max_voters
    max_voters = len(mafioso)

    await context.bot.send_message(chat_id=chat_id, text='Night 1 begins')

    reply_markup = build_mafiosi_keyboard()
    for m in mafioso:
        message = await context.bot.send_message(chat_id=m.id, text='Choose victim: ', 
                                                           reply_markup=reply_markup)
        m.vote_message_id = message.message_id
    
    context.job_queue.run_once(day, 10, name=str(chat_id) + '_day')


async def day(context):
    for m in mafioso:
        if not m.voted:
            await context.bot.edit_message_text(chat_id=m.id, 
                                                message_id=m.vote_message_id,
                                                text='Voting time expired')
        m.voted = False
        m.vote_message_id = None

    await context.bot.send_message(chat_id=chat_id, text='Day 1 begins')


async def mafiosi_callback(update, context):
    global voted

    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f'You selected: {query.data}')

    i = mafioso.index(query.from_user.id)
    mafioso[i].voted = True

    voted += 1
    if voted == max_voters:
        remove_job_if_exists(str(chat_id) + '_day', context)
        context.job_queue.run_once(day, 1)


def build_mafiosi_keyboard():
    victims = [p for p in players if p.id not in mafioso]
    keyboard = [[InlineKeyboardButton(vi.name, callback_data='maf_kill_' + str(vi.id))] for vi in victims]
    return InlineKeyboardMarkup(keyboard)


def build_detective_keyboard():
    pass


def build_general_keyboard():
    pass








if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reg', register))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(mafiosi_callback, pattern='^maf_kill_*'))

    application.run_polling()