import config
import random
from datetime import datetime
from utils.enums import GameStatus, PlayerRole
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, helpers

class Chat:
    def __init__(self, id, bot_username):
        self.id = id # telegram chat id
        self.game_id = int(datetime.now().strftime("%Y%m%d%H%M%S"))
        self.game_status = GameStatus.REGISTRATION
        self.registration_message_id = None
        self.players = {}
        self.mafioso = {}
        self.detective = None
        self.doctor = None
        self.query_header = f'{self.id}_{self.game_id}'
        self.killed_players = []
        self.max_voters = 0
        self.voted = 0
        self.nights_passed = 0
        url = helpers.create_deep_linked_url(bot_username, str(self.id))
        self.registration_keyboard = InlineKeyboardMarkup.from_button(InlineKeyboardButton(text='Register', 
                                                                                           url=url))
    
    def assign_roles(self):

        if len(self.players) >= config.MIN_PLAYERS_FOR_3_MAFIOSO:
            mafiosi_num = 3
        elif len(self.players) >= config.MIN_PLAYERS_FOR_2_MAFIOSO:
            mafiosi_num = 2
        else:
            mafiosi_num = 1
        
        mafiosi_id, detective_id, doctor_id = Chat.roles_indices(self.players.keys(), mafiosi_num, 1, 1)

        self.players[detective_id].role = PlayerRole.DETECTIVE
        self.detective = self.players[detective_id]

        self.players[doctor_id].role = PlayerRole.DOCTOR
        self.doctor = self.players[doctor_id]

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
                     callback_data=f'{self.query_header}_maf_{self.nights_passed}_{vi.id}')] for vi in victims]
        return InlineKeyboardMarkup(keyboard)
    
    def build_detective_action_keyboard(self):
        keyboard = [[InlineKeyboardButton('Kill', callback_data=f'{self.query_header}_detkill_{self.nights_passed}_'),
                     InlineKeyboardButton('Check', callback_data=f'{self.query_header}_detcheck_{self.nights_passed}_')]]
        return InlineKeyboardMarkup(keyboard)

    def build_detective_player_keyboard(self, action):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=f'{self.query_header}_{action}_{self.nights_passed}_{p.id}')]\
                     for p in self.players.values() if p.id != self.detective]
        return InlineKeyboardMarkup(keyboard)

    def build_doctor_keyboard(self):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=f'{self.query_header}_doc_{self.nights_passed}_{p.id}')]\
                     for p in self.players.values() if p.id != self.doctor]
        
        keyboard.append([InlineKeyboardButton('Yourself', 
                        callback_data=f'{self.query_header}_doc_{self.nights_passed}_{self.doctor.id}')])
        
        return InlineKeyboardMarkup(keyboard)
    
    
    def build_general_keyboard(self, id):
        keyboard = [[InlineKeyboardButton(p.name, 
                     callback_data=f'{self.query_header}_dayvote_{self.nights_passed}_{p.id}')] for p in self.players.values() if p.id != id]
        
        keyboard.append([InlineKeyboardButton('Skip vote', 
                         callback_data=f'{self.query_header}_dayvote_{self.nights_passed}_0')])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_night_voters(self):
        voters = list(self.mafioso.values())

        if self.detective:
            voters.append(self.detective)

        if self.doctor:
            voters.append(self.doctor)
        
        return voters

    def get_villains_names(self):
        villains_names = '\nLeft mafioso:'
        for m in self.mafioso.values():
            villains_names += '\n' + m.name
        return villains_names
    
    def get_innocents_leaders_names(self):
        innocents_leaders_names = ''
        if self.detective:
            innocents_leaders_names += f'\nDetective: {self.detective.name}'
        if self.doctor:
            innocents_leaders_names += f'\nDoctor: {self.doctor.name}'
        return innocents_leaders_names
    
    # called after night mafia vote
    # returns reference to player with more than 50% votes
    # None if there is no such player
    def get_mafia_victim(self):
        votes = list(map(lambda m: m.chosen_player_id, self.mafioso.values()))
        votes = Chat.get_occurences(votes)
        if len(votes) == 0:
            return None

        victim_id = max(votes, key=votes.get)

        if votes[victim_id] >= len(self.mafioso)//2 + 1:
            return self.players[victim_id]
        return None
    
    def get_detective_victim(self):
        if self.detective and self.detective.chosen_player_id:
            return self.players[self.detective.chosen_player_id]
        return None
    
    def get_doctor_choice(self):
        if self.doctor and self.doctor.chosen_player_id:
            return self.players[self.doctor.chosen_player_id]
        return None
    
    def get_night_victims(self):
        mafia_victim = self.get_mafia_victim()
        detective_victim = self.get_detective_victim()
        doctor_choice = self.get_doctor_choice()

        victims = []
        if mafia_victim:
            victims.append(mafia_victim)
        if detective_victim and detective_victim != mafia_victim:
            victims.append(detective_victim)
        
        victims = [victim for victim in victims if victim != doctor_choice]
        
        return victims
        
    
    # called after daily vote
    # same rules as with mafia voting
    def get_innocents_victim(self):
        votes = list(map(lambda p: p.chosen_player_id, self.players.values()))
        votes = Chat.get_occurences(votes)
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
            elif victim == self.doctor:
                self.doctor = None
    
    def check_game_ended(self, when):
        if len(self.mafioso) == 0:
            return GameStatus.INNOCENTS_WON
        
        if len(self.players) == 2 and len(self.mafioso) == 1 and (self.detective or self.doctor):
            return GameStatus.DRAW

        lower_bound = len(self.players)
        if self.detective and self.doctor:
            if when == 'after_day':
                lower_bound += 2
            else:
                lower_bound += 1
        elif self.detective and not self.doctor:
            lower_bound += 1
        elif not self.detective and not self.doctor and when == 'after_day':
            lower_bound -= 1
        
        if 2*len(self.mafioso) >= lower_bound:
            return GameStatus.MAFIA_WON
        return None

# returns dict which stores unique items from iterable as keys
# and number of occurence of those items in iterable as values 
@staticmethod
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
@staticmethod
def roles_indices(arr, *args):
    indices = random.sample(arr, k=sum(args))
    if len(args) == 1:
        return indices[0] if len(indices) == 1 else indices
    res = []
    start = 0
    for i in args:
        if i == 1:
            res.append(indices[start])
        else:
            res.append(indices[start:start + i])
        start += i
    return res