from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random

class GameStatus(Enum):
    REGISTRATION = 0
    RUNNING = 1
    MAFIA_WON = 2
    INNOCENTS_WON = 3


class PlayerRole(str, Enum):
    INNOCENT = 'innocent'
    DETECTIVE = 'detective'
    MAFIOSO = 'mafioso'


class Player:
    def __init__(self, id, name):
        self.id = id # telegram user id
        self.name = name # telegram nick
        self.role = PlayerRole.INNOCENT # players with special roles will get this field updated at roles assigning
        self.voted = False # True if player voted in running vote, False otherwise
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
    
    def reset_vote_data(self):
        self.voted = False
        self.vote_message_id = None


class Chat:
    def __init__(self, id):
        self.id = id # telegram chat id
        self.game_status = GameStatus.REGISTRATION
        self.players = {}
        self.mafioso = {}
        self.detective = None
        self.killed_players = []
        self.max_voters = 0
        self.voted = 0
        self.nights_passed = 0
    
    def assign_roles(self):
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
    
    def build_mafiosi_keyboard(self):
        victims = [player for player in self.players.values() if player not in self.mafioso]
        keyboard = [[InlineKeyboardButton(vi.name, 
                     callback_data=str(self.id) + '_maf_' + str(vi.id))] for vi in victims]
        # keyboard.append([InlineKeyboardButton('Skip vote', 
        #                                        callback_data=str(self.id) + '_maf_' + '0')])
        return InlineKeyboardMarkup(keyboard)
    
    def build_detective_action_keyboard(self):
        keyboard = [[InlineKeyboardButton('Kill', callback_data=str(self.id) + '_detkill_'),
                     InlineKeyboardButton('Check', callback_data=str(self.id) + '_detcheck_')]]
        return InlineKeyboardMarkup(keyboard)

    def build_detective_player_keyboard(self, action):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=str(self.id) + '_' + action + '_' + str(p.id))]\
                     for p in self.players.values() if p.id != self.detective]
        return InlineKeyboardMarkup(keyboard)
    
    def build_general_keyboard(self, id):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=str(self.id) + '_dayvote_' + str(p.id))] for p in self.players.values() if p.id != id]
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=str(self.id) + '_dayvote_' + '0')])
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
    
    def game_ended(self):
        if len(self.mafioso) == 0:
            return GameStatus.INNOCENTS_WON
        if len(self.mafioso) >= round(len(self.players)/2 + 0.01):
            return GameStatus.MAFIA_WON
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