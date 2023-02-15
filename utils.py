import json
from enum import Enum

class GameStatus(Enum):
    IDLE = 0
    REGISTRATION = 1
    RUNNING = 2


class PlayerRole(Enum):
    INNOCENT = 0
    MAFIOSO = 1


class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.alive = True
        self.role = None
    
    def __eq__(self, __o):
        if isinstance(__o, int):
            return __o == self.id
        return False
        