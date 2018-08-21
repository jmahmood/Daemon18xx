import unittest

from app.base import StockPurchaseSource
from app.state import Game
from app.unittests.scenarios.SimulateBuyPrivateCompaniesTests import skip_private_companies_round
from app.unittests.scenarios.common import TestBase
from app.unittests.scenarios.move_factory import StockRoundMoves


class SimulateFirstStockRoundTest(TestBase):
    """The first stock round doesn't let players sell their stock"""

    def setUp(self):
        super().setUp()
        skip_private_companies_round(self.game)

    def skip_round(self):
        player = self.game.current_player
        player_cash_before_move = player.cash
        skip_moves = StockRoundMoves.pass_round(self.game.current_player.name, self.game.state)
        self.execute_valid_move(skip_moves)
        self.assertEqual(player_cash_before_move, player.cash)  # Since there are skipping, their cash stays the same.
        self.assertEqual(len(self.game.errors()), 0)

    def testPublicCompaniesAdded(self):
        self.assertEqual(len(self.game.state.public_companies), 8)
        for pc in self.game.state.public_companies:
            self.assertIsNotNone(pc.id)

    def testMain(self):
        self.assertEqual(self.game.minigame_class, 'StockRound')
        self.assertEqual(self.game.current_player, self.game.getState().players[0])
        jawaad_cash = self.game.getState().players[0].cash
        move = StockRoundMoves.ipo_buy_sell(
            "Jawaad",
            "B&M",
            [],
            76,
            self.game.getState()
        )
        self.execute_valid_move(move)
        self.assertEqual(jawaad_cash - 2 * 76, self.game.getState().players[0].cash)
        self.assertEqual(len(self.game.errors()), 0)

        # Same player isn't allowed to go twice in a row.
        self.execute_invalid_player(move)

        for player_name in self.player_details[1:]:
            """Skipped 5 times"""
            player = self.game.current_player
            player_cash_before_move = player.cash
            self.assertEqual(self.game.current_player.name, player_name)
            skip_moves = StockRoundMoves.pass_round(player_name, self.game.state)
            self.execute_valid_move(skip_moves)
            self.assertEqual(player_cash_before_move, player.cash) # Since there are skipping, their cash stays the same.
            self.assertEqual(len(self.game.errors()), 0)

        self.assertEqual(self.game.current_player, self.game.getState().players[0])

        wrong_move = StockRoundMoves.ipo_buy_sell(
            "Jawaad",
            "C&O",
            [("B&M", 10)],
            71,
            self.game.getState()
        )
        self.execute_invalid_move(wrong_move)
        # Both purchase and sale need to be aborted, cash does not change.
        self.assertEqual(jawaad_cash - 2 * 76, self.game.getState().players[0].cash)

        move = StockRoundMoves.ipo_buy_sell(
            "Jawaad",
            "C&O",
            [],
            71,
            self.game.getState()
        )
        self.execute_valid_move(move)
        # Both purchase and sale need to be aborted, cash does not change.
        self.assertEqual(jawaad_cash - 2 * 76 - 2 * 71, self.game.getState().players[0].cash)
        self.assertEqual(len(self.game.errors()), 0)

        for _ in range(6):
            """Skipped 6 times"""
            self.skip_round()

        self.assertEqual(self.game.state.stock_round_count, 1, "When all the players pass in a row, the round is over."
                                                               "In this case, there is a new stock round that starts,"
                                                               "but the stock_round_count needs to be incremented")

        self.assertEqual(self.game.state.stock_round_passed_in_a_row, 0, "Reset stats at end of round.")
        self.assertEqual(self.game.current_player, self.game.getState().players[1])

        move = StockRoundMoves.buy_sell(
            "Alex",
            "C&O",
            [],
            self.game.getState()
        )
        self.execute_valid_move(move)

        pc = next(
            pc for pc in self.game.getState().public_companies
            if pc.short_name == "C&O"
        )
        self.assertIn(self.game.getState().players[1], pc.owners.keys())
        self.assertEqual(pc.owners[self.game.getState().players[1]], 10)

        for _ in range(5):
            """Skipped 5 times"""
            self.skip_round()

        self.execute_valid_move(move)
        self.assertIn(self.game.getState().players[1], pc.owners.keys())
        self.assertEqual(pc.owners[self.game.getState().players[1]], 20)

        for _ in range(5):
            """Skipped 5 times"""
            self.skip_round()

        self.execute_valid_move(move)
        self.assertIn(self.game.getState().players[1], pc.owners.keys())
        self.assertEqual(pc.owners[self.game.getState().players[1]], 30)
        self.assertEqual(pc.president, self.game.getState().players[1])

        for _ in range(4):
            """Skipped 4 times"""
            self.skip_round()

        move = StockRoundMoves.buy_sell(
            "Jawaad",
            None,
            [("C&O", 20)],
            self.game.getState()
        )
        self.execute_valid_move(move)
        # Price has to go down.
        self.assertEqual(pc.stockPrice[StockPurchaseSource.BANK], 67,
                         "The price of the stock is not being reduced after a valid sale")


if __name__ == "__main__":
    unittest.main()
