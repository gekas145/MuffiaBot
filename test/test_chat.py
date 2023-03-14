from utils.chat import Chat
from utils.player import Player
from unittest import TestCase



class ChatTestStaticMethods(TestCase):

    def test_get_occurences(self):
        arrs = [[1, 1, 5, None, 1, None, 2, 1],
                [1, 2, 3, None, 5, 1],
                range(1, 4),
                [],
                [None, None],
                [1, 1, 1, 1, 1]]
        
        dicts = [{1: 4, 5: 1, 2: 1},
                 {1: 2, 2: 1, 3: 1, 5: 1},
                 {1: 1, 2: 1, 3: 1},
                 {},
                 {},
                 {1: 5}]
        
        for arr, dc in zip(arrs, dicts):
            self.assertEqual(Chat.get_occurences(arr), dc)

    
    def test_roles_indices(self):

        def check(indices, i):
            if len(args[i]) == 1:
                indices = [indices]
            
            for j in range(len(indices)):
                self.assertIsInstance(indices[j], expected_types[i][j])
                if isinstance(indices[j], list):
                    self.assertEqual(len(indices[j]), args[i][j])


        arrs = [[0, 1, 2, 3, 4],
                range(5),
                set(range(10)),
                range(7),
                (1, 2, 3),
                [1, 2, 3],
                range(10),
                range(10)
                ]

        args = [[1, 1], 
                [1, 1],
                [1, 3, 1],
                [1, 1, 3],
                [1],
                [3],
                [2, 1, 2],
                [2, 4]]
        
        expected_types = [[int, int],
                          [int, int],
                          [int, list, int],
                          [int, int, list],
                          [int],
                          [list],
                          [list, int, list],
                          [list, list]]
        
        for i in range(len(arrs)):
            check(Chat.roles_indices(arrs[i], *args[i]), i)
            


class ChatTestPlayersDescription(TestCase):
    
    @classmethod
    def setUp(cls):
        cls._chat = Chat(123, 'botname')

    def test_villains_names(self):
        ChatTestPlayersDescription._chat.mafioso[1] = Player(1, 'John', None)
        self.assertEqual('\nMafioso: John', 
                         ChatTestPlayersDescription._chat.villains_names())

        ChatTestPlayersDescription._chat.mafioso[2] = Player(2, 'John', 'Doe')
        self.assertEqual('\nMafioso: John, John Doe', 
                         ChatTestPlayersDescription._chat.villains_names())
        

    def test_innocents_leaders_names(self):
        detective = Player(1, 'John', 'Doe')
        doctor = Player(2, 'John', None)

        ChatTestPlayersDescription._chat.detective = detective
        self.assertCountEqual('\nDetective: John Doe', 
                              ChatTestPlayersDescription._chat.innocents_leaders_names())

        ChatTestPlayersDescription._chat.detective = None
        ChatTestPlayersDescription._chat.doctor = doctor
        self.assertCountEqual('\nDoctor: John', 
                              ChatTestPlayersDescription._chat.innocents_leaders_names())

        ChatTestPlayersDescription._chat.detective = detective
        self.assertCountEqual('\nDetective: John Doe\nDoctor: John', 
                              ChatTestPlayersDescription._chat.innocents_leaders_names())
        
    
    def test_alive_players_links(self):
        ChatTestPlayersDescription._chat.players[1] = Player(1, 'John', 'Doe')
        ChatTestPlayersDescription._chat.players[2] = Player(2, 'John', None)
        ChatTestPlayersDescription._chat.players[3] = Player(3, 'John', 'John')

        self.assertEqual('\n1\. [John Doe](tg://user?id=1)'\
                         '\n2\. [John](tg://user?id=2)'\
                         '\n3\. [John John](tg://user?id=3)',
                         ChatTestPlayersDescription._chat.alive_players_links())

