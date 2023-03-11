from enum import Enum

class GameStatus(Enum):
    REGISTRATION = 0
    RUNNING = 1
    DAY = 2
    NIGHT = 3
    MAFIA_WON = 4
    INNOCENTS_WON = 5
    DRAW = 6

class PlayerRole(str, Enum):
    INNOCENT = 'Innocent'
    DETECTIVE = 'Detective'
    MAFIOSO = 'Mafioso'
    DOCTOR = 'Doctor'