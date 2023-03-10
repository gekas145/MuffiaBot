import os, asyncio, logging
from telegram import ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, filters
from config import *
from utils import *


TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
chats = {}

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

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
        
        if check_game_stopped(chat_id, game_id):
            return
        
        chats[chat_id].registration_message_id = message.message_id
        context.job_queue.run_once(finish_registration, 
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
    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_once(finish_registration, 
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
        remove_job_if_exists(str(chat_id), context)
        remove_job_if_exists(str(chat_id) + '_day', context)
        remove_job_if_exists(str(chat_id) + '_night', context)

        message_text = game_stopped_message

        await handle_game_finish(chat_id, context)
    
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

        remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(finish_registration, 
                                   1, 
                                   data=chats[chat_id].game_id, 
                                   name=str(chat_id),
                                   chat_id=chat_id)
    
    await update_registration_message(chat_id, context)
    await context.bot.send_message(chat_id=user_id, text=successfull_registration_message)


async def finish_registration(context):
    chat_id = context.job.chat_id
    game_id = context.job.data

    chats[chat_id].game_status = GameStatus.RUNNING

    await handle_registration_message(chat_id, context)
    if check_game_stopped(chat_id, game_id):
        return

    if len(chats[chat_id].players) < MIN_PLAYERS:
        del chats[chat_id]
        await context.bot.send_message(chat_id=chat_id, text=not_enough_players_message)
        return

    await context.bot.send_message(chat_id=chat_id, text=game_begins_message)
    await asyncio.sleep(5)
    if check_game_stopped(chat_id, game_id):
        return
    
    chats[chat_id].assign_roles()
    game_stopped = await send_greetings(context)
    if game_stopped:
        return
    
    if len(chats[chat_id].mafioso) > 1:
        game_stopped = await inform_mafia_team(context)
        if game_stopped:
            return

    context.job_queue.run_once(night, 
                               5, 
                               data=chats[chat_id].game_id, 
                               name=str(chat_id) + '_night',
                               chat_id=chat_id)


def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return
    for job in current_jobs:
        job.schedule_removal()


async def night(context):
    chat_id = context.job.chat_id
    game_id = context.job.data

    chats[chat_id].nights_passed += 1
    chats[chat_id].game_status = GameStatus.NIGHT

    game_stopped = await change_players_permissions(chat_id, context, game_id=game_id)
    if game_stopped:
        return

    if chats[chat_id].nights_passed > 1:
        await handle_voters(chats[chat_id].players.values(), context)
        if check_game_stopped(chat_id, game_id):
            return
        
        victim = chats[chat_id].get_innocents_victim()

        summary_message = 'Day vote has ended\n'
        if victim is not None:
            summary_message += f'{victim.markdown_link} was lynched, he was *{victim.role}*\n'
            chats[chat_id].handle_victims([victim])
        else:
            summary_message += 'Nobody was lynched\n'
        
        for p in chats[chat_id].players.values():
            p.chosen_player_id = None
        
        summary_message += 'Remaining players:\n' + chats[chat_id].get_alive_players_description()
        
        await context.bot.send_message(chat_id=chat_id, text=summary_message, parse_mode='MarkdownV2')
        await asyncio.sleep(5)
        if check_game_stopped(chat_id, game_id):
            return

        game_ended = await check_game_finish(chat_id, context, 'after_day')
        if game_ended:
            return
    
    await context.bot.send_message(chat_id=chat_id, 
                                   text=f'*Night {chats[chat_id].nights_passed}* begins',
                                   parse_mode='MarkdownV2')
    await asyncio.sleep(5)
    if check_game_stopped(chat_id, game_id):
        return

    chats[chat_id].max_voters = len(chats[chat_id].mafioso) + int(chats[chat_id].detective is not None) + int(chats[chat_id].doctor is not None)
    chats[chat_id].voted = 0

    game_stopped = await send_mafia_vote(context)
    if game_stopped:
        return
    
    game_stopped = await send_detective_action_vote(context)
    if game_stopped:
        return
    
    game_stopped = await send_doctor_vote(context)
    if game_stopped:
        return

    context.job_queue.run_once(day, 
                               night_voting_duration, 
                               name=str(chat_id) + '_day', 
                               data=chats[chat_id].game_id, 
                               chat_id=chat_id)


async def day(context):
    chat_id = context.job.chat_id
    game_id = context.job.data

    chats[chat_id].game_status = GameStatus.DAY

    voters = chats[chat_id].get_night_voters()
    await handle_voters(voters, context)
    if check_game_stopped(chat_id, game_id):
        return

    day_message = f'*Day {chats[chat_id].nights_passed}* begins'
    victims = chats[chat_id].get_night_victims()
    for victim in victims:
        day_message += f'\n{victim.markdown_link} was killed during the night, he was *{victim.role}*'
    chats[chat_id].handle_victims(victims)

    if len(victims) == 0:
        day_message += '\nNobody was killed during the night'
    
    await context.bot.send_message(chat_id=chat_id, text=day_message, parse_mode='MarkdownV2')
    if check_game_stopped(chat_id, game_id):
        return

    game_ended = await check_game_finish(chat_id, context, 'after_night')
    if game_ended:
        return
    
    await change_players_permissions(chat_id, context, mute=False)
    if check_game_stopped(chat_id, game_id):
        return

    await context.bot.send_message(chat_id=chat_id, text=conversation_message, parse_mode='MarkdownV2')
    await asyncio.sleep(conversation_duration) # give the players time to chat
    if check_game_stopped(chat_id, game_id):
        return

    await context.bot.send_message(chat_id=chat_id, text=day_vote_message, parse_mode='MarkdownV2')
    if check_game_stopped(chat_id, game_id):
        return

    chats[chat_id].max_voters = len(chats[chat_id].players)
    chats[chat_id].voted = 0
    
    game_stopped = await send_day_vote(context)
    if game_stopped:
        return
    
    context.job_queue.run_once(night, 
                               day_voting_duration, 
                               name=str(chat_id) + '_night', 
                               data=chats[chat_id].game_id, 
                               chat_id=chat_id)


async def send_mafia_vote(context):
    reply_markup = chats[context.job.chat_id].build_mafiosi_keyboard()
    for m in chats[context.job.chat_id].mafioso.values():
        message = await context.bot.send_message(chat_id=m.id, 
                                                 text='Choose victim: ', 
                                                 reply_markup=reply_markup)
        
        if check_game_stopped(context.job.chat_id, context.job.data):
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
        
        if check_game_stopped(context.job.chat_id, context.job.data):
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
    
    if check_game_stopped(context.job.chat_id, context.job.data):
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
    
    if check_game_stopped(context.job.chat_id, context.job.data):
        return True
    
    chats[context.job.chat_id].detective.vote_message_id = message.message_id

    return False


async def send_greetings(context):
    for p in chats[context.job.chat_id].players.values():
        await context.bot.send_message(chat_id=p.id, text=greetings[p.role], parse_mode='MarkdownV2')

        if check_game_stopped(context.job.chat_id, context.job.data):
            return True
        
    return False


async def inform_mafia_team(context):
    for id in chats[context.job.chat_id].mafioso:
        message_text = 'Other mafia members: '

        other_mafia_members = filter(lambda m: m != id, chats[context.job.chat_id].mafioso.values())
        other_mafia_names = map(lambda m: m.markdown_link, other_mafia_members)

        message_text += ', '.join(other_mafia_names)
        await context.bot.send_message(chat_id=id, text=message_text, parse_mode='MarkdownV2')

        if check_game_stopped(context.job.chat_id, context.job.data):
            return True 
            
    return False


async def handle_unvoted(context, id, message_id):
    await context.bot.edit_message_text(chat_id=id, 
                                        message_id=message_id,
                                        text=voting_time_expired_message)

# cleans unused keyboard markups
async def handle_voters(voters, context):
    for vo in voters:
        if vo.vote_message_id is not None:
            message_id = vo.vote_message_id
            vo.vote_message_id = None
            await handle_unvoted(context, vo.id, message_id)

# used for both mafia and day vote
async def voting_callback(update, context):
    query = update.callback_query

    from_user_id = query.from_user.id
    chat_id, game_id, who, check_num, chosen_player_id = parse_query(query.data)

    if ignore_query(chat_id, game_id, from_user_id, who, check_num):
        return

    if chosen_player_id != 0:
        chats[chat_id].players[from_user_id].chosen_player_id = chosen_player_id
        choice_text = chats[chat_id].players[chosen_player_id].name
    else:
        choice_text = 'Skip vote'

    chats[chat_id].players[from_user_id].vote_message_id = None

    voted_message = f'{chats[chat_id].players[from_user_id].name}'
    who_chosen = chats[chat_id].players[chosen_player_id].name if chosen_player_id != 0 else ''
    voted_message += f' voted for {who_chosen}' if chosen_player_id != 0 else ' skipped'

    chats[chat_id].voted += 1

    if who == 'maf':
        when = 'day'
    else:
        when = 'night'

    handle_all_voted(chat_id, when, context)

    await query.answer()
    await query.edit_message_text(text=f'You selected: {choice_text}')

    if who == 'maf':
        for m_id in chats[chat_id].mafioso:
            if m_id != from_user_id:
                await context.bot.send_message(chat_id=m_id, text=voted_message)
    else:
        await context.bot.send_message(chat_id=chat_id, text=voted_message)


async def detective_action_choice_callback(update, context):
    query = update.callback_query

    from_user_id = query.from_user.id
    chat_id, game_id, action, check_num, _ = parse_query(query.data)

    if ignore_query(chat_id, game_id, from_user_id, action, check_num):
        return

    reply_markup = chats[chat_id].build_detective_player_keyboard(action)

    await query.answer()
    if check_game_stopped(chat_id, game_id):
        return
    
    await query.edit_message_text(text=f'Whom do you want to {action[3:]}?')
    if check_game_stopped(chat_id, game_id):
        return
    
    await query.edit_message_reply_markup(reply_markup=reply_markup)


async def detective_player_choice_callback(update, context):
    query = update.callback_query

    from_user_id = query.from_user.id
    chat_id, game_id, action, check_num, chosen_player_id = parse_query(query.data)

    if ignore_query(chat_id, game_id, from_user_id, action, check_num):
        return

    chats[chat_id].detective.vote_message_id = None

    chats[chat_id].voted += 1
    handle_all_voted(chat_id, 'day', context)

    p = chats[chat_id].players[chosen_player_id]

    if action == 'detcheck':
        await query.answer()
        await query.edit_message_text(text=f'{p.markdown_link} is *{p.role}*', parse_mode='MarkdownV2')
    else:
        chats[chat_id].detective.chosen_player_id = chosen_player_id
        await query.answer()
        await query.edit_message_text(text=f'You decided to kill {p.markdown_link}, the day will show if you were right\.\.\.',
                                      parse_mode='MarkdownV2')


async def doctor_callback(update, context):
    query = update.callback_query

    from_user_id = query.from_user.id
    chat_id, game_id, action, check_num, chosen_player_id = parse_query(query.data)

    if ignore_query(chat_id, game_id, from_user_id, action, check_num):
        return
    
    chats[chat_id].doctor.vote_message_id = None
    chats[chat_id].doctor.chosen_player_id = chosen_player_id

    chats[chat_id].voted += 1
    handle_all_voted(chat_id, 'day', context)
    
    p = chats[chat_id].players[chosen_player_id]

    message = 'You decided to heal '
    if p == chats[chat_id].doctor:
        message += 'yourself'
    else:
        message += p.markdown_link

    await query.answer()
    await query.edit_message_text(text=message,
                                  parse_mode='MarkdownV2')


# mutes/unmutes players on night/day
async def change_players_permissions(chat_id, context, game_id=None, mute=True, all=False):
    permissions = ChatPermissions(can_send_messages=not mute)
    for p in chats[chat_id].players.values():
        try:
            await context.bot.restrict_chat_member(chat_id, p.id, permissions)
            if mute and check_game_stopped(chat_id, game_id):
                return True
        except Exception: # group owners will not be muted, cuz no idea how to
            pass
    if all:
        for p in chats[chat_id].killed_players:
            try:
                await context.bot.restrict_chat_member(chat_id, p.id, permissions)
                if mute and check_game_stopped(chat_id, game_id):
                    return True
            except Exception:
                pass
    
    return False


async def handle_game_finish(chat_id, context):
    chats[chat_id].game_id = None
    await handle_registration_message(chat_id, context)
    await handle_voters(chats[chat_id].players.values(), context)
    await change_players_permissions(chat_id, context, mute=False, all=True)
    del chats[chat_id]

# removes registration button from registration message
async def handle_registration_message(chat_id, context):
    if chats[chat_id].registration_message_id:
        message_id = chats[chat_id].registration_message_id
        chats[chat_id].registration_message_id = None
        await context.bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id, 
                                                    reply_markup=None)

# updates registration message with nicknames of newly joined users
async def update_registration_message(chat_id, context):
    text = game_start_message + '\nRegistered players:\n' + chats[chat_id].get_alive_players_description()
    await context.bot.edit_message_text(chat_id=chat_id,
                                        message_id=chats[chat_id].registration_message_id,
                                        text=text,
                                        reply_markup=chats[chat_id].registration_keyboard, 
                                        parse_mode='MarkdownV2')


def handle_all_voted(chat_id, when, context):
    if chats[chat_id].voted == chats[chat_id].max_voters:
        remove_job_if_exists(f'{chat_id}_{when}', context)

        if when == 'day':
            cor = day
        else:
            cor = night
        
        context.job_queue.run_once(cor, 
                                   5, 
                                   data=chats[chat_id].game_id, 
                                   name=f'{chat_id}_{when}',
                                   chat_id=chat_id)


async def check_game_finish(chat_id, context, when):
    game_ending = chats[chat_id].check_game_ended(when)

    if game_ending is None:
        return False

    if game_ending == GameStatus.INNOCENTS_WON:
        game_finished_message = 'Innocents have won!'
        game_finished_message += chats[chat_id].get_innocents_leaders_names()
    elif game_ending == GameStatus.MAFIA_WON:
        game_finished_message = 'Mafia has won!'
        game_finished_message += chats[chat_id].get_villains_names()
    else:
        game_finished_message = "It's a draw.\n"
        game_finished_message += f'Detective: {chats[chat_id].detective.name}\n'
        game_finished_message += f'Mafioso: {list(chats[chat_id].mafioso.values())[0].name}'

    # as this function will be called in each case if game has to finish, it was placed here
    await handle_game_finish(chat_id, context)
    await context.bot.send_message(chat_id, text=game_finished_message)

    return True


def check_game_stopped(chat_id, game_id):
    return chat_id not in chats or chats[chat_id].game_id != game_id


def ignore_query(chat_id, game_id, player_id, who, check_num):
    # if query came too late and game already ended or was stopped
    if check_game_stopped(chat_id, game_id):
        return True
    # if query came too early
    if chats[chat_id].players[player_id].vote_message_id is None:
        return True
    
    # if query came too late, but game is still going on
    if (who == 'maf' or 'det' in who or who == 'doc') and chats[chat_id].game_status != GameStatus.NIGHT:
        return True
    if chats[chat_id].nights_passed != check_num:
        return True
    
    return False


def parse_query(query):
    # each query looks like
    # [chat_id]_[game_id]_action_[night_number]_[player_id]
    # player_id may be absent in some cases
    res = query.split('_')
    res[0] = int(res[0])
    res[1] = int(res[1])
    res[-2] = int(res[-2])
    res[-1] = int(res[-1]) if res[-1] != '' else None
    return res




if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('start', register, filters.Regex('-\d+')))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('begin', begin))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern='^-\d+_\d+_maf_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(voting_callback, pattern='^-\d+_\d+_dayvote_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(doctor_callback, pattern='^-\d+_\d+_doc_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(detective_action_choice_callback, pattern='^-\d+_\d+_det(?:kill|check)_\d+_$'))
    application.add_handler(CallbackQueryHandler(detective_player_choice_callback, pattern='^-\d+_\d+_det(?:kill|check)_\d+_\d+$'))

    application.run_polling()