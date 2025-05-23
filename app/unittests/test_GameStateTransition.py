import json
import unittest

from app.base import Move
from app.state import Game, apply_move
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove


class GameStateTransitionTests(unittest.TestCase):
    def test_apply_move_returns_updated_state(self):
        game = Game.start(["Alice", "Bob"], variant="1830")
        game.setPlayerOrder()
        game.setCurrentPlayer()
        state = game.getState()

        msg = json.dumps(
            {
                "private_company_order": state.private_companies[0].order,
                "move_type": "BUY",
                "player_id": state.players[0].id,
                "bid_amount": 0,
            }
        )
        move = Move.fromMessage(msg)
        buy_move = BuyPrivateCompanyMove.fromMove(move)

        updated = apply_move(game, buy_move)

        self.assertIs(updated, game)
        self.assertEqual(state.private_companies[0].belongs_to, state.players[0])


if __name__ == "__main__":
    unittest.main()
