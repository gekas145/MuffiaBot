from enum import Enum

class GameStatus(Enum):
    IDLE = 0
    REGISTRATION = 1
    RUNNING = 2


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
        