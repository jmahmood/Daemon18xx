"""
Do a full simulation of Private Company rounds and make sure that everything runs according to plan.
"""
import unittest

from app.base import Move
from app.state import Game, PrivateCompanyInitialAuctionTurnOrder
from app.unittests.scenarios.move_factory import PrivateCompanyInitialAuctionMoves


def skip_private_companies_round(game: Game):
    """Skips the private round by having each player in the initial 6 buy whatever company there is in their order"""
    state = game.getState()
    for i, player in enumerate(state.players):
        move = PrivateCompanyInitialAuctionMoves.buy(player.name, state.private_companies[i].short_name, state)
        game.performedMove(move)


class SimulateFullPrivateCompanyRound(unittest.TestCase):

    def execute_invalid_player(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertFalse(
            game.isValidPlayer(move), game.errors()
        )

    def execute_invalid_move(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertTrue(
            game.isValidPlayer(move), game.errors()
        )

        self.assertFalse(
            game.performedMove(move),
            "This move should have failed but it actually succeeded"
        )

    def execute_valid_move(self, game, move: Move):
        self.assertTrue(
            game.isValidMove(move)
        )

        self.assertTrue(
            game.isValidPlayer(move),
            [game.errors(), game.current_player, [str(p) for p in game.state.players]]
        )

        self.assertTrue(
            game.performedMove(move),
            game.errors()
        )

    def testInitialBuyPrivateCompanyRound(self):
        player_details = [
            "Jawaad",
            "Alex",
            "Baba",
            "Sho",
            "Yuki",
            "Rafael"
        ]

        game = Game.start(player_details)
        game.setPlayerOrder()
        game.setCurrentPlayer()

        state = game.getState()

        self.assertEqual(game.current_player, state.players[0])

        move1 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 45, state)
        self.execute_valid_move(game, move1)

        self.assertEqual(game.state.players[0].cash, 2400 / 6 - 45)

        self.assertEqual(state.players[1], game.current_player,
                         "Current player should be {} but it is actually {}".format(
                             state.players[1].name, game.current_player.name
                         ))

        self.assertEqual(game.current_player, state.players[1])

        move2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)

        self.execute_valid_move(game, move2)

        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        self.assertEqual(game.current_player, state.players[2])

        move3wrong = PrivateCompanyInitialAuctionMoves.buy("Sho", "SVR", state)

        self.assertTrue(
            game.isValidMove(move3wrong)
        )

        self.assertFalse(
            game.isValidPlayer(move3wrong), game.errors()
        )

        move3 = PrivateCompanyInitialAuctionMoves.buy("Baba", "SVR", state)
        self.execute_valid_move(game, move3)

        # TODO Now we are in a bidding phase.  Jawaad / Alex exchange bidding until one passes
        self.assertEqual(game.current_player, state.players[0], game.current_player)
        self.assertEqual(game.minigame_class, "BiddingForPrivateCompany")

        move4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 55, state)
        self.execute_valid_move(game, move4)
        self.assertEqual(game.state.players[0].cash, 2400 / 6 - 100)

        move5 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 50, state)
        self.execute_invalid_move(game, move5)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_v2 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 55, state)
        self.execute_invalid_move(game, move5_v2)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_v3 = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 56, state)
        self.execute_invalid_move(game, move5_v3)

        move5_v4 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "C&StL", 60, state)
        self.execute_invalid_player(game, move5_v4)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 50)

        move5_corrected = PrivateCompanyInitialAuctionMoves.bid("Alex", "C&StL", 60, state)
        self.execute_valid_move(game, move5_corrected)
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 110)

        move_6 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Jawaad", "C&StL", state)
        self.execute_valid_move(game, move_6)

        self.assertEqual(game.minigame_class, "BuyPrivateCompany")
        self.assertEqual(game.state.private_companies[1].belongs_to,
                         game.state.players[1],
                         game.state.private_companies[1])
        self.assertEqual(game.state.players[0].cash, 2400 / 6, "You need to return the money")
        self.assertEqual(game.state.players[1].cash, 2400 / 6 - 60)

        self.assertEqual(game.current_player, state.players[3], [str(state.players[3]), "is not", str(game.current_player)])
        move_7 = PrivateCompanyInitialAuctionMoves.bid("Sho", "M&H", 115, state)
        self.execute_valid_move(game, move_7)

        move_8 = PrivateCompanyInitialAuctionMoves.buy("Yuki", "D&H", state)
        self.execute_valid_move(game, move_8)
        self.assertEqual(state.private_companies[2].belongs_to, state.players[4])

        self.assertEqual(state.private_companies[3].belongs_to, state.players[3],
                         "The lone bid by Sho should be auto-accepted and he should be made the owner")

        move_9_invalid = PrivateCompanyInitialAuctionMoves.bid("Rafael", "M&H", 115, state)
        self.execute_invalid_move(game, move_9_invalid)

        move_9_invalid_bid = PrivateCompanyInitialAuctionMoves.bid("Rafael", "C&A", 165, state)
        self.execute_invalid_move(game, move_9_invalid_bid)

        move_9 = PrivateCompanyInitialAuctionMoves.bid("Rafael", "B&O", 230, state)
        self.execute_valid_move(game, move_9)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_10 = PrivateCompanyInitialAuctionMoves.bid("Jawaad", "B&O", 235, state)
        self.execute_valid_move(game, move_10)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_11 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Alex", "C&A", state)
        self.execute_valid_move(game, move_11)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_12 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Baba", "C&A", state)
        self.execute_valid_move(game, move_12)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_13 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Sho", "C&A", state)
        self.execute_valid_move(game, move_13)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_14 = PrivateCompanyInitialAuctionMoves.bid("Yuki", "B&O", 240, state)
        self.execute_valid_move(game, move_14)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        move_15 = PrivateCompanyInitialAuctionMoves.pass_on_bid("Rafael", "C&A", state)
        self.execute_valid_move(game, move_15)
        self.assertEqual(game.minigame_class, "BuyPrivateCompany")

        self.assertEqual(state.private_companies[4].cost, state.private_companies[4].actual_cost + 5,
                         "Price needs to come down after 6 players pass or bid on something else.")

        while state.private_companies[4].actual_cost > 0:
            for p in player_details:
                if state.private_companies[4].actual_cost > 0:
                    move_ongoing = PrivateCompanyInitialAuctionMoves.pass_on_bid(p, "C&A", state)
                    self.execute_valid_move(game, move_ongoing)
                    self.assertEqual(game.minigame_class, "BuyPrivateCompany")
                else:
                    # Last player (Rafael in this case) doesn't have a choice; he needs to buy, but he needs to select
                    # that action as he may not realize it.
                    player_cash = state.players[5].cash
                    move_purchase = PrivateCompanyInitialAuctionMoves.buy(p, "C&A", state)
                    self.execute_valid_move(game, move_purchase)
                    self.assertEqual(state.players[5].cash, player_cash - 0)  # Costs nothing now.

        self.assertEqual(game.minigame_class, "BiddingForPrivateCompany")
        player_order_obj: PrivateCompanyInitialAuctionTurnOrder = game.get_player_order_fn()
        self.assertEqual(
            len(player_order_obj.players), 3
        )

        self.assertEqual(
            player_order_obj.players, [state.players[5], state.players[0], state.players[4]]
        )

        for p in ["Rafael", "Jawaad", "Yuki"][0:2]:
            move_pass = PrivateCompanyInitialAuctionMoves.pass_on_bid(p, "B&O", state)
            self.execute_valid_move(game, move_pass)

        self.assertEqual(state.private_companies[-1].belongs_to, state.players[4])
        self.assertEqual(game.minigame_class, "StockRound")


if __name__ == "__main__":
    unittest.main()
