"""
Test Stock Round to Operating Round transition.

This test verifies that when all players pass in the Stock Round,
the game correctly transitions to Operating Round with the operating
order properly set.
"""
import json
import unittest

from app.base import Move, MutableGameState, StockPurchaseSource
from app.config import load_config
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRound.move import StockRoundMove
from app.state import Game
from app.unittests.test_PrivateCompanyMinigame import fake_player
from app.unittests.test_StockRoundCriticalFixes import fake_public_company


class StockRoundToOperatingTransitionTests(unittest.TestCase):
    """Test transition from Stock Round to Operating Round."""

    def test_operating_order_set_when_transitioning_to_operating_round(self):
        """When transitioning to Operating Round, operating_order should be set."""
        # Create a minimal game with a floated company
        players = ["Alice", "Bob", "Charlie"]
        game = Game.start(players, "1889")

        # Force transition to Stock Round by setting minigame
        game.setMinigame("StockRound")
        game.setPlayerOrder()
        game.setCurrentPlayer()

        # Initialize Stock Round state
        StockRound.onStart(game.getState())

        # Get the first public company and float it
        company = game.state.public_companies[0]
        alice = game.state.players[0]
        bob = game.state.players[1]
        charlie = game.state.players[2]

        # Make Alice president and float the company
        company.setInitialPrice(100)
        company.buy(alice, StockPurchaseSource.IPO, 20)  # President cert
        company.buy(bob, StockPurchaseSource.IPO, 10)
        company.buy(charlie, StockPurchaseSource.IPO, 10)
        company.buy(alice, StockPurchaseSource.IPO, 10)
        company.buy(bob, StockPurchaseSource.IPO, 10)  # 60% sold = floated

        # Verify company is floated
        self.assertTrue(company.isFloated(), "Company should be floated")

        # Now all players pass to end the Stock Round
        minigame = StockRound()
        minigame.last_deal_player = alice  # Set someone as last dealer

        for player in game.state.players:
            msg = json.dumps({
                "player_id": player.id,
                "move_type": "PASS"
            })
            move = StockRoundMove.fromMove(Move.fromMessage(msg))
            move.backfill(game.getState())
            result = minigame.run(move, game.getState())
            self.assertTrue(result, f"Pass failed for {player.name}: {minigame.errors()}")

        # Check next phase
        next_phase = minigame.next(game.getState())
        self.assertEqual(next_phase, "OperatingRound1")

        # Simulate phase transition (what performedMove does)
        StockRound.onComplete(game.getState())
        game.setMinigame("OperatingRound1")
        game.setPlayerOrder()

        # Call onStart with game parameter (this is the FIX)
        from app.minigames.operating_round import OperatingRound
        OperatingRound.onStart(game.getState(), game=game)

        # NOW operating_order should be set
        self.assertIsNotNone(game.operating_order, "operating_order should not be None")
        self.assertEqual(len(game.operating_order), 1,
                        "operating_order should have 1 floated company")
        self.assertEqual(game.operating_order[0], company.id,
                        f"operating_order should contain {company.id}")

    def test_game_performedMove_sets_operating_order(self):
        """Integration test: game.performedMove() should set operating_order on transition."""
        players = ["Alice", "Bob", "Charlie"]
        game = Game.start(players, "1889")

        # Jump to Stock Round
        game.setMinigame("StockRound")
        game.setPlayerOrder()
        StockRound.onStart(game.getState())
        game.setCurrentPlayer()

        # Float a company
        company = game.state.public_companies[0]
        alice = game.state.players[0]
        bob = game.state.players[1]
        charlie = game.state.players[2]

        company.setInitialPrice(100)
        company.buy(alice, StockPurchaseSource.IPO, 20)
        company.buy(bob, StockPurchaseSource.IPO, 10)
        company.buy(charlie, StockPurchaseSource.IPO, 10)
        company.buy(alice, StockPurchaseSource.IPO, 10)
        company.buy(bob, StockPurchaseSource.IPO, 10)

        # Create last dealer to set priority
        minigame = game.getMinigame()
        minigame.last_deal_player = alice

        # All players pass using actual game.performedMove()
        for player in game.state.players:
            game.current_player = player
            msg = json.dumps({
                "player_id": player.id,
                "move_type": "PASS"
            })
            move = StockRoundMove.fromMove(Move.fromMessage(msg))
            game.performedMove(move)

        # After all players pass, should be in OperatingRound1
        self.assertEqual(game.minigame_class, "OperatingRound1",
                        f"Should be in OperatingRound1, but in {game.minigame_class}")

        # operating_order should be set
        self.assertEqual(len(game.operating_order), 1,
                        "operating_order should have 1 floated company")
        self.assertEqual(game.operating_order[0], company.id,
                        f"operating_order should contain {company.id}")


if __name__ == '__main__':
    unittest.main()
