from utils import PlayerRole

# players
MAX_PLAYERS = 4
MIN_PLAYERS = 4


# delays(in seconds)
registration_duration = 60
voting_duration = 60
conversation_duration = 5

# bot messages
greetings = {PlayerRole.MAFIOSO : 'Hi, you are mafioso',
             PlayerRole.INNOCENT: 'Hi, you are innocent'}

help_message = 'Hi there, I am MuffiaBot\n'\
                'I understand theese commands:\n'\
                '• /help \- display this help message\n'\
                '• /start \- start maffia game\n'\
                '• /reg \- register for game\n'\
                '• /stop \- stop game'\


# starting the game
game_start_message = 'Starting new game\!\n'\
                     'In order to join please press /reg'\

game_in_progress_message = 'Game is already in progress'
game_private_message = "You can't play alone, can you?"

# stopping the game
game_idle_message = 'Game is not running, nothing to stop'
game_stopped_message = 'Stopped the game'
not_enough_players_message = 'Not enough players, game will not start'

# registration
successfull_register_message = 'You have successfully registered!'
early_register_message = 'Unable to register, start game first'
late_register_message = 'Too late, wait for current game to stop'
double_register_message = 'You are already registered'

