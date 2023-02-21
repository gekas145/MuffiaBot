import os, asyncio
from telegram import ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import *
from utils import *


TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
chats = {}


async def help(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, 
                                   text=help_message, 
                                   parse_mode='MarkdownV2')



async def start(update, context):
    global chats
    chat_id = update.effective_chat.id

    if chat_id > 0:
        message_text = game_private_message
    elif chat_id not in chats:
        chat = Chat(chat_id)
        message_text = game_start_message
        context.job_queue.run_once(finish_registration, 
                                   registration_duration, 
                                   name=str(chat_id), 
                                   data=chat_id)
        chats[chat_id] = chat
    else:
        message_text = game_in_progress_message
    
    await context.bot.send_message(chat_id=chat_id, 
                                   text=message_text, 
                                   parse_mode='MarkdownV2')


async def stop(update, context):
    global chats

    chat_id = update.effective_chat.id
    if chat_id not in chats:
        message_text = game_idle_message
    else:
        await handle_game_finish(chat_id, context)
        message_text = game_stopped_message
    
    await context.bot.send_message(chat_id=chat_id, text=message_text)

    
async def register(update, context):

    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    success = True

    if chat_id in chats and chats[chat_id].game_status == GameStatus.REGISTRATION:
        if user_id in chats[chat_id].players:
            message_text = double_register_message
            success = False
        else:
            name = update.message.from_user.first_name 
            if update.message.from_user.last_name is not None:
                name += ' ' + update.message.from_user.last_name 
            chats[chat_id].players[user_id] = Player(user_id, name)
            message_text = successfull_register_message

    elif chat_id in chats:
        message_text = late_register_message
        success = False

    else:
        message_text = early_register_message
        success = False

    await context.bot.send_message(chat_id=user_id, text=message_text)
    
    if not success:
        return

    if len(chats[chat_id].players) == MAX_PLAYERS:
        chats[chat_id].game_status = GameStatus.RUNNING
        remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(finish_registration, 0, data=chat_id)


async def finish_registration(context):
    chat_id = context.job.data

    if len(chats[chat_id].players) < MIN_PLAYERS:
        await context.bot.send_message(chat_id=chat_id, text=not_enough_players_message)
        del chats[chat_id]
        return

    chats[chat_id].game_status = GameStatus.RUNNING
    await context.bot.send_message(chat_id=chat_id, text='The game begins!')
    await asyncio.sleep(5)
    chats[chat_id].assign_roles()
    for p in chats[chat_id].players.values():
        await context.bot.send_message(chat_id=p.id, text=greetings[p.role], parse_mode='MarkdownV2')

    context.job_queue.run_once(night, 5, data=chat_id)


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return
    for job in current_jobs:
        job.schedule_removal()


async def night(context):
    chat_id = context.job.data

    await change_players_permissions(chat_id, context)

    chats[chat_id].nights_passed += 1

    if chats[chat_id].nights_passed > 1:
        await handle_voters(chats[chat_id].players.values(), context)
        victim = chats[chat_id].get_innocents_victim()

        summary_message = 'Day vote has ended\n'
        if victim is not None:
            summary_message += f'{victim.name} was lynched, he was {victim.role}'
            chats[chat_id].handle_victims([victim])
        else:
            summary_message += 'Nobody was lynched'
        
        for p in chats[chat_id].players.values():
            p.chosen_player_id = None
        
        await context.bot.send_message(chat_id=chat_id, text=summary_message)
        await asyncio.sleep(5)

        game_ending = chats[chat_id].game_ended()
        if game_ending is not None:
            if game_ending == GameStatus.INNOCENTS_WON:
                game_finished_message = 'Innocents have won!'
            else:
                game_finished_message = 'Mafia has won!\nLeft mafioso:'
                for m in chats[chat_id].mafioso.values():
                    game_finished_message += '\n' + m.name
            await context.bot.send_message(chat_id, text=game_finished_message)
            await handle_game_finish(chat_id, context)
            return
    
    await context.bot.send_message(chat_id=chat_id, text=f'Night {chats[chat_id].nights_passed} begins')
    await asyncio.sleep(5)

    chats[chat_id].max_voters = len(chats[chat_id].mafioso)
    chats[chat_id].voted = 0
    reply_markup = chats[chat_id].build_mafiosi_keyboard()
    for m in chats[chat_id].mafioso.values():
        message = await context.bot.send_message(chat_id=m.id, text='Choose victim: ', 
                                                           reply_markup=reply_markup)
        m.vote_message_id = message.message_id
    
    context.job_queue.run_once(day, voting_duration, name=str(chat_id) + '_day', data=chat_id)


