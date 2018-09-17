import unittest

from app.base import StockPurchaseSource
from app.game import Game
from app.unittests.scenarios.SimulateBuyPrivateCompaniesTests import skip_private_companies_round
from app.unittests.scenarios.common import TestBase
from app.unittests.scenarios.move_factory import StockRoundMoves, StockRoundPrivateCompanyAuctionMoves, \
    StockRoundPrivateCompanyAuctionDecisionMoves


class SimulateFirstStockRoundTest(TestBase):
    """The first stock round doesn't let players sell their stock"""

    def setUp(self):
        super().setUp()
        skip_private_companies_round(self.game)

    def skip_private_company_bid(self):
        skip_move = StockRoundPrivateCompanyAuctionMoves.pass_on_bid(
            self.game.current_player.name, self.game.getState())
        self.execute_valid_move(skip_move)
        self.assertEqual(len(self.game.errors()), 0)

    def skip_round(self):
        game_round = self.game.getState().stock_round_count
        player = self.game.current_player
        player_cash_before_move = player.cash
        skip_moves = StockRoundMoves.pass_round(self.game.current_player.name, self.game.state)
        self.execute_valid_move(skip_moves)
        game_round_after_move = self.game.getState().stock_round_count
        if game_round == game_round_after_move:
            # If you skip a round and you enter a new Stock round, you will get money from
            # your private companies.  Otherwise, your cash should remain the same
            self.assertEqual(player_cash_before_move, player.cash)
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
        self.assertEqual(self.game.getState().private_companies[0].belongs_to,
                         self.game.getState().players[0])

        self.assertEqual(int(jawaad_cash - 2 * 76  - 2 * 71 + self.game.getState().private_companies[0].revenue),
                         int(self.game.state.players[0].cash))  # TODO: Make sure everyone got money from their private companies.

        move = StockRoundMoves.buy_sell(
            "Alex",
            "C&O",
            [],
            self.game.getState()
        )
        self.execute_valid_move(move)

        c_and_o = next(
            pc for pc in self.game.getState().public_companies
            if pc.short_name == "C&O"
        )
        self.assertIn(self.game.getState().players[1], c_and_o.owners.keys())
        self.assertEqual(c_and_o.owners[self.game.getState().players[1]], 10)

        for _ in range(5):
            """Skipped 5 times"""
            self.skip_round()

        self.execute_valid_move(move)
        self.assertIn(self.game.getState().players[1], c_and_o.owners.keys())
        self.assertEqual(c_and_o.owners[self.game.getState().players[1]], 20)

        for _ in range(5):
            """Skipped 5 times"""
            self.skip_round()

        self.execute_valid_move(move)
        self.assertIn(self.game.getState().players[1], c_and_o.owners.keys())
        self.assertEqual(c_and_o.owners[self.game.getState().players[1]], 30)
        self.assertEqual(c_and_o.president, self.game.getState().players[1])

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
        self.assertEqual(c_and_o.stockPrice[StockPurchaseSource.BANK], 67,
                         "The price of the stock is not being reduced after a valid sale")

        move = StockRoundMoves.sell_private_company(
            "Alex",
            "C&StL",
            self.game.state
        )

        self.execute_valid_move(move)
        self.assertEqual(self.game.minigame_class, "StockRoundSellPrivateCompany")
        self.assertEqual(self.game.current_player, self.game.getState().players[2])
        self.assertEqual(self.game.getPlayerOrderClass().players, self.game.getState().players[2:] + self.game.getState().players[0:1])

        # Let's say no one is interested.

        for _ in range(5):
            self.skip_private_company_bid()

        self.assertEqual(self.game.minigame_class, "StockRoundSellPrivateCompanyDecision")

        # You can't accept a bid when none exists.
        move = StockRoundPrivateCompanyAuctionDecisionMoves.accept(
            "Alex",
            "Jawaad",
            self.game.state
        )

        self.execute_invalid_move(move)

        move = StockRoundPrivateCompanyAuctionDecisionMoves.reject(
            "Alex",
            self.game.state
        )
        self.execute_valid_move(move)

        self.assertEqual(self.game.minigame_class, "StockRound")
        self.assertEqual(self.game.current_player, self.game.getState().players[1],
                         [str(self.game.current_player), str(self.game.getState().players[1])])


        # This time I will bid half the price and he will accept it.
        move = StockRoundMoves.sell_private_company(
            "Alex",
            "C&StL",
            self.game.state
        )

        self.execute_valid_move(move)

        for _ in range(4):
            self.skip_private_company_bid()

        move = StockRoundPrivateCompanyAuctionMoves.bid(
            "Jawaad",
            20,
            self.game.state
        )

        self.execute_valid_move(move)
        self.assertEqual(self.game.minigame_class, "StockRoundSellPrivateCompanyDecision")

        company = self.game.state.auctioned_private_company
        self.assertEqual(company.belongs_to, self.game.state.players[1])

        move = StockRoundPrivateCompanyAuctionDecisionMoves.accept(
            "Alex",
            "Jawaad",
            self.game.state
        )

        self.execute_valid_move(move)
        self.assertEqual(company.belongs_to, self.game.state.players[0])
        self.assertEqual(int(jawaad_cash - 20 - 2 * 76  - 2 * 71 + self.game.getState().private_companies[0].revenue),
                         int(self.game.state.players[0].cash))  # TODO: Make sure everyone got money from their private companies.
        self.assertEqual(self.game.current_player, self.game.getState().players[2],
                         [str(self.game.current_player), str(self.game.getState().players[2])])

        for _ in range(1):

            move = StockRoundMoves.buy_sell(
                "Baba",
                "C&O",
                [],
                self.game.getState()
            )
            self.execute_valid_move(move)

            move = StockRoundMoves.buy_sell(
                "Sho",
                "C&O",
                [],
                self.game.getState()
            )
            self.execute_valid_move(move)

            move = StockRoundMoves.buy_sell(
                "Yuki",
                "C&O",
                [],
                self.game.getState()
            )
            self.execute_valid_move(move)

            move = StockRoundMoves.buy_sell(
                "Rafael",
                "C&O",
                [],
                self.game.getState()
            )
            self.execute_valid_move(move)

        self.assertTrue(c_and_o.isFloated())

        for _ in range(6):
            self.skip_round()  # skip jawaad and alex

if __name__ == "__main__":
    unittest.main()
