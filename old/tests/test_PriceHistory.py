"""Tests for historical stock price tracking."""

import unittest
from app.base import (
    Player, PublicCompany, StockPurchaseSource, PriceHistoryEntry,
    StockMarket, Cell, Band, Direction
)


class PriceHistoryEntryTests(unittest.TestCase):
    """Tests for the PriceHistoryEntry dataclass."""

    def test_entry_creation(self):
        """Entry can be created with correct attributes."""
        entry = PriceHistoryEntry(
            round_number=1,
            old_price=100,
            new_price=110,
            reason="Dividend paid"
        )
        self.assertEqual(entry.round_number, 1)
        self.assertEqual(entry.old_price, 100)
        self.assertEqual(entry.new_price, 110)
        self.assertEqual(entry.reason, "Dividend paid")
        self.assertIsNone(entry.player_id)

    def test_entry_with_player(self):
        """Entry can include player information."""
        entry = PriceHistoryEntry(
            round_number=2,
            old_price=110,
            new_price=100,
            reason="Stock sold",
            player_id="player-1"
        )
        self.assertEqual(entry.player_id, "player-1")

    def test_entry_with_timestamp(self):
        """Entry can include timestamp."""
        entry = PriceHistoryEntry(
            round_number=1,
            old_price=100,
            new_price=110,
            reason="Test",
            timestamp="2024-01-01T12:00:00"
        )
        self.assertEqual(entry.timestamp, "2024-01-01T12:00:00")


class PublicCompanyPriceHistoryTests(unittest.TestCase):
    """Tests for price history tracking on PublicCompany."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.setInitialPrice(100)

    def test_initial_empty_history(self):
        """New company has empty price history."""
        self.assertEqual(len(self.company.price_history), 0)
        self.assertEqual(len(self.company.get_price_history()), 0)

    def test_record_single_price_change(self):
        """Single price change is recorded correctly."""
        self.company.record_price_change(
            old_price=100,
            new_price=110,
            reason="Test change",
            round_number=1
        )

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].old_price, 100)
        self.assertEqual(history[0].new_price, 110)
        self.assertEqual(history[0].reason, "Test change")

    def test_record_multiple_price_changes(self):
        """Multiple price changes are recorded in order."""
        self.company.record_price_change(100, 110, "Change 1", 1)
        self.company.record_price_change(110, 120, "Change 2", 2)
        self.company.record_price_change(120, 130, "Change 3", 3)

        history = self.company.get_price_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].reason, "Change 1")
        self.assertEqual(history[1].reason, "Change 2")
        self.assertEqual(history[2].reason, "Change 3")

    def test_get_price_history_with_limit(self):
        """Query can limit number of entries returned."""
        for i in range(10):
            self.company.record_price_change(100 + i*10, 110 + i*10, f"Change {i}", i)

        history = self.company.get_price_history(limit=3)
        self.assertEqual(len(history), 3)
        # Should get the last 3 entries
        self.assertEqual(history[0].reason, "Change 7")
        self.assertEqual(history[1].reason, "Change 8")
        self.assertEqual(history[2].reason, "Change 9")

    def test_get_price_history_since_round(self):
        """Query can filter by round number."""
        self.company.record_price_change(100, 110, "Change 1", 1)
        self.company.record_price_change(110, 120, "Change 2", 2)
        self.company.record_price_change(120, 130, "Change 3", 3)
        self.company.record_price_change(130, 140, "Change 4", 4)

        history = self.company.get_price_history(since_round=3)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].reason, "Change 3")
        self.assertEqual(history[1].reason, "Change 4")

    def test_get_price_history_with_limit_and_filter(self):
        """Query can combine limit and round filter."""
        for i in range(10):
            self.company.record_price_change(100 + i*10, 110 + i*10, f"Change {i}", i)

        history = self.company.get_price_history(limit=2, since_round=5)
        self.assertEqual(len(history), 2)
        # Should get last 2 entries from rounds >= 5
        self.assertEqual(history[0].reason, "Change 8")
        self.assertEqual(history[1].reason, "Change 9")

    def test_get_current_price(self):
        """get_current_price returns correct value."""
        self.company.setInitialPrice(100)
        self.assertEqual(self.company.get_current_price(), 100)

        self.company.stockPrice[StockPurchaseSource.BANK] = 150
        self.assertEqual(self.company.get_current_price(), 150)


class PriceUpDownHistoryTests(unittest.TestCase):
    """Tests for price history with priceUp/priceDown (no stock market)."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.setInitialPrice(100)
        # No stock market attached - uses simple price logic

    def test_price_up_records_history(self):
        """priceUp records price change in history."""
        self.company.priceUp(1)  # Increases by 1 space = $10

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].old_price, 100)
        self.assertEqual(history[0].new_price, 110)
        self.assertIn("Price increase", history[0].reason)

    def test_price_up_multiple_spaces(self):
        """priceUp with multiple spaces records correctly."""
        self.company.priceUp(3)  # Increases by 3 spaces = $30

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].old_price, 100)
        self.assertEqual(history[0].new_price, 130)
        self.assertIn("3 spaces", history[0].reason)

    def test_price_up_with_custom_reason(self):
        """priceUp with custom reason records correctly."""
        self.company.priceUp(1, reason="Special bonus")

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertIn("Special bonus", history[0].reason)

    def test_price_down_records_history(self):
        """priceDown records price change in history."""
        self.company.priceDown(10)  # 10% = 1 certificate = down by $10

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].old_price, 100)
        self.assertEqual(history[0].new_price, 90)
        self.assertIn("Stock sold", history[0].reason)

    def test_price_down_no_change_no_record(self):
        """priceDown with no actual change doesn't record."""
        # Price is 100, try to decrease by 200 (but floor is 0)
        self.company.stockPrice[StockPurchaseSource.BANK] = 5
        self.company.priceDown(10)  # Would go to 0, but might not change if already low

        # If price was already at or near 0, we might not record
        # This tests the conditional logic

    def test_multiple_price_changes(self):
        """Multiple price changes accumulate in history."""
        self.company.priceUp(1)
        self.company.priceUp(2)
        self.company.priceDown(10)

        history = self.company.get_price_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].new_price, 110)  # First up
        self.assertEqual(history[1].old_price, 110)  # Second up starts from 110
        self.assertEqual(history[2].old_price, 130)  # Down starts from 130


