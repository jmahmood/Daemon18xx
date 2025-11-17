"""Tests for logging configuration and game history."""

import unittest
import json
import tempfile
import os
from io import StringIO
import logging

from app.logging_config import setup_logging, get_logger, is_debug_mode, PerformanceTimer
from app.game_history import GameHistory, load_history_from_json
from app.base import Player, PublicCompany, MutableGameState


class LoggingConfigTests(unittest.TestCase):
    """Tests for logging configuration."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset logging to avoid interference between tests
        logging.getLogger().handlers.clear()

    def test_setup_logging_basic(self):
        """Logging can be set up with basic configuration."""
        setup_logging(level='INFO', debug_mode=False)
        logger = get_logger(__name__)
        self.assertIsNotNone(logger)

    def test_setup_logging_debug_mode(self):
        """Debug mode can be enabled."""
        setup_logging(level='DEBUG', debug_mode=True)
        self.assertTrue(is_debug_mode())

    def test_setup_logging_with_file(self):
        """Logging can write to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            setup_logging(level='INFO', debug_mode=False, log_file=log_file)
            logger = get_logger(__name__)
            logger.info("Test message")

            # Check that file was created and contains content
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, 'r') as f:
                content = f.read()
                self.assertIn("Test message", content)
        finally:
            if os.path.exists(log_file):
                os.remove(log_file)

    def test_logger_with_context(self):
        """Logger can include context data."""
        setup_logging(level='INFO', debug_mode=False)
        logger = get_logger(__name__)

        # Should not raise exception
        logger.info("Test with context", extra={'player': 'Alice', 'phase': 'StockRound'})

    def test_performance_timer(self):
        """Performance timer tracks operation duration."""
        setup_logging(level='INFO', debug_mode=False)
        logger = get_logger(__name__)

        with PerformanceTimer(logger, "Test operation", player="Alice"):
            pass  # Operation completes successfully

        # If we get here without exception, timer worked


class GameHistoryTests(unittest.TestCase):
    """Tests for game history tracking."""

    def setUp(self):
        """Set up test fixtures."""
        self.history = GameHistory()
        self.history.initialize(variant="1830", players=["Alice", "Bob", "Charlie"])

        self.state = MutableGameState()
        self.player1 = Player.create("Alice", 1000, 0)
        self.player2 = Player.create("Bob", 1000, 1)
        self.state.players = [self.player1, self.player2]

        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.state.public_companies = [self.company]
        self.state.private_companies = []

    def test_history_initialization(self):
        """History can be initialized with game metadata."""
        self.assertEqual(self.history.variant, "1830")
        self.assertEqual(self.history.players, ["Alice", "Bob", "Charlie"])
        self.assertIsNotNone(self.history.game_start_time)

    def test_record_successful_move(self):
        """Successful moves can be recorded."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move = StockRoundMove()
        move.player_id = "Alice"

        self.history.record_move(
            move=move,
            state=self.state,
            success=True,
            phase="StockRound"
        )

        self.assertEqual(self.history.get_move_count(), 1)
        recorded = self.history.moves[0]
        self.assertEqual(recorded['player_id'], "Alice")
        self.assertEqual(recorded['phase'], "StockRound")
        self.assertTrue(recorded['success'])

    def test_record_failed_move(self):
        """Failed moves can be recorded with errors."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move = StockRoundMove()
        move.player_id = "Bob"

        self.history.record_move(
            move=move,
            state=self.state,
            success=False,
            errors=["Insufficient funds", "Invalid action"],
            phase="StockRound"
        )

        self.assertEqual(self.history.get_move_count(), 1)
        recorded = self.history.moves[0]
        self.assertFalse(recorded['success'])
        self.assertEqual(len(recorded['errors']), 2)

    def test_export_to_dict(self):
        """History can be exported as dictionary."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move = StockRoundMove()
        move.player_id = "Alice"
        self.history.record_move(move, self.state, success=True, phase="StockRound")

        data = self.history.export_dict()

        self.assertIn('metadata', data)
        self.assertIn('moves', data)
        self.assertEqual(data['metadata']['variant'], "1830")
        self.assertEqual(data['metadata']['total_moves'], 1)

    def test_export_to_json(self):
        """History can be exported to JSON file."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move = StockRoundMove()
        move.player_id = "Alice"
        self.history.record_move(move, self.state, success=True, phase="StockRound")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_file = f.name

        try:
            self.history.export_json(json_file)
            self.assertTrue(os.path.exists(json_file))

            # Verify JSON is valid
            with open(json_file, 'r') as f:
                data = json.load(f)
                self.assertEqual(data['metadata']['variant'], "1830")
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)

    def test_load_from_json(self):
        """History can be loaded from JSON file."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move = StockRoundMove()
        move.player_id = "Alice"
        self.history.record_move(move, self.state, success=True, phase="StockRound")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_file = f.name

        try:
            self.history.export_json(json_file)
            loaded_history = load_history_from_json(json_file)

            self.assertEqual(loaded_history.variant, "1830")
            self.assertEqual(loaded_history.get_move_count(), 1)
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)

    def test_get_moves_by_player(self):
        """Can filter moves by player."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move1 = StockRoundMove()
        move1.player_id = "Alice"
        self.history.record_move(move1, self.state, success=True, phase="StockRound")

        move2 = StockRoundMove()
        move2.player_id = "Bob"
        self.history.record_move(move2, self.state, success=True, phase="StockRound")

        move3 = StockRoundMove()
        move3.player_id = "Alice"
        self.history.record_move(move3, self.state, success=True, phase="StockRound")

        alice_moves = self.history.get_moves_by_player("Alice")
        self.assertEqual(len(alice_moves), 2)

        bob_moves = self.history.get_moves_by_player("Bob")
        self.assertEqual(len(bob_moves), 1)

    def test_get_moves_by_phase(self):
        """Can filter moves by game phase."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move1 = StockRoundMove()
        move1.player_id = "Alice"
        self.history.record_move(move1, self.state, success=True, phase="StockRound")

        move2 = StockRoundMove()
        move2.player_id = "Bob"
        self.history.record_move(move2, self.state, success=True, phase="OperatingRound")

        stock_moves = self.history.get_moves_by_phase("StockRound")
        self.assertEqual(len(stock_moves), 1)

        op_moves = self.history.get_moves_by_phase("OperatingRound")
        self.assertEqual(len(op_moves), 1)

    def test_get_failed_moves(self):
        """Can retrieve all failed moves."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        move1 = StockRoundMove()
        move1.player_id = "Alice"
        self.history.record_move(move1, self.state, success=True, phase="StockRound")

        move2 = StockRoundMove()
        move2.player_id = "Bob"
        self.history.record_move(move2, self.state, success=False, errors=["Invalid"], phase="StockRound")

        failed = self.history.get_failed_moves()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]['player_id'], "Bob")

    def test_multiple_moves_sequence(self):
        """Move sequence numbers increment correctly."""
        from app.minigames.StockRound.minigame_stockround import StockRoundMove

        for i in range(5):
            move = StockRoundMove()
            move.player_id = f"Player{i}"
            self.history.record_move(move, self.state, success=True, phase="StockRound")

        self.assertEqual(self.history.get_move_count(), 5)

        # Check sequences
        for i, move_record in enumerate(self.history.moves):
            self.assertEqual(move_record['sequence'], i + 1)


if __name__ == '__main__':
    unittest.main()
