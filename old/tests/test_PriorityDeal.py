import json
import unittest

from app.base import Move, MutableGameState
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.StockRound.minigame_stockround import StockRound
from app.state import Game
from app.unittests.test_PrivateCompanyMinigame import fake_player
from app.unittests.test_StockRoundMinigame import fake_public_company

class PriorityDealTests(unittest.TestCase):
    def setup_state(self):
        state = MutableGameState()
        state.players = [fake_player("A"), fake_player("B")]
        state.public_companies = [fake_public_company("ABC")]
        state.stock_round_count = 1
        state.stock_round_play = 0
        state.stock_round_passed = 0
        state.sales = [{}, {}]
        state.purchases = [{}, {}]
        state.priority_deal_player = state.players[0]
        return state

    def test_priority_deal_changes_after_purchase(self):
        state = self.setup_state()
        # Player A buys one share
        msg = json.dumps({
            "player_id": "A",
            "public_company_id": "ABC",
            "source": "IPO",
            "move_type": "BUY",
            "ipo_price": 90
        })
        buy_move = StockRoundMove.fromMove(Move.fromMessage(msg))
        sr = StockRound()
        self.assertTrue(sr.run(buy_move, state))

        # Player B passes
        msg = json.dumps({"player_id": "B", "move_type": "PASS"})
        pass_move_b = StockRoundMove.fromMove(Move.fromMessage(msg))
        self.assertTrue(sr.run(pass_move_b, state))

        # Player A passes -> round ends
        msg = json.dumps({"player_id": "A", "move_type": "PASS"})
        pass_move_a = StockRoundMove.fromMove(Move.fromMessage(msg))
        self.assertTrue(sr.run(pass_move_a, state))
        # force end-of-round conditions
        state.stock_round_play = len(state.players)
        state.stock_round_passed = len(state.players)
        self.assertEqual(sr.next(state), "OperatingRound1")
        self.assertEqual(state.priority_deal_player, state.players[1])

    def test_set_player_order_uses_priority_deal(self):
        state = self.setup_state()
        state.priority_deal_player = state.players[1]
        game = Game()
        game.state = state
        game.minigame_class = "StockRound"
        game.setPlayerOrder()
        game.setCurrentPlayer()
        self.assertEqual(game.current_player, state.players[1])

if __name__ == "__main__":
    unittest.main()
