import unittest

from app.base import StockMarket, Cell, Band, Direction, MutableGameState, StockPurchaseSource
from app.state import Game
from app.unittests.test_StockRoundMinigame import fake_public_company
from app.unittests.test_OperatingRoundMinigame import fake_player

class OperatingOrderAndDividendTests(unittest.TestCase):
    def setUp(self):
        grid = []
        for r in range(5):
            row = []
            for c in range(12):
                band = Band.WHITE
                arrow = None
                if (r, c) == (1, 1):
                    band = Band.BROWN
                    arrow = Direction.UP_RIGHT
                if (r, c) == (3, 3):
                    arrow = Direction.DOWN_LEFT
                row.append(Cell(10 * (c + 1), band, arrow))
            grid.append(row)
        self.market = StockMarket(grid)

    def make_game(self, companies):
        game = Game()
        game.config = type("cfg", (), {"STOCK_MARKET": self.market})
        game.state = MutableGameState()
        game.state.public_companies = companies
        return game

    def test_operating_order_sort_stable(self):
        bo = fake_public_company("BO")
        prr = fake_public_company("PRR")
        bo.attach_market(self.market, 1, 10)
        prr.attach_market(self.market, 2, 10)
        bo._floated = prr._floated = True
        game = self.make_game([bo, prr])
        self.assertEqual(game.sort_operating_order(), ["BO", "PRR"])
        self.assertEqual(game.sort_operating_order(), ["BO", "PRR"])

    def test_pay_right_edge_ignored(self):
        corp = fake_public_company("NYC")
        corp.attach_market(self.market, 2, self.market.max_col())
        corp.owners = {fake_player("A"): 100}
        corp._income = 10
        corp.payDividends()
        self.assertEqual(corp.stock_pos, (2, self.market.max_col()))

    def test_withhold_left_edge_ignored(self):
        corp = fake_public_company("NYNH")
        corp.attach_market(self.market, 2, 0)
        corp._income = 10
        corp.incomeToCash()
        self.assertEqual(corp.stock_pos, (2, 0))

    def test_receiverless_dividend_moves_left(self):
        corp = fake_public_company("ERIE")
        corp.attach_market(self.market, 2, 5)
        corp._floated = True
        corp.stocks[StockPurchaseSource.BANK] = 100
        corp.stocks[StockPurchaseSource.IPO] = 0
        corp._income = 10
        corp.payDividends()  # all shares in bank pool -> receiverless
        self.assertEqual(corp.stock_pos, (2, 4))

    def test_unsold_ipo_shares_pay_company(self):
        corp = fake_public_company("B&M")
        corp.attach_market(self.market, 2, 5)
        corp._floated = True
        corp.stocks[StockPurchaseSource.IPO] = 50
        player = fake_player("A")
        corp.owners = {player: 50}
        corp._income = 100
        corp.payDividends()
        self.assertEqual(player.cash, 1050)
        self.assertEqual(corp.cash, 50)

    def test_arrow_cells(self):
        pay = fake_public_company("B&O")
        pay.attach_market(self.market, 1, 1)
        pay.owners = {fake_player("A"): 100}
        pay._income = 10
        pay.payDividends()
        self.assertEqual(pay.stock_pos, (0, 2))

        withd = fake_public_company("PRR")
        withd.attach_market(self.market, 3, 3)
        withd._income = 10
        withd.incomeToCash()
        self.assertEqual(withd.stock_pos, (4, 2))

if __name__ == "__main__":
    unittest.main()
