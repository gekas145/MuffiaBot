from config import *
from utils.enums import GameStatus
from utils.player import Player
from utils.chat import Chat
from src import helpers, jobs

# /help
async def help(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=help_message, 
                                   parse_mode='MarkdownV2')

# /start
async def start(update, context):
    global chats
    chat_id = update.effective_chat.id

    if chat_id > 0:
        await context.bot.send_message(chat_id=chat_id, 
                                       text=game_private_message, 
                                       parse_mode='MarkdownV2')
    elif chat_id not in chats:
        chats[chat_id] = Chat(chat_id, context.bot.username)
        game_id = chats[chat_id].game_id

        message = await context.bot.send_message(chat_id=chat_id, 
                                                 text=game_start_message,
                                                 reply_markup=chats[chat_id].registration_keyboard, 
                                                 parse_mode='MarkdownV2')
        
        if helpers.check_game_stopped(chat_id, game_id):
            return
        
        chats[chat_id].registration_message_id = message.message_id
        context.job_queue.run_once(jobs.finish_registration, 
                                   registration_duration, 
                                   name=str(chat_id), 
                                   data=chats[chat_id].game_id, 
                                   chat_id=chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, 
                                       text=game_in_progress_message, 
                                       parse_mode='MarkdownV2')

# /begin
async def begin(update, context):
    chat_id = update.effective_chat.id

    if chat_id not in chats or chats[chat_id].game_status != GameStatus.REGISTRATION:
        await context.bot.send_message(chat_id=chat_id, text=no_active_registration_message)
        return
    
    chats[chat_id].game_status = GameStatus.RUNNING
    jobs.remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_once(jobs.finish_registration, 
                               1, 
                               data=chats[chat_id].game_id, 
                               name=str(chat_id),
                               chat_id=chat_id)

# /stop
async def stop(update, context):
    global chats

    chat_id = update.effective_chat.id
    if chat_id not in chats:
        message_text = game_idle_message
    else:
        jobs.remove_job_if_exists(str(chat_id), context)
        jobs.remove_job_if_exists(str(chat_id) + '_day', context)
        jobs.remove_job_if_exists(str(chat_id) + '_night', context)

        message_text = game_stopped_message

        await helpers.handle_game_finish(chat_id, context)
    
    await context.bot.send_message(chat_id=chat_id, text=message_text)

# called when user presses registration button
async def register(update, context):

    user_id = update.message.from_user.id
    chat_id = int(context.args[0])

    chat_in_chats = chat_id in chats

    if chat_in_chats and chats[chat_id].registration_message_id is None:
        await context.bot.send_message(chat_id=chat_id, text=registration_error_message)
        return
    
    if chat_in_chats and chats[chat_id].game_status == GameStatus.REGISTRATION:

        if user_id in chats[chat_id].players:
            await context.bot.send_message(chat_id=user_id, text=double_registration_message)
            return
        
        first_name = update.message.from_user.first_name
        last_name = update.message.from_user.last_name 
        chats[chat_id].players[user_id] = Player(user_id, first_name, last_name)

    elif chat_in_chats:
        await context.bot.send_message(chat_id=user_id, text=late_registration_message)
        return
    else:
        await context.bot.send_message(chat_id=user_id, text=early_registration_message)
        return

    if len(chats[chat_id].players) == MAX_PLAYERS:

        chats[chat_id].game_status = GameStatus.RUNNING

        jobs.remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(jobs.finish_registration, 
                                   1, 
                                   data=chats[chat_id].game_id, 
                                   name=str(chat_id),
                                   chat_id=chat_id)
    
    await helpers.update_registration_message(chat_id, context)
    await context.bot.send_message(chat_id=user_id, text=successfull_registration_message)
    