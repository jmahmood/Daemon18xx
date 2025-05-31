import json
import unittest

from app.base import PrivateCompany, Move, Player
from app.minigames.PrivateCompanyInitialAuction.enums import BidType
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.state import MutableGameState


def fake_private_company(order=1, cost=250):
    pc = PrivateCompany.initiate(
        order,
        "Fake company {}".format(order),
        "FC{}".format(order),
        cost,
        int(cost / 2),
        "A1",
        belongs_to=None,
    )
    return pc


def fake_player(id="A", cash=500, order=1):
    player = Player()
    player.id = id
    player.cash = cash
    player.order = order
    player.private_companies = set()
    player.sold_this_round = set()
    return player


class BasicInitializationTests(unittest.TestCase):
    def testBidType(self):
        for enumval, name, id in [(BidType.BUY, "BUY", 1), (BidType.BID, "BID", 2), (BidType.PASS, "PASS", 3)]:
            self.assertEqual(enumval, BidType(id))
            self.assertEqual(enumval, BidType[name])
            with self.assertRaises(ValueError):
                BidType(name)

    def testInitializeMove(self):
        move_json = {
            "private_company_order": 1,
            "move_type": "BUY",
            "player_id": "A",
            "bid_amount": 0
        }
        move = Move.fromMessage(json.dumps(move_json))
        private_company_purchase_move = BuyPrivateCompanyMove.fromMove(move)
        self.assertEqual(private_company_purchase_move.private_company_order, 1)
        self.assertEqual(private_company_purchase_move.move_type, BidType.BUY)
        self.assertEqual(private_company_purchase_move.player_id, "A")
        self.assertEqual(private_company_purchase_move.bid_amount, 0)

        self.assertIsNone(private_company_purchase_move.player)
        self.assertIsNone(private_company_purchase_move.private_company)

        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.private_companies = [fake_private_company(0), fake_private_company(1)]

        private_company_purchase_move.backfill(game_context)

        self.assertEqual(private_company_purchase_move.player, game_context.players[0])
        self.assertEqual(private_company_purchase_move.private_company, game_context.private_companies[1])

        duck_type_checking_player = fake_player("A")
        duck_type_checking_company = fake_private_company(1)
        self.assertEqual(private_company_purchase_move.player, duck_type_checking_player)
        self.assertEqual(private_company_purchase_move.private_company, duck_type_checking_company)


