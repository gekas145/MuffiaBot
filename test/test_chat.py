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
            
