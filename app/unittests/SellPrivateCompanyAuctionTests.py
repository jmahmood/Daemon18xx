import json
import unittest

from app.base import Move, MutableGameState
from app.minigames.sell_private_company_auction import AuctionBidMove, Auction
from app.unittests.PrivateCompanyMinigameTests import fake_player, fake_private_company
from app.unittests.StockRoundMinigameTests import fake_public_company


class AuctionResponseTests(unittest.TestCase):
    pass

class AuctionBidTests(unittest.TestCase):
    def bid(self, amount) -> AuctionBidMove:
        msg = json.dumps({
            "player_id": "A",
            "private_company_id": "1",
            "move_type": "BID",
            "amount": amount
        })
        move = Move.fromMessage(msg)
        return AuctionBidMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B"), fake_player("C"), fake_player("D"), fake_player("E"), fake_player("F")]
        game_context.public_companies = [fake_public_company(x) for x in ["PublicABC", "PublicDEF", "PublicGHI"]]
        game_context.private_companies = [fake_private_company(int(x)) for x in [1, 2]]
        game_context.auctioned_private_company = game_context.private_companies[0]
        game_context.auctioned_private_company.belongs_to = game_context.players[5]
        game_context.auction = []

        game_context.stock_round_count = 1
        game_context.sales = [{},{}]
        game_context.purchases = [{},{}]
        return game_context

    def testPlayerValidBid(self):
        move = self.bid(250)
        state = self.state()

        minigame = Auction()
        self.assertTrue(minigame.run(move, state), minigame.errors())

    def testPlayerInsufficientCashBid(self):
        move = self.bid(650)
        state = self.state()

        minigame = Auction()
        # You should have insufficient cash to make this bid.
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You cannot afford poorboi. 650 (You have: 500)",
            minigame.errors()
        )

    def testPlayerWrongCompanyBid(self):
        move = self.bid(500)
        state = self.state()
        move.private_company_id = 2
        move.private_company = state.private_companies[1]

        minigame = Auction()
        # You can't bid on a company that is not up for auction
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You are bidding on the wrong company numbnuts. Fake company 2 vs. Fake company 1 Probably something wrong with your UI system.",
            minigame.errors()
        )

    def testPlayerSelfBid(self):
        move = self.bid(500)
        state = self.state()

        move.player_id = state.auctioned_private_company.belongs_to.id

        minigame = Auction()
        # You can't bid on a company that is not up for auction
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You can't bid on your own company.",
            minigame.errors()
        )

    def testPlayerBidTooSmall(self):
        move = self.bid(1)
        state = self.state()

        minigame = Auction()
        # You can't bid on a company that is not up for auction
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You are paying too little.  Your bid must be 1/2 to 2 times the price of the company (125 to 500).",
            minigame.errors()
        )


    def testPlayerBidTooLarge(self):
        move = self.bid(1000)
        state = self.state()

        minigame = Auction()
        # You can't bid on a company that is not up for auction
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You are paying too much.  Your bid must be 1/2 to 2 times the price of the company (125 to 500).",
            minigame.errors()
        )

if __name__ == "__main__":
    unittest.main()

