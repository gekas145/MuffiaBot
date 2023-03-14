from config import *
from telegram import ChatPermissions
from utils.enums import GameStatus


# updates registration message with nicknames of newly joined users
async def update_registration_message(chat_id, context):
    text = game_start_message + '\nRegistered players:' + chats[chat_id].alive_players_links()
    await context.bot.edit_message_text(chat_id=chat_id,
                                        message_id=chats[chat_id].registration_message_id,
                                        text=text,
                                        reply_markup=chats[chat_id].registration_keyboard, 
                                        parse_mode='MarkdownV2')
    

# removes registration button from registration message
async def handle_registration_message(chat_id, context):
    if chats[chat_id].registration_message_id:
        message_id = chats[chat_id].registration_message_id
        chats[chat_id].registration_message_id = None
        await context.bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id, 
                                                    reply_markup=None)
        

def check_game_stopped(chat_id, game_id):
    return chat_id not in chats or chats[chat_id].game_id != game_id


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


# cleans unused keyboard markups
async def handle_voters(voters, context):
    for vo in voters:
        if vo.vote_message_id is not None:
            message_id = vo.vote_message_id
            vo.vote_message_id = None
            await handle_unvoted(context, vo.id, message_id)


async def handle_unvoted(context, id, message_id):
    await context.bot.edit_message_text(chat_id=id, 
                                        message_id=message_id,
                                        text=voting_time_expired_message)


async def check_game_finish(chat_id, context, when):
    game_ending = chats[chat_id].check_game_ended(when)

    if game_ending is None:
        return False

    if game_ending == GameStatus.INNOCENTS_WON:
        game_finished_message = 'Innocents have won!'
        game_finished_message += chats[chat_id].innocents_leaders_names()
    elif game_ending == GameStatus.MAFIA_WON:
        game_finished_message = 'Mafia has won!'
        game_finished_message += chats[chat_id].villains_names()
    else:
        game_finished_message = "It's a draw."
        game_finished_message += chats[chat_id].innocents_leaders_names()
        game_finished_message += chats[chat_id].villains_names()

    # as this function will be called in each case if game has to finish, it was placed here
    await handle_game_finish(chat_id, context)
    await context.bot.send_message(chat_id, text=game_finished_message)

    return True


async def handle_game_finish(chat_id, context):
    chats[chat_id].game_id = None
    await handle_registration_message(chat_id, context)
    await handle_voters(chats[chat_id].players.values(), context)
    await change_players_permissions(chat_id, context, mute=False, all=True)
    del chats[chat_id]
    