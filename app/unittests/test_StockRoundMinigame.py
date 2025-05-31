"""

4. Test for non-president buying additional stock (reaching 30%)
    -> President should be transferred over.
"""
import json
import unittest

from app.base import Move, PublicCompany, PrivateCompany, MutableGameState, StockPurchaseSource, STOCK_CERTIFICATE, \
    STOCK_PRESIDENT_CERTIFICATE
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRound.move import StockRoundMove
from app.unittests.test_PrivateCompanyMinigame import fake_player


def fake_public_company(name="1") -> PublicCompany:
    pc = PublicCompany.initiate(
        name="Fake company {}".format(name),
        short_name="FC{}".format(name),
        id=name,
        cash=0,
        tokens_available=4,
        token_costs=[40, 60, 80, 100]
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

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A"), fake_player("B")]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 1
        game_context.sales = [{},{}]
        game_context.purchases = [{},{}]
        return game_context

    def testPlayerPurchasesInitialStockInvalidPrice(self):
        move = self.move()
        state = self.state()

        move.ipo_price = 3  # Invalid Price

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn('Invalid IPO Price (3).  Valid prices are 100,90,82,76,71,67.', minigame.errors())


    def testPlayerPurchasesInitialStockNoCash(self):
        move = self.move()
        state = self.state()
        state.players[0].cash = 1

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn('You cannot afford poorboi. 90.0 (You have: 1)', minigame.errors())

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

        self.assertEqual(move.public_company.president, move.player)

        self.assertFalse(
            move.public_company.isFloated()
        )

        try:
            self.assertIn(
                state.public_companies[0],
                state.purchases[state.stock_round_count][state.players[0]],
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")

    def testPlayerPurchasesNonInitialStock(self):
        move = self.move()
        state = self.state()
        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[1], StockPurchaseSource.IPO, 50)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.players[0].cash, 500 - 72 * 1)
        self.assertIn(
            move.player, move.public_company.owners.keys()
        )
        self.assertEqual(
            move.public_company.owners[move.player], 10
        )

        self.assertTrue(
            move.public_company.isFloated()
        )

        self.assertEqual(move.public_company.president, state.players[1])
        self.assertEqual(move.public_company.cash, 72 * 10)

        try:
            self.assertIn(
                state.public_companies[0],
                state.purchases[state.stock_round_count][state.players[0]],
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")

    def test_player_cannot_exceed_sixty_percent(self):
        move = self.move()
        state = self.state()
        state.players[0].cash = 10000
        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[0], StockPurchaseSource.IPO, 60)

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], 60)
        self.assertIn(
            "You can't own more than 60% of a company ABC Fake company ABC",
            minigame.errors(),
        )

    def test_player_can_buy_up_to_sixty_percent(self):
        move = self.move()
        state = self.state()
        state.players[0].cash = 10000
        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[0], StockPurchaseSource.IPO, 50)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], 60)

    def test_certificate_limit_allows_final_share(self):
        """Player at certificate limit minus one may buy one more share."""
        move = self.move()
        state = self.state()
        # Add two extra players to enforce 4-player limit of 25
        state.players.append(fake_player("C"))
        state.players.append(fake_player("D"))

        # Give current player 24 private company certificates
        for i in range(24):
            pc = PrivateCompany.initiate(i, f"PC{i}", f"PC{i}", 0, 0, "A1")
            state.players[0].private_companies.add(pc)

        state.public_companies[0].setInitialPrice(72)
        state.public_companies[0].buy(state.players[1], StockPurchaseSource.IPO, 20)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())

    def test_certificate_limit_blocks_president_cert(self):
        """Buying a 20% certificate would exceed the limit and should fail."""
        move = self.move()
        state = self.state()
        state.players.append(fake_player("C"))
        state.players.append(fake_player("D"))

        for i in range(24):
            pc = PrivateCompany.initiate(i, f"PC{i}", f"PC{i}", 0, 0, "A1")
            state.players[0].private_companies.add(pc)

        # Ensure purchase is for a president's share
        move.ipo_price = 90
        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn("You have too many certificates", minigame.errors()[0])


