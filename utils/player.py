from telegram import helpers
from utils.enums import PlayerRole

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

    def __eq__(self, other):
        if isinstance(other, int):
            return other == self.id

        if isinstance(other, Player):
            return other.id == self.id
            
        return False
    
    def __hash__(self):
        return self.id
    