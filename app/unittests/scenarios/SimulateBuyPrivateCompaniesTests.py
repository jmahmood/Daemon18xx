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
            game.isValidPlayer(move),
            [game.errors(), game.current_player, [str(p) for p in game.state.players]]
        )

        self.assertTrue(
            game.performedMove(move),
            game.errors()
        )

    def testStartGame(self):
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

        self.assertEqual(game.state.players[0].cash, 2400 / 6 - 45)

        self.assertEqual(state.players[1], game.current_player,
                         "Current player should be {} but it is actually {}".format(
                             state.players[1].name, game.current_player.name
                         ))

        self.assertEqual(game.current_player, state.players[1])

        move2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)

        self.execute_valid_move(game, move2)

        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

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
        self.assertEqual(game.minigame_class, "BiddingForPrivateCompany")

        move4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 55, state)
        self.execute_valid_move(game, move4)
        self.assertEqual(game.state.players[0].cash, 2400 / 6 - 100)

        move5 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)
        self.execute_invalid_move(game, move5)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_v2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 55, state)
        self.execute_invalid_move(game, move5_v2)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_v3 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 56, state)
        self.execute_invalid_move(game, move5_v3)

        move5_v4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 60, state)
        self.execute_invalid_player(game, move5_v4)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_corrected = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 60, state)
        self.execute_valid_move(game, move5_corrected)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 110)

        move_6 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Jawaad", "C&StL", state)
        self.execute_valid_move(game, move_6)

        self.assertEqual(game.minigame_class, "BuyPrivateCompany")
        self.assertEqual(game.state.private_companies[1].belongs_to,
                         game.state.players[1],
                         game.state.private_companies[1])
        self.assertEqual(game.state.players[0].cash, 2400 / 6, "You need to return the money")
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 60)

        # move_7 = PrivateCompanyInitialAuctionMoves.bid("Sho", "M&H", 115, state)
        # self.execute_valid_move(game, move_7)

        # self.assertEqual(game.current_player, state.players[1], game.current_player)



if __name__ == "__main__":
    unittest.main()
