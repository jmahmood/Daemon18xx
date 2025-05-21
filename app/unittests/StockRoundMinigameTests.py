"""

4. Test for non-president buying additional stock (reaching 30%)
    -> President should be transferred over.
"""
import json
import unittest

from app.base import Move, PublicCompany, MutableGameState, StockPurchaseSource, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRound.move import StockRoundMove
from app.unittests.PrivateCompanyMinigameTests import fake_player


def fake_public_company(name="1") -> PublicCompany:
    pc = PublicCompany.initiate(
        name="Fake company {}".format(name),
        short_name="FC{}".format(name),
        id=name,
        cash=0,
        tokens_available=4,
        token_costs=[40, 60, 80, 100]
    )
    return pc


class StockRoundMinigameBuyTests(unittest.TestCase):
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "player_id": "A",
            "public_company_id": "ABC",
            "source": "IPO",
            "move_type": "BUY",
            "ipo_price": 90
        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 1
        game_context.sales = [{},{}]
        game_context.purchases = [{},{}]
        return game_context

    def testPlayerPurchasesInitialStockInvalidPrice(self):
        move = self.move()
        state = self.state()

        move.ipo_price = 3  # Invalid Price

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn('Invalid IPO Price (3).  Valid prices are 100,90,82,76,71,67.', minigame.errors())


    def testPlayerPurchasesInitialStockNoCash(self):
        move = self.move()
        state = self.state()
        state.players[0].cash = 1

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn('You cannot afford poorboi. 90.0 (You have: 1)', minigame.errors())

    def testPlayerPurchasesInitialStock(self):
        move = self.move()
        state = self.state()

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.players[0].cash, 500 - 90 * 2)
        self.assertIn(
            move.player, move.public_company.owners.keys()
        )

        self.assertEqual(
            move.public_company.owners[move.player], 20
        )

        self.assertEqual(move.public_company.president, move.player)

        self.assertFalse(
            move.public_company.isFloated()
        )

        try:
            self.assertIn(
                state.public_companies[0],
                state.purchases[state.stock_round_count][state.players[0]],
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")

    def testPlayerPurchasesNonInitialStock(self):
        move = self.move()
        state = self.state()
        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[1], StockPurchaseSource.IPO, 50)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.players[0].cash, 500 - 72 * 1)
        self.assertIn(
            move.player, move.public_company.owners.keys()
        )
        self.assertEqual(
            move.public_company.owners[move.player], 10
        )

        self.assertTrue(
            move.public_company.isFloated()
        )

        self.assertEqual(move.public_company.president, state.players[1])
        self.assertEqual(move.public_company.cash, 72 * 10)

        try:
            self.assertIn(
                state.public_companies[0],
                state.purchases[state.stock_round_count][state.players[0]],
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")


class StockRoundMinigameSellTests(unittest.TestCase):
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "SELL",
            "player_id": "A",
            "for_sale_raw": [["ABC", 10], ["DEF", 10]]

        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerInvalidSellRound(self):
        # You've already bought this company this round.

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        state.purchases[state.stock_round_count][state.players[0]] = [state.public_companies[0]]

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], STOCK_CERTIFICATE,
                         "The amount of stock in state should not have changed.")

    def testPlayerValidSellRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())

        self.assertEqual(
            state.public_companies[0].owners[move.player], 0
        )

        self.assertEqual(
            state.public_companies[0].president, state.players[1]
        )

        self.assertEqual(
            state.public_companies[1].president, state.players[0]
        )

        try:
            self.assertIn(
                state.public_companies[0],
                state.sales[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

        try:
            self.assertIn(
                state.public_companies[1],
                state.sales[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")




class StockRoundMinigameBuySellTests(unittest.TestCase):
    """Realistically, this is the most important one."""
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "BUYSELL",
            "player_id": "A",
            "public_company_id": "GHI",
            "source": "IPO",
            "ipo_price": 76,
            "for_sale_raw": [["ABC", 10], ["DEF", 10]]

        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerInvalidBuyWeirdQuantityRound(self):
        """You can't buy what doesn't exist"""
        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], 20),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)
        move.for_sale_raw[0][1] = 15
        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn("You can only sell in units of 10 stocks (15)", minigame.errors())

    def testPlayerInvalidBuyNoStockLeftRound(self):
        """You can't buy what doesn't exist"""
        move = self.move()
        state = self.state()
        self.initial_setup_company(
            state.public_companies[2], [(state.players[1], 100)], 72
        )
        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn("The company does not have enough stock in category StockPurchaseSource.IPO", minigame.errors())

    def testPlayerInvalidBuySellRound(self):
        # You've already bought this company this round.

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        state.purchases[state.stock_round_count][state.players[0]] = [state.public_companies[0]]

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], STOCK_CERTIFICATE,
                         "The amount of stock in state should not have changed.")
        self.assertEqual(len(state.public_companies[2].owners.keys()), 0,
                         "The buy order should not be executed either.")

    def testPlayerValidBuySellRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())

        self.assertEqual(
            state.public_companies[0].owners[move.player], 0
        )

        self.assertEqual(
            state.public_companies[0].president, state.players[1]
        )

        self.assertEqual(
            state.public_companies[1].president, state.players[0]
        )

        self.assertEqual(
            state.public_companies[2].president, state.players[0]
        )

        self.assertEqual(
            state.public_companies[2].stockPrice[StockPurchaseSource.IPO], move.ipo_price
        )

        try:
            self.assertIn(
                state.public_companies[0],
                state.sales[state.stock_round_count][state.players[0]],
                "You need to have {} in {}".format(state.public_companies[0],
                                                   [str(company) for company in
                                                   state.sales[state.stock_round_count][state.players[0]]])
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

        try:
            self.assertIn(
                state.public_companies[1],
                state.sales[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

        try:
            self.assertIn(
                state.public_companies[2],
                state.purchases[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")


class StockRoundMinigamePassTests(unittest.TestCase):
    """Realistically, this is the most important one."""
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "PASS",
            "player_id": "A",
        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.stock_round_play = 0
        game_context.stock_round_passed = 0
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerValidPassRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.stock_round_passed, self.state().stock_round_passed + 1)


if __name__ == "__main__":
    unittest.main()