class StockRoundMinigameSellTests(unittest.TestCase):
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "SELL",
            "player_id": "A",
            "for_sale_raw": [["ABC", 10], ["DEF", 10]]

        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerInvalidSellRound(self):
        # You've already bought this company this round.

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        state.purchases[state.stock_round_count][state.players[0]] = [state.public_companies[0]]

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], STOCK_CERTIFICATE,
                         "The amount of stock in state should not have changed.")

    def testPlayerValidSellRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

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

        try:
            self.assertIn(
                state.public_companies[0],
                state.sales[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

    def test_bank_pool_limit(self):
        move = self.move()
        move.for_sale_raw = [["ABC", 10]]
        state = self.state()
        self.initial_setup_company(
            state.public_companies[0],
            [(state.players[0], STOCK_CERTIFICATE), (state.players[1], STOCK_PRESIDENT_CERTIFICATE)],
            72,
        )
        state.public_companies[0].stocks[StockPurchaseSource.BANK] = 50

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You can't sell that much (10); the bank can only have 50 shares max.",
            minigame.errors(),
        )

    def test_cannot_sell_in_first_round(self):
        move = self.move()
        state = self.state()
        state.stock_round_count = 1

        self.initial_setup_company(
            state.public_companies[0],
            [(state.players[0], STOCK_CERTIFICATE), (state.players[1], STOCK_PRESIDENT_CERTIFICATE)],
            72,
        )

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn(
            "You can only sell after the first stock round.",
            minigame.errors(),
        )




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

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerInvalidBuyWeirdQuantityRound(self):
        """You can't buy what doesn't exist"""
        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], 20),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)
        move.for_sale_raw = [["ABC", 15]]
        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn("You can only sell in units of 10 stocks (15)", minigame.errors())

    def testPlayerInvalidBuyNoStockLeftRound(self):
        """You can't buy what doesn't exist"""
        move = self.move()
        state = self.state()
        self.initial_setup_company(
            state.public_companies[2], [(state.players[1], 100)], 72
        )
        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertIn("The company does not have enough stock in category StockPurchaseSource.IPO", minigame.errors())

    def testPlayerInvalidBuySellRound(self):
        # You've already bought this company this round.

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        state.purchases[state.stock_round_count][state.players[0]] = [state.public_companies[0]]

        minigame = StockRound()
        self.assertFalse(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.public_companies[0].owners[state.players[0]], STOCK_CERTIFICATE,
                         "The amount of stock in state should not have changed.")
        self.assertEqual(len(state.public_companies[2].owners.keys()), 0,
                         "The buy order should not be executed either.")

    def testPlayerValidBuySellRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

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

        try:
            self.assertIn(
                state.public_companies[0],
                state.sales[state.stock_round_count][state.players[0]],
                "You need to have {} in {}".format(state.public_companies[0],
                                                   [str(company) for company in
                                                   state.sales[state.stock_round_count][state.players[0]]])
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

        try:
            self.assertIn(
                state.public_companies[1],
                state.sales[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the sales dict")

        try:
            self.assertIn(
                state.public_companies[2],
                state.purchases[state.stock_round_count][state.players[0]]
            )
        except KeyError:
            self.assertEqual(True, False, "The Player has not been added to the purchases dict")


class StockRoundMinigamePassTests(unittest.TestCase):
    """Realistically, this is the most important one."""
    def move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "PASS",
            "player_id": "A",
        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company(str(x)) for x in ["ABC", "DEF", "GHI"]]
        game_context.stock_round_count = 2
        game_context.stock_round_play = 0
        game_context.stock_round_passed = 0
        game_context.sales = [{},{},{}]
        game_context.purchases = [{},{},{}]

        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def testPlayerValidPassRound(self):
        """
        A very basic buy / sell round (buying one stock and selling two others).

        It should go without a hitch.
        :return:
        """

        move = self.move()
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [(state.players[0], STOCK_CERTIFICATE),
                                    (state.players[1], STOCK_PRESIDENT_CERTIFICATE)], 72)

        self.initial_setup_company(state.public_companies[1],
                                   [(state.players[0], STOCK_CERTIFICATE + STOCK_PRESIDENT_CERTIFICATE),], 72)

        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(state.stock_round_passed, self.state().stock_round_passed + 1)


class StockRoundPriceAdjustmentTests(unittest.TestCase):
    def sell_move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "SELL",
            "player_id": "A",
            "for_sale_raw": [["ABC", 10]]
        })
        move = Move.fromMessage(msg)
        return StockRoundMove.fromMove(move)

    def sell_state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company("ABC")]
        game_context.stock_round_count = 2
        game_context.sales = [{}, {}, {}]
        game_context.purchases = [{}, {}, {}]
        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def test_price_decreases_on_sale(self):
        move = self.sell_move()
        state = self.sell_state()
        self.initial_setup_company(
            state.public_companies[0],
            [(state.players[0], STOCK_CERTIFICATE), (state.players[1], STOCK_PRESIDENT_CERTIFICATE)],
            72,
        )
        initial_bank_price = state.public_companies[0].stockPrice[StockPurchaseSource.BANK]
        initial_ipo_price = state.public_companies[0].stockPrice[StockPurchaseSource.IPO]
        minigame = StockRound()
        self.assertTrue(minigame.run(move, state), minigame.errors())
        self.assertEqual(
            state.public_companies[0].stockPrice[StockPurchaseSource.BANK],
            initial_bank_price - 10,
        )
        self.assertEqual(
            state.public_companies[0].stockPrice[StockPurchaseSource.IPO],
            initial_ipo_price,
        )

    def test_price_increases_when_no_stock_left(self):
        state = self.sell_state()
        state.public_companies = [fake_public_company("ABC")]
        company = state.public_companies[0]
        company.setInitialPrice(72)
        company.buy(state.players[0], StockPurchaseSource.IPO, 100)
        initial_bank_price = company.stockPrice[StockPurchaseSource.BANK]
        initial_ipo_price = company.stockPrice[StockPurchaseSource.IPO]
        company.checkPriceIncrease()
        self.assertEqual(
            company.stockPrice[StockPurchaseSource.BANK],
            initial_bank_price + 10,
        )
        self.assertEqual(
            company.stockPrice[StockPurchaseSource.IPO],
            initial_ipo_price,
        )


