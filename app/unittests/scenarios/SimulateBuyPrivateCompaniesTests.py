"""
Do a full simulation of Private Company rounds and make sure that everything runs according to plan.
"""
import unittest

import logging

from app.base import MutableGameState, Move
from app.state import Game
from app.unittests.scenarios.move_factory import PrivateCompanyInitialAuctionMoves


class InitialGameTests(unittest.TestCase):

    def execute_invalid_player(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertFalse(
            game.isValidPlayer(move), game.errors()
        )

    def execute_invalid_move(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertTrue(
            game.isValidPlayer(move), game.errors()
        )

        self.assertFalse(
            game.performedMove(move),
            game.errors()
        )

    def execute_valid_move(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertTrue(
            game.isValidPlayer(move), game.errors()
        )

        self.assertTrue(
            game.performedMove(move),
            game.errors()
        )

    def testStartGame(self):
        initial_state = MutableGameState()
        player_details = [
            "Jawaad",
            "Alex",
            "Baba",
            "Sho",
            "Yuki",
            "Rafael"
        ]

        game = Game.start(player_details)
        game.setPlayerOrder()
        game.setCurrentPlayer()

        state = game.getState()

        self.assertEqual(game.current_player, state.players[0])

        move1 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 45, state)
        self.execute_valid_move(game, move1)


        # game.setPlayerOrder()

        self.assertEqual(state.players[1], game.current_player,
                         "Current player should be {} but it is actually {}".format(
                             state.players[1].name, game.current_player.name
                         ))

        self.assertEqual(game.current_player, state.players[1])

        move2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)

        self.execute_valid_move(game, move2)

        self.assertEqual(game.current_player, state.players[2])

        move3wrong = PrivateCompanyInitialAuctionMoves.buy("Sho", "SVR", state)

        self.assertTrue(
            game.isValidMove(move3wrong)
        )

        self.assertFalse(
            game.isValidPlayer(move3wrong), game.errors()
        )

        move3 = PrivateCompanyInitialAuctionMoves.buy("Baba", "SVR", state)
        self.execute_valid_move(game, move3)

        # TODO Now we are in a bidding phase.  Jawaad / Alex exchange bidding until one passes
        self.assertEqual(game.current_player, state.players[0], game.current_player)

        move4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 55, state)
        self.execute_valid_move(game, move4)

        move5 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)
        self.execute_invalid_move(game, move5)

        move5_v2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 55, state)
        self.execute_invalid_move(game, move5_v2)

        move5_v3 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 56, state)
        self.execute_invalid_move(game, move5_v3)

        move5_v4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 60, state)
        self.execute_invalid_player(game, move5_v4)

        move5_corrected = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 60, state)
        self.execute_valid_move(game, move5_corrected)

        # self.assertEqual(game.current_player, state.players[1], game.current_player)



if __name__ == "__main__":
    unittest.main()
