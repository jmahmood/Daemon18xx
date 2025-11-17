"""Integration tests for SELL_PRIVATE_COMPANY move type in StockRound.

Tests the flow from initiating a private company sale in stock round,
through the auction process, and back to stock round.
"""

import json
import unittest

from app.base import Move, MutableGameState
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.StockRoundSellPrivateCompany.minigame_auction import Auction
from app.minigames.StockRoundSellPrivateCompany.minigame_decision import AuctionDecision
from app.minigames.StockRoundSellPrivateCompany.move import AuctionBidMove, AuctionDecisionMove
from app.unittests.test_PrivateCompanyMinigame import fake_player, fake_private_company
from app.unittests.test_StockRoundMinigame import fake_public_company


class SellPrivateCompanyInitiationTests(unittest.TestCase):
    """Tests for initiating a private company sale from the stock round."""

    def create_state(self, stock_round_count=2) -> MutableGameState:
        """Create a basic game state for testing."""
        game_context = MutableGameState()
        game_context.players = [
            fake_player("A"), fake_player("B"), fake_player("C"),
            fake_player("D"), fake_player("E"), fake_player("F")
        ]
        game_context.public_companies = [
            fake_public_company(x) for x in ["PublicABC", "PublicDEF", "PublicGHI"]
        ]
        game_context.private_companies = [fake_private_company(int(x)) for x in [1, 2]]

        # Player F owns private company 1
        game_context.private_companies[0].belongs_to = game_context.players[5]
        if hasattr(game_context.players[5], 'private_companies'):
            game_context.players[5].private_companies.add(game_context.private_companies[0])

        game_context.stock_round_count = stock_round_count
        game_context.stock_round_play = 0
        game_context.stock_round_passed = 0
        game_context.sales = [{} for _ in range(stock_round_count + 1)]
        game_context.purchases = [{} for _ in range(stock_round_count + 1)]
        game_context.auction = None
        game_context.auctioned_private_company = None

        return game_context

    def create_sell_move(self, player_id="F", private_company_id=1) -> StockRoundMove:
        """Create a SELL_PRIVATE_COMPANY move."""
        msg = json.dumps({
            "player_id": player_id,
            "move_type": "SELL_PRIVATE_COMPANY",
            "private_company_id": private_company_id
        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def test_valid_private_company_sale_initiation(self):
        """Player can initiate a private company sale after first stock round."""
        move = self.create_sell_move()
        state = self.create_state(stock_round_count=2)
        minigame = StockRound()

        initial_play_count = state.stock_round_play

        result = minigame.run(move, state)
        self.assertTrue(result, minigame.errors())

        # Verify auction state is properly initialized
        self.assertEqual(state.auctioned_private_company, state.private_companies[0])
        self.assertEqual(state.auction, [])
        self.assertTrue(minigame.sell_private_company_auction)

        # stock_round_play should NOT increment when initiating sale
        self.assertEqual(state.stock_round_play, initial_play_count)

        # Next minigame should be Auction
        self.assertEqual(minigame.next(state), "Auction")

    def test_cannot_sell_in_first_stock_round(self):
        """Players cannot sell private companies in the first stock round."""
        move = self.create_sell_move()
        state = self.create_state(stock_round_count=1)
        minigame = StockRound()

        result = minigame.run(move, state)
        self.assertFalse(result)
        errors = minigame.errors()
        self.assertTrue(any("You can't sell a private company in the first stock round" in err
                           for err in errors), f"Expected error not found in: {errors}")

    def test_cannot_sell_company_you_dont_own(self):
        """Players cannot sell private companies they don't own."""
        # Player A trying to sell Player F's company
        move = self.create_sell_move(player_id="A", private_company_id=1)
        state = self.create_state(stock_round_count=2)
        minigame = StockRound()

        result = minigame.run(move, state)
        self.assertFalse(result)
        errors = minigame.errors()
        self.assertTrue(any("You can't sell a private company you don't own" in err
                           for err in errors), f"Expected error not found in: {errors}")

    def test_cannot_sell_nonexistent_company(self):
        """Selling a non-existent private company fails gracefully."""
        # Try to sell company 999 which doesn't exist
        move = self.create_sell_move(player_id="F", private_company_id=999)
        state = self.create_state(stock_round_count=2)
        minigame = StockRound()

        # Should fail during backfill or validation
        try:
            result = minigame.run(move, state)
            # If it doesn't throw, it should return False
            self.assertFalse(result)
        except StopIteration:
            # Expected if company not found during backfill
            pass


class FullSellPrivateCompanyFlowTests(unittest.TestCase):
    """Integration tests for the complete private company sale flow."""

    def create_state(self) -> MutableGameState:
        """Create a game state ready for full auction flow."""
        game_context = MutableGameState()
        game_context.players = [
            fake_player("A"), fake_player("B"), fake_player("C"),
            fake_player("D"), fake_player("E"), fake_player("F")
        ]
        game_context.public_companies = [
            fake_public_company(x) for x in ["PublicABC", "PublicDEF", "PublicGHI"]
        ]
        game_context.private_companies = [fake_private_company(int(x)) for x in [1, 2]]

        # Player F owns private company 1
        game_context.private_companies[0].belongs_to = game_context.players[5]
        if hasattr(game_context.players[5], 'private_companies'):
            game_context.players[5].private_companies.add(game_context.private_companies[0])

        game_context.stock_round_count = 2
        game_context.stock_round_play = 0
        game_context.stock_round_passed = 0
        game_context.sales = [{}, {}, {}]
        game_context.purchases = [{}, {}, {}]

        return game_context

    def test_full_auction_flow_with_acceptance(self):
        """Test complete flow: sell → auction → accept → stock round."""
        state = self.create_state()

        # Step 1: Player F initiates sale
        sell_msg = json.dumps({
            "player_id": "F",
            "move_type": "SELL_PRIVATE_COMPANY",
            "private_company_id": 1
        })
        sell_move = StockRoundMove.fromMove(Move.fromMessage(sell_msg))
        stock_round = StockRound()

        result = stock_round.run(sell_move, state)
        self.assertTrue(result, stock_round.errors())
        self.assertEqual(stock_round.next(state), "Auction")

        # Step 2: Other players bid (A bids 100, B bids 150, C-E pass)
        auction = Auction()

        # Player A bids 100
        bid_a_msg = json.dumps({
            "player_id": "A",
            "move_type": "BID",
            "private_company_id": 1,
            "amount": 100
        })
        bid_a = AuctionBidMove.fromMove(Move.fromMessage(bid_a_msg))
        self.assertTrue(auction.run(bid_a, state))

        # Player B bids 150
        bid_b_msg = json.dumps({
            "player_id": "B",
            "move_type": "BID",
            "private_company_id": 1,
            "amount": 150
        })
        bid_b = AuctionBidMove.fromMove(Move.fromMessage(bid_b_msg))
        self.assertTrue(auction.run(bid_b, state))

        # Players C, D, E pass
        for player_id in ["C", "D", "E"]:
            pass_msg = json.dumps({
                "player_id": player_id,
                "move_type": "PASS",
                "private_company_id": 1
            })
            pass_move = AuctionBidMove.fromMove(Move.fromMessage(pass_msg))
            self.assertTrue(auction.run(pass_move, state))

        # Should transition to AuctionDecision
        self.assertEqual(auction.next(state), "AuctionDecision")

        # Step 3: Player F accepts Player B's bid of 150
        original_f_cash = state.players[5].cash
        original_b_cash = state.players[1].cash

        accept_msg = json.dumps({
            "player_id": "F",
            "move_type": "ACCEPT",
            "accepted_player_id": "B"
        })
        accept_move = AuctionDecisionMove.fromMove(Move.fromMessage(accept_msg))
        decision = AuctionDecision()

        self.assertTrue(decision.run(accept_move, state))

        # Verify ownership transfer
        self.assertEqual(state.private_companies[0].belongs_to, state.players[1])

        # Verify cash transfer
        self.assertEqual(state.players[5].cash, original_f_cash + 150)
        self.assertEqual(state.players[1].cash, original_b_cash - 150)

        # Verify stock_round_play incremented
        self.assertEqual(state.stock_round_play, 1)

        # Should return to StockRound
        self.assertEqual(decision.next(state), "StockRound")

    def test_full_auction_flow_with_rejection(self):
        """Test complete flow: sell → auction → reject → stock round."""
        state = self.create_state()

        # Step 1: Player F initiates sale
        sell_msg = json.dumps({
            "player_id": "F",
            "move_type": "SELL_PRIVATE_COMPANY",
            "private_company_id": 1
        })
        sell_move = StockRoundMove.fromMove(Move.fromMessage(sell_msg))
        stock_round = StockRound()

        self.assertTrue(stock_round.run(sell_move, state))

        # Step 2: Collect bids
        auction = Auction()
        for player_id in ["A", "B", "C", "D", "E"]:
            pass_msg = json.dumps({
                "player_id": player_id,
                "move_type": "PASS",
                "private_company_id": 1
            })
            pass_move = AuctionBidMove.fromMove(Move.fromMessage(pass_msg))
            self.assertTrue(auction.run(pass_move, state))

        # Step 3: Player F rejects all bids
        original_f_cash = state.players[5].cash

        reject_msg = json.dumps({
            "player_id": "F",
            "move_type": "REJECT"
        })
        reject_move = AuctionDecisionMove.fromMove(Move.fromMessage(reject_msg))
        decision = AuctionDecision()

        self.assertTrue(decision.run(reject_move, state))

        # Verify ownership unchanged
        self.assertEqual(state.private_companies[0].belongs_to, state.players[5])

        # Verify cash unchanged
        self.assertEqual(state.players[5].cash, original_f_cash)

        # Should return to StockRound
        self.assertEqual(decision.next(state), "StockRound")


if __name__ == '__main__':
    unittest.main()
