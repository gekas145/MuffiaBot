import os, asyncio, random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
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
nights_passed = 0


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

    
async def register(update, context):
    global players
    global game_status

    user_id = update.message.from_user.id
    success = True
    if game_status == GameStatus.REGISTRATION:
        if user_id in players:
            message_text = double_register_message
        else:
            name = update.message.from_user.first_name 
            if update.message.from_user.last_name is not None:
                name += ' ' + update.message.from_user.last_name 
            players.append(Player(user_id, name))
            message_text = successfull_register_message
    elif game_status == GameStatus.IDLE:
        message_text = early_register_message
        success = False
    else:
        message_text = late_register_message
        success = False
    await context.bot.send_message(chat_id=user_id, text=message_text)
    
    if not success:
        return

    if len(players) == MAX_PLAYERS:
        game_status = GameStatus.RUNNING
        remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(finish_registration, 0)


async def finish_registration(context):
    global game_status

    if len(players) < MIN_PLAYERS:
        await context.bot.send_message(chat_id=chat_id, text=not_enough_players_message)
        reset_globals()
        return

    game_status = GameStatus.RUNNING
    await context.bot.send_message(chat_id=chat_id, text='The game begins!')
    await asyncio.sleep(5)
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
    global nights_passed

    game_status = GameStatus.IDLE
    players = []
    mafioso = []
    chat_id = None
    max_voters = 0
    voted = 0
    nights_passed = 0


async def night(context):
    global max_voters
    global voted
    global nights_passed

    max_voters = len(mafioso)
    voted = 0
    nights_passed += 1

    night_message = f'Night {nights_passed} begins'
    if nights_passed > 1:
        await handle_voters(players, context)
        victim = get_victim()
        if victim is not None:
            night_message += f'\n {victim.name} was lynched, he was {victim.role}'
        
    await context.bot.send_message(chat_id=chat_id, text=night_message)
    await asyncio.sleep(5)

    reply_markup = build_mafiosi_keyboard()
    for m in mafioso:
        message = await context.bot.send_message(chat_id=m.id, text='Choose victim: ', 
                                                           reply_markup=reply_markup)
        m.vote_message_id = message.message_id
    
    context.job_queue.run_once(day, 60, name=str(chat_id) + '_day')


async def day(context):
    global max_voters
    global voted

    max_voters = len(players)
    voted = 0

    await handle_voters(mafioso, context)

    day_message = f'Day {nights_passed} begins'
    victim = get_victim()
    if victim is not None:
        day_message += f'\n {victim.name} was killed during the night, he was {victim.role}'
    await context.bot.send_message(chat_id=chat_id, text=day_message)
    
    await asyncio.sleep(5)

    for p in players:
        p.times_chosen = 0
        reply_markup = build_general_keyboard(p.id)
        message = await context.bot.send_message(chat_id=p.id, 
                                       text='Whom do you suspect: ',
                                       reply_markup=reply_markup)
        p.vote_message_id = message.message_id
    
    context.job_queue.run_once(night, 60, name=str(chat_id) + '_night')


async def handle_unvoted(context, id, message_id):
    await context.bot.edit_message_text(chat_id=id, 
                                        message_id=message_id,
                                        text='Voting time expired')


async def handle_voters(voters, context):
    for vo in voters:
        if not vo.voted:
            await handle_unvoted(context, vo.id, vo.vote_message_id)
        vo.reset_vote_data()


async def mafiosi_callback(update, context):
    global voted

    query = update.callback_query
    await query.answer()

    chosen_player_id = parse_query(query.data)[-1]
    chosen_player = find(players, chosen_player_id)
    chosen_player.times_chosen += 1

    await query.edit_message_text(text=f'You selected: {chosen_player.name}')

    m = find(mafioso, query.from_user.id)
    m.voted = True

    voted += 1
    if voted == max_voters:
        remove_job_if_exists(str(chat_id) + '_day', context)
        context.job_queue.run_once(day, 5)


def build_mafiosi_keyboard():
    victims = [p for p in players if p.id not in mafioso]
    keyboard = [[InlineKeyboardButton(vi.name, callback_data='maf_' + str(vi.id))] for vi in victims]
    return InlineKeyboardMarkup(keyboard)


def build_detective_keyboard():
    pass


async def general_callback(update, context):
    global voted

    query = update.callback_query
    await query.answer()

    chosen_player_id = parse_query(query.data)[-1]
    chosen_player = find(players, chosen_player_id)
    chosen_player.times_chosen += 1

    await query.edit_message_text(text=f'You selected: {chosen_player.name}')

    p = find(players, query.from_user.id)
    p.voted = True

    voted += 1
    if voted == max_voters:
        remove_job_if_exists(str(chat_id) + '_night', context)
        context.job_queue.run_once(night, 5)


def build_general_keyboard(id):
    keyboard = [[InlineKeyboardButton(p.name, callback_data='day_vote_' + str(p.id))] for p in players if p.id != id]
    return InlineKeyboardMarkup(keyboard)


def parse_query(query):
    res = query.split('_')
    res[-1] = int(res[-1])
    return res


def find(ls, val):
    try:
        return ls[ls.index(val)]
    except ValueError:
        return None


def get_victim():
    candidate = max(players, key=lambda p: p.times_chosen)
    
    count = 0
    for p in players:
        if candidate.times_chosen == p.times_chosen:
            count += 1
        if count > 1:
            break
    
    if count > 1:
        return None
    return candidate






if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reg', register))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(mafiosi_callback, pattern='^maf_*'))
    application.add_handler(CallbackQueryHandler(general_callback, pattern='^day_vote_*'))

    application.run_polling()