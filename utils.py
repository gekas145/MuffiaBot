from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random

class GameStatus(Enum):
    REGISTRATION = 0
    RUNNING = 1


class PlayerRole(str, Enum):
    INNOCENT = 'innocent'
    MAFIOSO = 'mafioso'


class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.alive = True
        self.role = None
        self.voted = False
        self.vote_message_id = None
        self.times_chosen = 0
    
    def __eq__(self, __o):
        if isinstance(__o, int):
            return __o == self.id

        if isinstance(__o, Player):
            return __o.id == self.id
            
        return False
    
    def reset_vote_data(self):
        self.voted = False
        self.vote_message_id = None


class Chat:
    def __init__(self, id):
        self.id = id
        self.game_status = GameStatus.REGISTRATION
        self.players = []
        self.mafioso = []
        self.max_voters = 0
        self.voted = 0
        self.nights_passed = 0
    
    def assign_roles(self):
        mafiosi_ind = random.randint(0, len(self.players) - 1)

        for i in range(len(self.players)):
            if i == mafiosi_ind:
                self.players[i].role = PlayerRole.MAFIOSO
                self.mafioso.append(self.players[i])
            else:
                self.players[i].role = PlayerRole.INNOCENT
    
    def add_player(self, player):
        self.players.append(player)

    def __eq__(self, __o):
        if isinstance(__o, int):
            return __o == self.id

        if isinstance(__o, Chat):
            return __o.id == self.id
            
        return False
    
    def build_mafiosi_keyboard(self):
        victims = [p for p in self.players if p.id not in self.mafioso]
        keyboard = [[InlineKeyboardButton(vi.name, 
                     callback_data=str(self.id) + '_maf_' + str(vi.id))] for vi in victims]
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=str(self.id) + '_maf_' + '0')])
        return InlineKeyboardMarkup(keyboard)
    
    def build_general_keyboard(self, id):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=str(self.id) + '_dayvote_' + str(p.id))] for p in self.players if p.id != id]
        keyboard.append([InlineKeyboardButton('Skip vote', 
                                               callback_data=str(self.id) + '_dayvote_' + '0')])
        return InlineKeyboardMarkup(keyboard)
    
    def get_victim(self):
        candidate = max(self.players, key=lambda p: p.times_chosen)
        
        count = 0
        for p in self.players:
            if candidate.times_chosen == p.times_chosen:
                count += 1
            if count > 1:
                break
        
        if count > 1:
            return None
        return candidate
        