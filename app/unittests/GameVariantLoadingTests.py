import unittest

from app.state import Game
from app.config import load_config


class GameVariantLoadingTests(unittest.TestCase):
    def test_1830_config(self):
        cfg = load_config("1830")
        game = Game.start(["A", "B", "C", "D"], variant="1830")
        self.assertEqual(game.state.players[0].cash, cfg.starting_cash(4))
        self.assertEqual([pc.name for pc in game.state.private_companies],
                         [pc.name for pc in cfg.PRIVATE_COMPANIES])
        self.assertEqual([pc.name for pc in game.state.public_companies],
                         [pc.name for pc in cfg.PUBLIC_COMPANIES])

    def test_1846_config(self):
        cfg = load_config("1846")
        game = Game.start(["A", "B", "C"], variant="1846")
        self.assertEqual(game.state.players[0].cash, cfg.starting_cash(3))
        self.assertEqual([pc.name for pc in game.state.private_companies],
                         [pc.name for pc in cfg.PRIVATE_COMPANIES])
        self.assertEqual([pc.name for pc in game.state.public_companies],
                         [pc.name for pc in cfg.PUBLIC_COMPANIES])

    def test_1889_config(self):
        cfg = load_config("1889")
        game = Game.start(["A", "B", "C", "D", "E"], variant="1889")
        self.assertEqual(game.state.players[0].cash, cfg.starting_cash(5))
        self.assertEqual([pc.name for pc in game.state.private_companies],
                         [pc.name for pc in cfg.PRIVATE_COMPANIES])
        self.assertEqual([pc.name for pc in game.state.public_companies],
                         [pc.name for pc in cfg.PUBLIC_COMPANIES])


if __name__ == '__main__':
    unittest.main()
