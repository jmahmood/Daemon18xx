import json
import unittest

import logging

from app.minigames.PrivateCompanyInitialAuction.enums import BidType
from app.minigames.PrivateCompanyInitialAuction.minigame_auction import BiddingForPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.state import MutableGameState
from app.unittests.PrivateCompanyMinigameTests import fake_player, fake_private_company

# logging.basicConfig(level=logging.DEBUG)

from app.base import Move


class BasicInitializationTests(unittest.TestCase):
    def _context(self):
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 2000), fake_player("B", 2000), fake_player("C", 3000)]
        game_context.private_companies = [fake_private_company(0), fake_private_company(1)]
        game_context.private_companies[1].bid(game_context.players[0], 255)
        game_context.private_companies[1].bid(game_context.players[1], 260)
        return game_context

    def _move(self):
        move_json = {
            "private_company_order": 1,  # Doesn't really matter at this point.
            "move_type": "BID",
            "player_id": "A",
            "bid_amount": 265
        }
        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)

    def _pass_move(self):
        move_json = {
            "private_company_order": 1,  # Doesn't really matter at this point.
            "move_type": "PASS",
            "player_id": "A",
            "bid_amount": 265
        }
        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)

    def testInitializeMove(self):
        """This is the base "correct" case (they have enough money, are bidders,
        haven't passed, etc)."""

        bid_move = self._move()
        context = self._context()
        bfpc = BiddingForPrivateCompany()

        self.assertTrue(bfpc.run(bid_move, context), bfpc.errors())

    def testInsufficientCash(self):
        """Make sure they have enough money."""

        bid_move = self._move()
        context = self._context()
        context.players[0].cash = 200
        bfpc = BiddingForPrivateCompany()

        self.assertFalse(bfpc.run(bid_move, context), bfpc.errors())

    def testPassedAlready(self):
        """Make sure they have enough money."""
        _pass_move = self._pass_move()
        bid_move = self._move()
        context = self._context()
        bfpc = BiddingForPrivateCompany()

        self.assertTrue(bfpc.run(_pass_move, context), bfpc.errors())
        self.assertEqual(_pass_move.move_type, BidType.PASS)
        self.assertEqual(len(context.private_companies[1].passed_by), 1)

        self.assertFalse(bfpc.run(bid_move, context), bfpc.errors())
        self.assertIn("You can only keep bidding until you've passed once.", bfpc.errors())

    def testAutopurchaseOnLastPass(self):
        """If the last person passes, you should assign the new owner asap."""
        _pass_move = self._pass_move()
        context = self._context()
        bfpc = BiddingForPrivateCompany()

        self.assertTrue(bfpc.run(_pass_move, context), bfpc.errors())
        self.assertEqual(_pass_move.move_type, BidType.PASS)
        self.assertEqual(len(context.private_companies[1].passed_by), 1)

        self.assertTrue(context.private_companies[1].hasOwner())
        self.assertNotEqual(context.private_companies[1].belongs_to,
                            _pass_move.player,
                            context.private_companies[1].belongs_to.id
                            )
        self.assertEqual(
            context.private_companies[1].belongs_to,
            context.players[1],
            context.private_companies[1].belongs_to.id
        )


if __name__ == "__main__":
    unittest.main()
