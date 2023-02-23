from utils import PlayerRole

# players
MAX_PLAYERS = 4
MIN_PLAYERS = 4


# delays(in seconds)
registration_duration = 60
voting_duration = 60
conversation_duration = 5

# bot messages
greetings = {PlayerRole.MAFIOSO : 'You are *Mafioso*\.\n'\
                                  'Your main goal is to eliminate innocents\.\n'\
                                  "Good luck and don't let other players guess who you really are\!",
             PlayerRole.INNOCENT: 'You are *Innocent*\.\n'\
                                  "There's not much you can to stop mafia\,\n"\
                                  'but if you cooperate with other innocents your city might stand a chance\.',
             PlayerRole.DETECTIVE: 'You are *Detective*\,\n'\
                                   "the only hope of this city in fight against mafia\.\n"\
                                   'Good luck\!'}

help_message = 'Hi there, I am *MuffiaBot*\n'\
                'I understand theese commands:\n'\
                '• /help \- display this help message\n'\
                '• /start \- start game\n'\
                '• /stop \- stop game'\


# starting the game
game_start_message = 'Starting new game\!'

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