async def day(context):
    chat_id = context.job.data

    await handle_voters(chats[chat_id].mafioso.values(), context)

    day_message = f'Day {chats[chat_id].nights_passed} begins'
    victim = chats[chat_id].get_mafia_victim()
    if victim is not None:
        day_message += f'\n{victim.name} was killed during the night, he was {victim.role}'
        chats[chat_id].handle_victims([victim])
    else:
        day_message += '\nNobody was killed during the night'
    await context.bot.send_message(chat_id=chat_id, text=day_message)
    
    await change_players_permissions(chat_id, context, mute=False)

    await asyncio.sleep(conversation_duration) # give the players time to chat

    chats[chat_id].max_voters = len(chats[chat_id].players)
    chats[chat_id].voted = 0
    for p in chats[chat_id].players.values():
        p.chosen_player_id = None
        reply_markup = chats[chat_id].build_general_keyboard(p.id)
        message = await context.bot.send_message(chat_id=p.id, 
                                       text='Whom do you suspect: ',
                                       reply_markup=reply_markup)
        p.vote_message_id = message.message_id
    
    context.job_queue.run_once(night, voting_duration, name=str(chat_id) + '_night', data=chat_id)


async def handle_unvoted(context, id, message_id):
    await context.bot.edit_message_text(chat_id=id, 
                                        message_id=message_id,
                                        text='Voting time expired')


async def handle_voters(voters, context):
    for vo in voters:
        if not vo.voted:
            await handle_unvoted(context, vo.id, vo.vote_message_id)
        vo.reset_vote_data()


async def voting_callback(update, context):
    query = update.callback_query
    await query.answer()

    chat_id, who, chosen_player_id = parse_query(query.data)
    from_user_id = query.from_user.id
    if chosen_player_id != 0:
        chats[chat_id].players[from_user_id].chosen_player_id = chosen_player_id
        choice_text = chats[chat_id].players[chosen_player_id].name
    else:
        choice_text = 'Skip vote'

    await query.edit_message_text(text=f'You selected: {choice_text}')

    chats[chat_id].players[from_user_id].voted = True

    if who == 'dayvote':
        voted_message = f'{chats[chat_id].players[from_user_id].name}'
        who_chosen = chats[chat_id].players[chosen_player_id].name if chosen_player_id != 0 else ''
        voted_message += f' voted for {who_chosen}' if chosen_player_id != 0 else ' skipped'
        await context.bot.send_message(chat_id, text=voted_message)

    chats[chat_id].voted += 1
    if chats[chat_id].voted == chats[chat_id].max_voters:
        if who == 'maf':
            remove_job_if_exists(str(chat_id) + '_day', context)
            context.job_queue.run_once(day, 5, data=chat_id)
        else:
            remove_job_if_exists(str(chat_id) + '_night', context)
            context.job_queue.run_once(night, 5, data=chat_id)


async def change_players_permissions(chat_id, context, mute=True, all=False):
    permissions = ChatPermissions(can_send_messages=not mute)
    for p in chats[chat_id].players.values():
        try:
            await context.bot.restrict_chat_member(chat_id, p.id, permissions)
        except Exception: # group owners will not be muted, cuz no idea how to
            pass
    if all:
        for p in chats[chat_id].killed_players:
            try:
                await context.bot.restrict_chat_member(chat_id, p.id, permissions)
            except Exception:
                pass


async def handle_game_finish(chat_id, context):
    await change_players_permissions(chat_id, context, mute=False, all=True)
    del chats[chat_id]


def parse_query(query):
    res = query.split('_')
    res[0] = int(res[0])
    res[-1] = int(res[-1])
    return res




if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reg', register))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern=r'^-\d+_maf_\d+$'))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern=r'^-\d+_dayvote_\d+$'))

    application.run_polling()