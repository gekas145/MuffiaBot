from config import *
from utils.enums import GameStatus
from src import jobs, helpers


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
    if helpers.check_game_stopped(chat_id, game_id):
        return
    
    await query.edit_message_text(text=f'Whom do you want to {action[3:]}?')
    if helpers.check_game_stopped(chat_id, game_id):
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


def handle_all_voted(chat_id, when, context):
    if chats[chat_id].voted == chats[chat_id].max_voters:
        jobs.remove_job_if_exists(f'{chat_id}_{when}', context)

        if when == 'day':
            cor = jobs.day
        else:
            cor = jobs.night
        
        context.job_queue.run_once(cor, 
                                   5, 
                                   data=chats[chat_id].game_id, 
                                   name=f'{chat_id}_{when}',
                                   chat_id=chat_id)
    

def ignore_query(chat_id, game_id, player_id, who, check_num):
    # if query came too late and game already ended or was stopped
    if helpers.check_game_stopped(chat_id, game_id):
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
