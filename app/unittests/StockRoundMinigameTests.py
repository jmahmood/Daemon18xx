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
    -> President should be transfered over.

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

from app.base import Move, PublicCompany, MutableGameState
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


class StockRoundMinigameInitTests(unittest.TestCase):
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




if __name__ == "__main__":
    unittest.main()

