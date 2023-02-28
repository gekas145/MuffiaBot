from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, helpers
import config
import random

class GameStatus(Enum):
    REGISTRATION = 0
    RUNNING = 1
    DAY = 2
    NIGHT = 3
    MAFIA_WON = 4
    INNOCENTS_WON = 5
    DRAW = 6


class PlayerRole(str, Enum):
    INNOCENT = 'innocent'
    DETECTIVE = 'detective'
    MAFIOSO = 'mafioso'


class Player:
    def __init__(self, id, first_name, last_name):
        self.id = id # telegram user id
        self.name = first_name # telegram nick
        if last_name:
            self.name += ' ' + last_name
        self.markdown_link = helpers.mention_markdown(self.id, self.name, version=2) # telegram markdown link to user
        self.role = PlayerRole.INNOCENT # players with special roles will get this field updated at roles assigning
        self.vote_message_id = None # id of last vote message
        self.chosen_player_id = None # id of player chosen on voting

    def __eq__(self, __o):
        if isinstance(__o, int):
            return __o == self.id

        if isinstance(__o, Player):
            return __o.id == self.id
            
        return False
    
    def __hash__(self):
        return self.id


class Chat:
    def __init__(self, id, bot_username):
        self.id = id # telegram chat id
        self.game_status = GameStatus.REGISTRATION
        self.registration_message_id = None
        self.players = {}
        self.mafioso = {}
        self.detective = None
        self.killed_players = []
        self.max_voters = 0
        self.voted = 0
        self.nights_passed = 0
        url = helpers.create_deep_linked_url(bot_username, str(self.id))
        self.registration_keyboard = InlineKeyboardMarkup.from_button(InlineKeyboardButton(text='Register', 
                                                                                           url=url))
    
    def assign_roles(self):

        if len(self.players) >= config.MIN_PLAYERS_FOR_3_MAFIOSO:
            mafiosi_id, detective_id = roles_indices(self.players.keys(), 3, 1)
        elif len(self.players) >= config.MIN_PLAYERS_FOR_2_MAFIOSO:
            mafiosi_id, detective_id = roles_indices(self.players.keys(), 2, 1)
        else:
            mafiosi_id, detective_id = roles_indices(self.players.keys(), 1, 1)

        self.players[detective_id].role = PlayerRole.DETECTIVE
        self.detective = self.players[detective_id]

        if isinstance(mafiosi_id, int):
            mafiosi_id = [mafiosi_id]

        for id in mafiosi_id:
            self.players[id].role = PlayerRole.MAFIOSO
            self.mafioso[id] = self.players[id]

    def __eq__(self, other):
        if isinstance(other, int):
            return other == self.id

        if isinstance(other, Chat):
            return other.id == self.id
            
        return False
    
    def get_alive_players_description(self):
        description = ''
        for i, player in enumerate(self.players.values()):
            description += f'{i+1}\. {player.markdown_link}\n'

        return description

    def build_mafiosi_keyboard(self):
        victims = [player for player in self.players.values() if player not in self.mafioso]
        keyboard = [[InlineKeyboardButton(vi.name, 
                     callback_data=f'{self.id}_maf_{self.nights_passed}_{vi.id}')] for vi in victims]
        return InlineKeyboardMarkup(keyboard)
    
    def build_detective_action_keyboard(self):
        keyboard = [[InlineKeyboardButton('Kill', callback_data=f'{self.id}_detkill_{self.nights_passed}_'),
                     InlineKeyboardButton('Check', callback_data=f'{self.id}_detcheck_{self.nights_passed}_')]]
        return InlineKeyboardMarkup(keyboard)

    def build_detective_player_keyboard(self, action):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=f'{self.id}_{action}_{self.nights_passed}_{p.id}')]\
                     for p in self.players.values() if p.id != self.detective]
        return InlineKeyboardMarkup(keyboard)
    
    def build_general_keyboard(self, id):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=f'{self.id}_dayvote_{self.nights_passed}_{p.id}')] for p in self.players.values() if p.id != id]
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=f'{self.id}_dayvote_{self.nights_passed}_0')])
        return InlineKeyboardMarkup(keyboard)
    
    # called after night mafia vote
    # returns reference to player with more than 50% votes
    # None if there is no such player
    def get_mafia_victim(self):
        votes = list(map(lambda m: m.chosen_player_id, self.mafioso.values()))
        votes = get_occurences(votes)
        if len(votes) == 0:
            return None

        victim_id = max(votes, key=votes.get)

        if votes[victim_id] >= len(self.mafioso)//2 + 1:
            return self.players[victim_id]
        return None
    
    def get_detective_victim(self):
        if self.detective is not None and self.detective.chosen_player_id is not None:
            return self.players[self.detective.chosen_player_id]
        return None
    
    def get_night_victims(self):
        mafia_victim = self.get_mafia_victim()
        detective_victim = self.get_detective_victim()

        victims = []
        if mafia_victim:
            victims.append(mafia_victim)
        if detective_victim and detective_victim != mafia_victim:
            victims.append(detective_victim)
        
        return victims
        
    
    # called after daily vote
    # same rules as with mafia voting
    def get_innocents_victim(self):
        votes = list(map(lambda p: p.chosen_player_id, self.players.values()))
        votes = get_occurences(votes)
        if len(votes) == 0:
            return None

        victim_id = max(votes, key=votes.get)

        if votes[victim_id] >= len(self.players)//2 + 1:
            return self.players[victim_id]
        return None
    
    def handle_victims(self, victims):
        for victim in victims:
            self.killed_players.append(self.players.pop(victim))
            if victim in self.mafioso:
                self.mafioso.pop(victim)
            elif victim == self.detective:
                self.detective = None
    
    def check_game_ended(self, when):
        if len(self.mafioso) == 0:
            return GameStatus.INNOCENTS_WON
        
        if len(self.players) == 2 and len(self.mafioso) == 1 and self.detective:
            return GameStatus.DRAW

        if 2*len(self.mafioso) >= len(self.players) + 1:
            return GameStatus.MAFIA_WON

        if when == 'after_day' and self.detective is None:
            if 2*len(self.mafioso) >= len(self.players) - 1:
                return GameStatus.MAFIA_WON
            else:
                return None

        if when == 'after_night' and self.detective is None:
            if 2*len(self.mafioso) >= len(self.players):
                return GameStatus.MAFIA_WON
            else:
                return None

        return None

# returns dict which stores unique items from iterable as keys
# and number of occurence of those items in iterable as values 
def get_occurences(iterable):
    occurences = {}
    for item in iterable:
        if item is None:
            continue
        if item in occurences:
            occurences[item] += 1
        else:
            occurences[item] = 1
    return occurences

# samples players indices for roles assigning
def roles_indices(arr, *args):
    indices = random.sample(arr, k=sum(args))
    if len(args) == 1:
        return indices
    res = []
    start = 0
    for i in args:
        if i == 1:
            res.append(indices[start])
        else:
            res.append(indices[start:start + i])
        start += i
    return res