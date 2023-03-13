from utils.player import Player
from unittest import TestCase




class TestPlayer(TestCase):

    def test_player_name(self):
        players = [Player(1, 'John', None),
                   Player(1, 'John', 'Doe')]

        expected_names = ['John', 'John Doe']

        for name, player in zip(expected_names, players):
            self.assertEqual(name, player.name)


    def test_markdown_link(self):
        players = [Player(1, 'John', None),
                   Player(2, 'John', 'Doe'),
                   Player(3, 'John!', 'Doe')]
        
        expected_links = ['[John](tg://user?id=1)',
                          '[John Doe](tg://user?id=2)',
                          '[John\! Doe](tg://user?id=3)']
        
        for link, player in zip(expected_links, players):
            self.assertEqual(link, player.markdown_link)

    
    def test_equality(self):
        player1 = Player(123, 'John', None)
        player2 = Player(123, 'John', None)
        player3 = Player(3, 'John', None)

        self.assertEqual(player1, player2)
        self.assertEqual(player1, 123)
        self.assertNotEqual(player1, player3)
        self.assertNotEqual(player1, 111)

