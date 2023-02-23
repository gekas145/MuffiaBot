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
    if len(chats[chat_id].mafioso) > 1:
        await inform_mafia_team(chat_id, context)

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

        game_ended = await check_game_ended(chat_id, context, 'after_day')
        if game_ended:
            return
    
    await context.bot.send_message(chat_id=chat_id, text=f'Night {chats[chat_id].nights_passed} begins')
    await asyncio.sleep(5)

    chats[chat_id].max_voters = len(chats[chat_id].mafioso) + int(chats[chat_id].detective is not None)
    chats[chat_id].voted = 0
    await send_mafia_vote(chat_id, context)
    await send_detective_action_vote(chat_id, context)
    
    context.job_queue.run_once(day, voting_duration, name=str(chat_id) + '_day', data=chat_id)


async def day(context):
    chat_id = context.job.data

    voters = list(chats[chat_id].mafioso.values())
    if chats[chat_id].detective is not None:
        voters.append(chats[chat_id].detective)
    await handle_voters(voters, context)

    day_message = f'Day {chats[chat_id].nights_passed} begins'
    victims = chats[chat_id].get_night_victims()
    for victim in victims:
        day_message += f'\n{victim.name} was killed during the night, he was {victim.role}'
    chats[chat_id].handle_victims(victims)

    if len(victims) == 0:
        day_message += '\nNobody was killed during the night'
    
    await context.bot.send_message(chat_id=chat_id, text=day_message)

    game_ended = await check_game_ended(chat_id, context, 'after_night')
    if game_ended:
        return
    
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


async def send_mafia_vote(chat_id, context):
    reply_markup = chats[chat_id].build_mafiosi_keyboard()
    for m in chats[chat_id].mafioso.values():
        message = await context.bot.send_message(chat_id=m.id, text='Choose victim: ', 
                                                           reply_markup=reply_markup)
        m.vote_message_id = message.message_id


async def send_detective_action_vote(chat_id, context):
    if chats[chat_id].detective is None:
        return

    reply_markup = chats[chat_id].build_detective_action_keyboard()
    message = await context.bot.send_message(chat_id=chats[chat_id].detective.id, 
                                             text='What to do: ', 
                                             reply_markup=reply_markup)
    chats[chat_id].detective.vote_message_id = message.message_id


async def inform_mafia_team(chat_id, context):
    message_text = 'Other mafia members: '
    for id in chats[chat_id].mafioso:
        other_mafia_members = list(filter(lambda m: m != id, chats[chat_id].mafioso.values()))
        other_mafia_names = map(lambda m: m.name, other_mafia_members)
        message_text += ', '.join(other_mafia_names)
        await context.bot.send_message(chat_id=id, text=message_text)


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

    voted_message = f'{chats[chat_id].players[from_user_id].name}'
    who_chosen = chats[chat_id].players[chosen_player_id].name if chosen_player_id != 0 else ''
    voted_message += f' voted for {who_chosen}' if chosen_player_id != 0 else ' skipped'

    if who == 'maf':
        for m_id in chats[chat_id].mafioso:
            if m_id != from_user_id:
                await context.bot.send_message(chat_id=m_id, text=voted_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text=voted_message)

    chats[chat_id].voted += 1
    if chats[chat_id].voted == chats[chat_id].max_voters:
        if who == 'maf':
            remove_job_if_exists(str(chat_id) + '_day', context)
            context.job_queue.run_once(day, 5, data=chat_id)
        else:
            remove_job_if_exists(str(chat_id) + '_night', context)
            context.job_queue.run_once(night, 5, data=chat_id)


async def detective_action_callback(update, context):
    query = update.callback_query
    await query.answer()

    chat_id, action, _ = parse_query(query.data)

    reply_markup = chats[chat_id].build_detective_player_keyboard(action)

    await query.edit_message_text(text=f'Whom do you want to {action[3:]}?')
    await query.edit_message_reply_markup(reply_markup=reply_markup)


async def detective_player_callback(update, context):
    query = update.callback_query
    await query.answer()

    chat_id, action, chosen_player_id = parse_query(query.data)

    chats[chat_id].detective.voted = True

    p = chats[chat_id].players[chosen_player_id]
    if action == 'detcheck':
        await query.edit_message_text(text=f'{p.name} is {p.role}')
    else:
        await query.edit_message_text(text=f'You decided to kill {p.name}, the day will show if you were right...')
        chats[chat_id].detective.chosen_player_id = chosen_player_id
        
    chats[chat_id].voted += 1
    if chats[chat_id].voted == chats[chat_id].max_voters:
        remove_job_if_exists(str(chat_id) + '_day', context)
        context.job_queue.run_once(day, 5, data=chat_id)


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


async def check_game_ended(chat_id, context, when):
    game_ending = chats[chat_id].check_game_ended(when)

    if game_ending is None:
        return False

    if game_ending == GameStatus.INNOCENTS_WON:
        game_finished_message = 'Innocents have won!'
        if chats[chat_id].detective is not None:
            game_finished_message += f'\nDetective: {chats[chat_id].detective.name}'
    elif game_ending == GameStatus.MAFIA_WON:
        game_finished_message = 'Mafia has won!\nLeft mafioso:'
        for m in chats[chat_id].mafioso.values():
            game_finished_message += '\n' + m.name
    else:
        game_finished_message = "It's a draw.\n"
        game_finished_message += f'Detective: {chats[chat_id].detective.name}\n'
        game_finished_message += f'Mafioso: {list(chats[chat_id].mafioso.values())[0].name}'

    await context.bot.send_message(chat_id, text=game_finished_message)
    await handle_game_finish(chat_id, context)

    return True


def parse_query(query):
    res = query.split('_')
    res[0] = int(res[0])
    res[-1] = int(res[-1]) if res[-1] != '' else None
    return res




if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reg', register))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern=r'^-\d+_maf_\d+$'))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern=r'^-\d+_dayvote_\d+$'))
    application.add_handler(CallbackQueryHandler(detective_action_callback, pattern=r'^-\d+_det(?:kill|check)_$'))
    application.add_handler(CallbackQueryHandler(detective_player_callback, pattern=r'^-\d+_det(?:kill|check)_\d+$'))

    application.run_polling()