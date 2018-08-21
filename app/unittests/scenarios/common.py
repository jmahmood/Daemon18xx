import unittest

from app.base import Move
from app.state import Game


class TestBase(unittest.TestCase):
    def setUp(self):
        self.player_details = [
            "Jawaad",
            "Alex",
            "Baba",
            "Sho",
            "Yuki",
            "Rafael"
        ]

        game = Game.start(self.player_details)
        game.setPlayerOrder()
        game.setCurrentPlayer()
        self.game = game

    def execute_invalid_player(self, move: Move):
        self.assertTrue(
            self.game.isValidMove(move)
        )

        self.assertFalse(
            self.game.isValidPlayer(move), self.game.errors()
        )

    def execute_invalid_move(self, move: Move):
        self.assertTrue(
            self.game.isValidMove(move),
            self.game.errors()
        )

        self.assertTrue(
            self.game.isValidPlayer(move), self.game.errors()
        )

        self.assertFalse(
            self.game.performedMove(move),
            "This move should have failed but it actually succeeded"
        )

    def execute_valid_move(self, move: Move):
        self.assertTrue(
            self.game.isValidMove(move),
            self.game.errors()
        )

        self.assertTrue(
            self.game.isValidPlayer(move),
            [self.game.errors(), self.game.current_player, [str(p) for p in self.game.state.players]]
        )

        self.assertTrue(
            self.game.performedMove(move),
            self.game.errors()
        )
