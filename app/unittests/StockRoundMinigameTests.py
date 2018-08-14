"""
1. Test for player purchasing the first stock
    -> Stock amount is set based on the amount passed in.
    -> They should be given 20% of the stock (not 10%); President's share.
    -> The IPO stock should be reduced by 20%
    -> Company should not be floated
    -> Company president should be the person
    -> Should be added to the owners dict

2. Test for player buying stock as a follow-up
    -> Stock amount is set based on the amount passed in.
    -> They should be given 10% of the stock
    -> The IPO stock should be reduced by 10%
    -> Company should not be floated
    -> Company president should be the person
    -> Should be added to the owners dict


3. Test for same player buying additional stock (Reaching 20%)
    -> Should not be made the president.

4. Test for non-president buying additional stock (reaching 30%)
    -> President should be transferred over.

5. Test for floating stock
    -> Once the IPO shares hits 40%, the company should be floated
    -> Starting cash should be IPO Price * 10


6. Test for Buy-Sell or Sell-Buy
    -> You can't buy something if you have sold it already and vice-versa

7. Test for Buy and Sell in the same round
    -> You can do a single buy and multiple sells in the same round.
"""
import json
import unittest

from app.base import Move, PublicCompany, MutableGameState, StockPurchaseSource, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.minigames.stock_round import StockRoundMove, StockRound
from app.unittests.PrivateCompanyMinigameTests import fake_player


def fake_public_company(name="1") -> PublicCompany:
    pc = PublicCompany.initiate(
        name="Fake company {}".format(name),
        short_name="FC{}".format(name),
        id=name,
        cash=0
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

    def state(self):
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 1
        game_context.sales = [{},{}]
        game_context.purchases = [{},{}]
        return game_context

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

    def state(self):
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

    def state(self):
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

    def state(self):
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

