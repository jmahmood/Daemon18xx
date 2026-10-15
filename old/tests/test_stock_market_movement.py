import unittest

from app.base import StockMarket, Cell, Band, Direction
from app.unittests.test_StockRoundMinigame import fake_public_company


class StockMarketMovementTests(unittest.TestCase):
    def setUp(self):
        grid = []
        for r in range(5):
            row = []
            for c in range(12):
                band = Band.WHITE
                arrow = None
                if (r, c) == (2, 2):
                    band = Band.YELLOW
                if (r, c) == (1, 1):
                    band = Band.BROWN
                    arrow = Direction.UP_RIGHT
                row.append(Cell(10 * (c + 1), band, arrow))
            grid.append(row)
        self.market = StockMarket(grid)

    def test_sale_multiple_rows_down(self):
        company = fake_public_company("PRR")
        company.attach_market(self.market, 3, 5)
        company.priceDown(30)
        self.assertEqual(company.stock_pos, (4, 5))

    def test_withhold_yellow_moves_left(self):
        company = fake_public_company("NYC")
        company.attach_market(self.market, 2, 2)
        self.market.on_withhold(company)
        self.assertEqual(company.stock_pos, (2, 1))

    def test_dividend_brown_up_right(self):
        company = fake_public_company("B&O")
        company.attach_market(self.market, 1, 1)
        self.market.on_payout(company)
        self.assertEqual(company.stock_pos, (0, 2))

    def test_sold_out_bump_ignored_top(self):
        company = fake_public_company("ERIE")
        company.attach_market(self.market, 0, 5)
        self.market.on_sold_out(company)
        self.assertEqual(company.stock_pos, (0, 5))

    def test_left_edge_withhold_ignored(self):
        company = fake_public_company("C&O")
        company.attach_market(self.market, 2, 0)
        self.market.on_withhold(company)
        self.assertEqual(company.stock_pos, (2, 0))


if __name__ == "__main__":
    unittest.main()
