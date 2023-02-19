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
        self.role = None
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
        self.id = id
        self.game_status = GameStatus.REGISTRATION
        self.players = {}
        self.mafioso = {}
        self.detective = None
        self.killed_players = []
        self.max_voters = 0
        self.voted = 0
        self.nights_passed = 0
    
    def assign_roles(self):
        ind = random.randint(0, len(self.players) - 1)
        mafiosi_id = list(self.players.keys())[ind]

        for player in self.players.values():
            if player.id == mafiosi_id:
                player.role = PlayerRole.MAFIOSO
                self.mafioso[player.id] = player
            else:
                player.role = PlayerRole.INNOCENT

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
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=str(self.id) + '_maf_' + '0')])
        return InlineKeyboardMarkup(keyboard)
    
    def build_general_keyboard(self, id):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=str(self.id) + '_dayvote_' + str(p.id))] for p in self.players.values() if p.id != id]
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=str(self.id) + '_dayvote_' + '0')])
        return InlineKeyboardMarkup(keyboard)
    
    def get_mafia_victim(self):
        votes = list(map(lambda m: m.chosen_player_id, self.mafioso.values()))
        votes = get_occurences(votes)
        if len(votes) == 0:
            return None

        victim_id = max(votes, key=votes.get)

        if votes[victim_id] >= len(self.mafioso)//2 + 1:
            return self.players[victim_id]
        return None
    
    def get_innocents_victim(self):
        votes = list(map(lambda p: p.chosen_player_id, self.players.values()))
        votes = get_occurences(votes)
        if len(votes) == 0:
            return None

        victim_id = max(votes, key=votes.get)

        if votes[victim_id] >= len(self.players)//2:
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
        if len(self.players) <= 2:
            return GameStatus.MAFIA_WON
        return None


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
        