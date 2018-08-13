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

class StockRoundMinigameSellTests(unittest.TestCase):
    pass


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

    def testPlayerValidBuySellRound(self):

        move = self.move()
        state = self.state()

        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[0], StockPurchaseSource.IPO, STOCK_CERTIFICATE)
        state.public_companies[0].buy(state.players[1], StockPurchaseSource.IPO, STOCK_PRESIDENT_CERTIFICATE)


        state.public_companies[0].setInitialPrice(72)
        state.public_companies[1].buy(state.players[0], StockPurchaseSource.IPO, STOCK_CERTIFICATE)
        state.public_companies[1].buy(state.players[0], StockPurchaseSource.IPO, STOCK_PRESIDENT_CERTIFICATE)

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


if __name__ == "__main__":
    unittest.main()

