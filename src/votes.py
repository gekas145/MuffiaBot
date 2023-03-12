from config import *
from src import helpers


async def send_mafia_vote(context):
    reply_markup = chats[context.job.chat_id].build_mafiosi_keyboard()
    for m in chats[context.job.chat_id].mafioso.values():
        message = await context.bot.send_message(chat_id=m.id, 
                                                 text='Choose victim: ', 
                                                 reply_markup=reply_markup)
        
        if helpers.check_game_stopped(context.job.chat_id, context.job.data):
            return True
        
        m.vote_message_id = message.message_id

    return False


async def send_day_vote(context):
    for p in chats[context.job.chat_id].players.values():
        p.chosen_player_id = None
        reply_markup = chats[context.job.chat_id].build_general_keyboard(p.id)

        message = await context.bot.send_message(chat_id=p.id, 
                                       text='Whom do you suspect: ',
                                       reply_markup=reply_markup)
        
        if helpers.check_game_stopped(context.job.chat_id, context.job.data):
            return True

        p.vote_message_id = message.message_id
    
    return False


async def send_doctor_vote(context):
    if chats[context.job.chat_id].doctor is None:
        return
    
    reply_markup = chats[context.job.chat_id].build_doctor_keyboard()
    message = await context.bot.send_message(chat_id=chats[context.job.chat_id].doctor.id,
                                             text='Whom do you want to heal: ',
                                             reply_markup=reply_markup)
    
    if helpers.check_game_stopped(context.job.chat_id, context.job.data):
        return True
    
    chats[context.job.chat_id].doctor.vote_message_id = message.message_id

    return False


async def send_detective_action_vote(context):
    if chats[context.job.chat_id].detective is None:
        return

    reply_markup = chats[context.job.chat_id].build_detective_action_keyboard()
    message = await context.bot.send_message(chat_id=chats[context.job.chat_id].detective.id, 
                                             text='What to do: ', 
                                             reply_markup=reply_markup)
    
    if helpers.check_game_stopped(context.job.chat_id, context.job.data):
        return True
    
    chats[context.job.chat_id].detective.vote_message_id = message.message_id

    return False