class StockRoundPresidencyTests(unittest.TestCase):
    def setup_company(self):
        state = MutableGameState()
        state.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        state.public_companies = [fake_public_company("ABC")]
        company = state.public_companies[0]
        company.setInitialPrice(72)
        return state, company

    def test_presidency_does_not_transfer_below_threshold(self):
        state, company = self.setup_company()
        a, b = state.players

        company.buy(a, StockPurchaseSource.IPO, STOCK_PRESIDENT_CERTIFICATE)
        company.setPresident(a)

        company.buy(b, StockPurchaseSource.IPO, STOCK_CERTIFICATE)
        company.checkPresident()
        self.assertEqual(company.president, a)

        company.sell(a, STOCK_PRESIDENT_CERTIFICATE)
        company.checkPresident()
        self.assertEqual(company.president, a)

    def test_presidency_transfers_at_threshold(self):
        state, company = self.setup_company()
        a, b = state.players

        company.buy(a, StockPurchaseSource.IPO, STOCK_PRESIDENT_CERTIFICATE)
        company.setPresident(a)

        company.buy(b, StockPurchaseSource.IPO, STOCK_CERTIFICATE)
        company.checkPresident()
        self.assertEqual(company.president, a)

        company.buy(b, StockPurchaseSource.IPO, STOCK_CERTIFICATE * 2)
        company.checkPresident()
        self.assertEqual(company.president, b)

    def test_presidency_transfers_to_largest_holder(self):
        state, company = self.setup_company()
        a, b = state.players
        c = fake_player("C", 10000, 3)
        state.players.append(c)

        company.buy(a, StockPurchaseSource.IPO, STOCK_PRESIDENT_CERTIFICATE)
        company.setPresident(a)

        company.buy(b, StockPurchaseSource.IPO, STOCK_CERTIFICATE * 2)
        company.buy(c, StockPurchaseSource.IPO, STOCK_CERTIFICATE * 3)

        company.checkPresident()
        self.assertEqual(company.president, c)


class StockRoundNoBuyAfterSellTests(unittest.TestCase):
    def sell_move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "SELL",
            "player_id": "A",
            "for_sale_raw": [["ABC", 20]]
        })
        return StockRoundMove.fromMove(Move.fromMessage(msg))

    def buy_move(self) -> StockRoundMove:
        msg = json.dumps({
            "move_type": "BUY",
            "player_id": "A",
            "public_company_id": "ABC",
            "source": "BANK",
            "ipo_price": 72
        })
        return StockRoundMove.fromMove(Move.fromMessage(msg))

    def state(self) -> MutableGameState:
        game_context = MutableGameState()
        game_context.players = [fake_player("A", 10000, 1), fake_player("B", 10000, 2)]
        game_context.public_companies = [fake_public_company("ABC")]
        game_context.stock_round_count = 2
        game_context.sales = [{}, {}, {}]
        game_context.purchases = [{}, {}, {}]
        return game_context

    def initial_setup_company(self, company, owners, initial_price):
        company.setInitialPrice(initial_price)
        for owner, amount in owners:
            company.buy(owner, StockPurchaseSource.IPO, amount)

    def test_cannot_rebuy_same_round(self):
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [
            (state.players[0], 30), (state.players[1], 30)
        ], 72)

        sell = self.sell_move()
        buy = self.buy_move()
        sr = StockRound()
        self.assertTrue(sr.run(sell, state), sr.errors())
        self.assertFalse(sr.run(buy, state), sr.errors())
        self.assertIn("You can't buy from a company you sold this round", sr.errors()[0])

    def test_can_buy_next_round(self):
        state = self.state()
        self.initial_setup_company(state.public_companies[0], [
            (state.players[0], 30), (state.players[1], 30)
        ], 72)

        sell = self.sell_move()
        sr = StockRound()
        self.assertTrue(sr.run(sell, state), sr.errors())

        # end of stock round
        StockRound.onComplete(state)
        state.stock_round_count += 1
        state.sales.append({})
        state.purchases.append({})

        buy = self.buy_move()
        sr2 = StockRound()
        self.assertTrue(sr2.run(buy, state), sr2.errors())


if __name__ == "__main__":
    unittest.main()