class BuyPrivateCompanyMinigameBuyTests(unittest.TestCase):
    def _getContext(self):
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.private_companies = [fake_private_company(0), fake_private_company(1)]
        return game_context

    def _getMove(self):
        move_json = {
            "private_company_order": 0,
            "move_type": "BUY",
            "player_id": "A",
            "bid_amount": 0
        }
        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)


    def testRunBuyPrivateCompanyMinigame(self):
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.player, game_context.players[0])
        self.assertEqual(private_company_purchase_move.private_company, game_context.private_companies[0])
        self.assertEqual(private_company_purchase_move.private_company.belongs_to, private_company_purchase_move.player)

        self.assertEqual(private_company_purchase_move.player.cash, 500 - 250, "Player is not paying for the company")


    def testRunBuyPrivateCompanyMinigameWrongOrder(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.private_company_order = 1

        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("You can't buy this yet. Fake company 0 needs to be sold first.", minigame.errors())

        self.assertEqual(private_company_purchase_move.player, game_context.players[0])
        self.assertEqual(private_company_purchase_move.private_company, game_context.private_companies[1])
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Player shouldn't have to pay if there is an error.")

    def testRunBuyPrivateCompanyMinigameFirstHasBeenBought(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.private_company_order = 1

        game_context = self._getContext()
        game_context.private_companies[0].belongs_to = game_context.players[0]

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.private_company.belongs_to, private_company_purchase_move.player)
        self.assertEqual(private_company_purchase_move.player.cash, 500 - 250, "Player is not paying for the company")

    def testRunBuyPrivateCompanyMinigameAlreadyHasOwner(self):
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()
        game_context.private_companies[0].belongs_to = game_context.players[0]

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("Someone already owns this cheatingboi Fake company 0 / A", minigame.errors())
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Don't pay if you get things wrong.")

    def testRunBuyPrivateCompanyMinigamePoorboi(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.private_company_order = 1
        game_context = self._getContext()
        game_context.private_companies[0].belongs_to = game_context.players[0]
        game_context.private_companies[1].cost = 12000
        game_context.private_companies[1].actual_cost = 10000

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("You cannot afford poorboi. {} (You have: {})".format(10000, 500), minigame.errors())
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Don't pay if you get things wrong.")

    def testRunBuyPrivateCompanyWithBid(self):
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()
        game_context.private_companies[0].bid(game_context.players[1], 1000)

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("You cannot buy something that has a bid on it.", minigame.errors())
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Don't pay if you get things wrong.")


class BuyPrivateCompanyMinigameBidTests(unittest.TestCase):
    def _getContext(self):
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.private_companies = [fake_private_company(0), fake_private_company(1)]
        return game_context

    def _getMove(self):
        move_json = {
            "private_company_order": 1,
            "move_type": "BID",
            "player_id": "A",
            "bid_amount": 255
        }
        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)

    def testRunBuyPrivateCompanyMinigame(self):
        """Tests that a bid is taken out of hte player's account and that the bid is listed on the private company"""
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.player, game_context.players[0])
        self.assertEqual(private_company_purchase_move.private_company, game_context.private_companies[1])
        self.assertTrue(private_company_purchase_move.private_company.hasNoOwner)

        self.assertEqual(private_company_purchase_move.player.cash, 500 - 255,
                         "Player is not paying for bidding on the company (Money should be kept in trust)")

        self.assertTrue(private_company_purchase_move.private_company.hasBids())


    def testRunBuyPrivateCompanyMinigameWrongOrder(self):
        """You cannot bid on something which is up for sale."""
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.private_company_order = 0
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("You can't bid on this, it's currently for sale", minigame.errors())

        self.assertEqual(private_company_purchase_move.player, game_context.players[0])
        self.assertEqual(private_company_purchase_move.private_company, game_context.private_companies[0])
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Player shouldn't have to pay if there is an error.")


    def testRunBuyPrivateCompanyMinigamePoorboiBoi(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.bid_amount = 13000
        game_context = self._getContext()
        game_context.private_companies[1].cost = 12000
        game_context.private_companies[1].actual_cost = 10000

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("You cannot afford poorboi. {} (You have: {})".format(13000, 500), minigame.errors())
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Don't pay if you get things wrong.")

    def testRunBuyPrivateCompanyMinigameWeenieBoi(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.bid_amount = 250
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))
        self.assertIn("Your bid is too small weenieboi. {} (Minimum Bid: {})".format(250, 255), minigame.errors())
        self.assertEqual(private_company_purchase_move.player.cash, 500, "Don't pay if you get things wrong.")

    def testRunBuyPrivateCompanyMinigamePriceDown(self):
        private_company_purchase_move = self._getMove()
        private_company_purchase_move.bid_amount = 255
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.player.cash, 500 - 255,
                         "Player is not paying for bidding on the company (Money should be kept in trust)")

        private_company_purchase_move = self._getMove()
        private_company_purchase_move.player = game_context.players[1]
        private_company_purchase_move.player_id = game_context.players[1].id
        private_company_purchase_move.bid_amount = 260

        self.assertEqual(private_company_purchase_move.player.cash, 500,
                         "Player 2 should still have his cash..")

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context), minigame.error_list)

        self.assertTrue(game_context.private_companies[0].pass_count == 2, "Pass count is: {}".format(game_context.private_companies[0].pass_count))
        self.assertTrue(game_context.private_companies[0].cost == game_context.private_companies[0].actual_cost + 5)


class BuyPrivateCompanyMinigamePassTests(unittest.TestCase):
    def _getContext(self):
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.private_companies = [fake_private_company(0), fake_private_company(1)]
        return game_context

    def _getMove(self):
        move_json = {
            "private_company_order": 0,
            "move_type": "PASS",
            "player_id": "A",
            "bid_amount": 255
        }
        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)

    def testBuyPrivateCompanyMinigamePassNormal(self):
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()

        minigame = BuyPrivateCompany()
        self.assertTrue(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.player.cash, 500,
                         "No cash loss for a pass action")

        self.assertTrue(game_context.private_companies[0].pass_count == 1,
                        "Pass count is: {}".format(game_context.private_companies[0].pass_count))

        # All players haven't passed so the cost should not go up.
        self.assertTrue(game_context.private_companies[0].cost == game_context.private_companies[0].actual_cost)

    def testBuyPrivateCompanyMinigamePassFreeCompany(self):
        private_company_purchase_move = self._getMove()
        game_context = self._getContext()
        game_context.private_companies[0].actual_cost = 0

        minigame = BuyPrivateCompany()
        self.assertFalse(minigame.run(private_company_purchase_move, game_context))

        self.assertEqual(private_company_purchase_move.player.cash, 500,
                         "You must purchase the private company if its price has been reduced to zero. ({})".format(0))

        self.assertTrue(game_context.private_companies[0].pass_count == 0,
                        "Pass count is: {}".format(game_context.private_companies[0].pass_count))

        # All players haven't passed so the cost should not go up.
        self.assertTrue(game_context.private_companies[0].cost != game_context.private_companies[0].actual_cost)


if __name__ == "__main__":
    unittest.main()