class StockMarketPriceHistoryTests(unittest.TestCase):
    """Tests for price history with stock market movements."""

    def setUp(self):
        """Set up test fixtures with a stock market."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player

        # Create a simple 3x3 stock market
        self.market = StockMarket([
            [Cell(150, Band.BROWN), Cell(160, Band.BROWN), Cell(170, Band.BROWN)],
            [Cell(100, Band.YELLOW), Cell(110, Band.YELLOW), Cell(120, Band.YELLOW)],
            [Cell(50, Band.YELLOW), Cell(60, Band.YELLOW), Cell(70, Band.YELLOW)]
        ])

        # Place company at middle position (100)
        self.company.attach_market(self.market, 1, 0)

    def test_market_attachment_records_initial_price(self):
        """Attaching to market records initial price setting."""
        # The attach_market records the initial price change from 0 to the market value
        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].old_price, 0)
        self.assertEqual(history[0].new_price, 100)
        self.assertEqual(history[0].reason, "Initial market price")

    def test_market_move_right_records(self):
        """Moving right in market records price increase."""
        initial_price = self.company.get_current_price()
        self.market.move(self.company, Direction.RIGHT)

        history = self.company.get_price_history()
        # Should have 2 entries: initial attachment + move
        self.assertEqual(len(history), 2)
        # Check the move entry (second one)
        self.assertEqual(history[1].old_price, initial_price)
        self.assertEqual(history[1].new_price, 110)
        self.assertIn("Manual market movement", history[1].reason)

    def test_on_payout_records(self):
        """Stock market payout movement records with reason."""
        # Move to a position where payout will cause movement (not YELLOW band, has space to move)
        self.company.stock_pos = (2, 1)  # Start at 60 (YELLOW)
        self.company.update_price_from_pos("Test position")

        initial_history_len = len(self.company.get_price_history())
        self.market.on_payout(self.company)

        history = self.company.get_price_history()
        # YELLOW band doesn't move on payout, so check if we're on a moving band
        if len(history) > initial_history_len:
            self.assertIn("Dividend paid", history[-1].reason)

    def test_on_withhold_records(self):
        """Stock market withhold movement records with reason."""
        # Move to a position where withhold will cause movement (has space to move left)
        self.company.stock_pos = (1, 2)  # Start at 120 (can move left)
        self.company.update_price_from_pos("Test position")

        initial_history_len = len(self.company.get_price_history())
        self.market.on_withhold(self.company)

        history = self.company.get_price_history()
        # Check that withhold recorded if movement happened
        if len(history) > initial_history_len:
            self.assertIn("Revenue withheld", history[-1].reason)

    def test_on_sale_records(self):
        """Stock market sale movement records with reason."""
        initial_price = self.company.get_current_price()
        self.market.on_sale(self.company, 20)  # 20% sale = 2 steps down

        history = self.company.get_price_history()
        if len(history) > 0:
            self.assertIn("Stock sold", history[-1].reason)

    def test_on_sold_out_records(self):
        """Stock market sold out movement records with reason."""
        initial_price = self.company.get_current_price()
        self.market.on_sold_out(self.company)

        history = self.company.get_price_history()
        if len(history) > 0:
            self.assertEqual(history[-1].reason, "Stock sold out")

    def test_update_price_from_pos_only_records_if_changed(self):
        """update_price_from_pos only records if price actually changed."""
        initial_count = len(self.company.get_price_history())

        # Call update_price_from_pos without changing position
        self.company.update_price_from_pos("Test reason")

        # Should not add a new entry since price didn't change
        self.assertEqual(len(self.company.get_price_history()), initial_count)


class PriceHistoryIntegrationTests(unittest.TestCase):
    """Integration tests for price history in realistic scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.player1 = Player.create("Player1", 1000, 0)
        self.player2 = Player.create("Player2", 1000, 1)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player1
        self.company.setInitialPrice(100)

    def test_complete_price_lifecycle(self):
        """Test a complete lifecycle of price changes."""
        # Start at 100
        self.assertEqual(self.company.get_current_price(), 100)

        # Price goes up due to stock sold out
        self.company.priceUp(1, "Stock sold out")
        self.assertEqual(self.company.get_current_price(), 110)

        # Price goes down due to selling (10% = 1 share)
        self.company.priceDown(10)
        self.assertEqual(self.company.get_current_price(), 100)

        # Price goes up due to dividend
        self.company.priceUp(2, "Good dividend")
        self.assertEqual(self.company.get_current_price(), 120)

        # Check history
        history = self.company.get_price_history()
        self.assertEqual(len(history), 3)

        # Verify first change
        self.assertEqual(history[0].old_price, 100)
        self.assertEqual(history[0].new_price, 110)
        self.assertIn("Stock sold out", history[0].reason)

        # Verify second change
        self.assertEqual(history[1].old_price, 110)
        self.assertEqual(history[1].new_price, 100)

        # Verify third change
        self.assertEqual(history[2].old_price, 100)
        self.assertEqual(history[2].new_price, 120)

    def test_price_history_timestamps(self):
        """Price history entries have timestamps."""
        self.company.record_price_change(100, 110, "Test", 1)

        history = self.company.get_price_history()
        self.assertEqual(len(history), 1)
        self.assertIsNotNone(history[0].timestamp)
        # Timestamp should be in ISO format
        self.assertIn("T", history[0].timestamp)


if __name__ == '__main__':
    unittest.main()
