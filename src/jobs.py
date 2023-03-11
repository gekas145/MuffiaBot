import asyncio
from config import *
from utils.enums import GameStatus
from src import helpers, votes


async def finish_registration(context):
    chat_id = context.job.chat_id
    game_id = context.job.data

    chats[chat_id].game_status = GameStatus.RUNNING

    await helpers.handle_registration_message(chat_id, context)
    if helpers.check_game_stopped(chat_id, game_id):
        return

    if len(chats[chat_id].players) < MIN_PLAYERS:
        del chats[chat_id]
        await context.bot.send_message(chat_id=chat_id, text=not_enough_players_message)
        return

    await context.bot.send_message(chat_id=chat_id, text=game_begins_message)
    await asyncio.sleep(5)
    if helpers.check_game_stopped(chat_id, game_id):
        return
    
    chats[chat_id].assign_roles()
    game_stopped = await helpers.send_greetings(context)
    if game_stopped:
        return
    
    if len(chats[chat_id].mafioso) > 1:
        game_stopped = await helpers.inform_mafia_team(context)
        if game_stopped:
            return

    context.job_queue.run_once(night, 
                               5, 
                               data=chats[chat_id].game_id, 
                               name=str(chat_id) + '_night',
                               chat_id=chat_id)


async def night(context):
    chat_id = context.job.chat_id
    game_id = context.job.data

    chats[chat_id].nights_passed += 1
    chats[chat_id].game_status = GameStatus.NIGHT

    game_stopped = await helpers.change_players_permissions(chat_id, context, game_id=game_id)
    if game_stopped:
        return

    if chats[chat_id].nights_passed > 1:
        await helpers.handle_voters(chats[chat_id].players.values(), context)
        if helpers.check_game_stopped(chat_id, game_id):
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
        if helpers.check_game_stopped(chat_id, game_id):
            return

        game_ended = await helpers.check_game_finish(chat_id, context, 'after_day')
        if game_ended:
            return
    
    await context.bot.send_message(chat_id=chat_id, 
                                   text=f'*Night {chats[chat_id].nights_passed}* begins',
                                   parse_mode='MarkdownV2')
    await asyncio.sleep(5)
    if helpers.check_game_stopped(chat_id, game_id):
        return

    chats[chat_id].max_voters = len(chats[chat_id].mafioso) + int(chats[chat_id].detective is not None) + int(chats[chat_id].doctor is not None)
    chats[chat_id].voted = 0

    game_stopped = await votes.send_mafia_vote(context)
    if game_stopped:
        return
    
    game_stopped = await votes.send_detective_action_vote(context)
    if game_stopped:
        return
    
    game_stopped = await votes.send_doctor_vote(context)
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
    await helpers.handle_voters(voters, context)
    if helpers.check_game_stopped(chat_id, game_id):
        return

    day_message = f'*Day {chats[chat_id].nights_passed}* begins'
    victims = chats[chat_id].get_night_victims()
    for victim in victims:
        day_message += f'\n{victim.markdown_link} was killed during the night, he was *{victim.role}*'
    chats[chat_id].handle_victims(victims)

    if len(victims) == 0:
        day_message += '\nNobody was killed during the night'
    
    await context.bot.send_message(chat_id=chat_id, text=day_message, parse_mode='MarkdownV2')
    if helpers.check_game_stopped(chat_id, game_id):
        return

    game_ended = await helpers.check_game_finish(chat_id, context, 'after_night')
    if game_ended:
        return
    
    await helpers.change_players_permissions(chat_id, context, mute=False)
    if helpers.check_game_stopped(chat_id, game_id):
        return

    await context.bot.send_message(chat_id=chat_id, text=conversation_message, parse_mode='MarkdownV2')
    await asyncio.sleep(conversation_duration) # give the players time to chat
    if helpers.check_game_stopped(chat_id, game_id):
        return

    await context.bot.send_message(chat_id=chat_id, text=day_vote_message, parse_mode='MarkdownV2')
    if helpers.check_game_stopped(chat_id, game_id):
        return

    chats[chat_id].max_voters = len(chats[chat_id].players)
    chats[chat_id].voted = 0
    
    game_stopped = await votes.send_day_vote(context)
    if game_stopped:
        return
    
    context.job_queue.run_once(night, 
                               day_voting_duration, 
                               name=str(chat_id) + '_night', 
                               data=chats[chat_id].game_id, 
                               chat_id=chat_id)
    

def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return
    for job in current_jobs:
        job.schedule_removal()

