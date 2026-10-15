"""Tests for game phase transition validation."""

import unittest
from app.phase_validation import PhaseValidator, validate_transition, PhaseTransition
from app.state import Game


class PhaseValidatorTests(unittest.TestCase):
    """Tests for PhaseValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = PhaseValidator(variant="1830")

    def test_initial_state(self):
        """Validator starts in initial state."""
        self.assertIsNone(self.validator.current_phase)
        self.assertEqual(self.validator.stock_round_count, 0)
        self.assertEqual(self.validator.operating_round_count, 0)
        self.assertEqual(len(self.validator.transition_history), 0)

    def test_valid_initial_transition(self):
        """Can transition from None to initial phase."""
        self.assertTrue(self.validator.can_transition(None, "BuyPrivateCompany"))

    def test_invalid_initial_transition(self):
        """Cannot transition from None to non-initial phase."""
        self.assertFalse(self.validator.can_transition(None, "OperatingRound"))

    def test_auction_to_stock_round(self):
        """Can transition from auction to stock round."""
        self.assertTrue(
            self.validator.can_transition("BuyPrivateCompany", "StockRound")
        )

    def test_auction_to_bidding(self):
        """Can transition from auction to bidding."""
        self.assertTrue(
            self.validator.can_transition("BuyPrivateCompany", "BiddingForPrivateCompany")
        )

    def test_stock_round_to_operating_round(self):
        """Can transition from stock round to operating round."""
        self.assertTrue(
            self.validator.can_transition("StockRound", "OperatingRound")
        )

    def test_operating_round_to_stock_round(self):
        """Can transition from operating round to stock round."""
        self.assertTrue(
            self.validator.can_transition("OperatingRound", "StockRound")
        )

    def test_operating_round_to_operating_round(self):
        """Can transition between operating rounds (up to limit)."""
        self.assertTrue(
            self.validator.can_transition("OperatingRound", "OperatingRound")
        )

    def test_invalid_transition_stock_to_auction(self):
        """Cannot transition from stock round to initial auction."""
        self.assertFalse(
            self.validator.can_transition("StockRound", "BuyPrivateCompany")
        )

    def test_invalid_transition_operating_to_bidding(self):
        """Cannot transition from operating round to bidding."""
        self.assertFalse(
            self.validator.can_transition("OperatingRound", "BiddingForPrivateCompany")
        )

    def test_record_transition_updates_phase(self):
        """Recording transition updates current phase."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.assertEqual(self.validator.current_phase, "BuyPrivateCompany")

    def test_record_transition_adds_history(self):
        """Recording transition adds to history."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.assertEqual(len(self.validator.transition_history), 1)

        transition = self.validator.transition_history[0]
        self.assertEqual(transition.from_phase, "INIT")
        self.assertEqual(transition.to_phase, "BuyPrivateCompany")

    def test_stock_round_counter(self):
        """Stock round counter increments correctly."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")
        self.assertEqual(self.validator.stock_round_count, 1)

        self.validator.record_transition("StockRound", "OperatingRound")
        self.validator.record_transition("OperatingRound", "StockRound")
        self.assertEqual(self.validator.stock_round_count, 2)

    def test_operating_round_counter(self):
        """Operating round counter increments correctly."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")
        self.validator.record_transition("StockRound", "OperatingRound")
        self.assertEqual(self.validator.operating_round_count, 1)

        self.validator.record_transition("OperatingRound", "OperatingRound")
        self.assertEqual(self.validator.operating_round_count, 2)

    def test_operating_rounds_this_set_resets(self):
        """Operating round set counter resets after stock round."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")
        self.validator.record_transition("StockRound", "OperatingRound")
        self.assertEqual(self.validator.operating_rounds_this_set, 1)

        self.validator.record_transition("OperatingRound", "OperatingRound")
        self.assertEqual(self.validator.operating_rounds_this_set, 2)

        # New stock round resets
        self.validator.record_transition("OperatingRound", "StockRound")
        self.assertEqual(self.validator.operating_rounds_this_set, 0)

    def test_max_operating_rounds_per_set(self):
        """Cannot exceed max operating rounds per set."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")

        # Add max allowed operating rounds (3 for 1830)
        for i in range(3):
            self.assertTrue(
                self.validator.can_transition("OperatingRound", "OperatingRound")
            )
            self.validator.record_transition("StockRound" if i == 0 else "OperatingRound", "OperatingRound")

        # Next one should fail
        self.assertFalse(
            self.validator.can_transition("OperatingRound", "OperatingRound")
        )

    def test_get_valid_next_phases(self):
        """Can query valid next phases."""
        valid = self.validator.get_valid_next_phases("StockRound")
        self.assertIn("OperatingRound", valid)
        self.assertIn("StockRound", valid)
        self.assertNotIn("BuyPrivateCompany", valid)

    def test_get_phase_summary(self):
        """Can get phase summary."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")

        summary = self.validator.get_phase_summary()
        self.assertEqual(summary['current_phase'], "StockRound")
        self.assertEqual(summary['stock_round_count'], 1)
        self.assertEqual(summary['total_transitions'], 2)

    def test_reset(self):
        """Reset clears all state."""
        self.validator.record_transition(None, "BuyPrivateCompany")
        self.validator.record_transition("BuyPrivateCompany", "StockRound")

        self.validator.reset()

        self.assertIsNone(self.validator.current_phase)
        self.assertEqual(self.validator.stock_round_count, 0)
        self.assertEqual(len(self.validator.transition_history), 0)

    def test_validate_and_record_valid(self):
        """validate_and_record works for valid transition."""
        result = self.validator.validate_and_record(None, "BuyPrivateCompany")
        self.assertTrue(result)
        self.assertEqual(self.validator.current_phase, "BuyPrivateCompany")

    def test_validate_and_record_invalid(self):
        """validate_and_record rejects invalid transition."""
        result = self.validator.validate_and_record("StockRound", "BuyPrivateCompany")
        self.assertFalse(result)
        # Phase should not have changed
        self.assertIsNone(self.validator.current_phase)


class StandaloneValidationTests(unittest.TestCase):
    """Tests for standalone validation function."""

    def test_valid_transition_returns_true(self):
        """Valid transition returns True with no error."""
        valid, error = validate_transition("StockRound", "OperatingRound")
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_invalid_transition_returns_false(self):
        """Invalid transition returns False with error message."""
        valid, error = validate_transition("StockRound", "BuyPrivateCompany")
        self.assertFalse(valid)
        self.assertIsNotNone(error)
        self.assertIn("Invalid transition", error)


class GameIntegrationTests(unittest.TestCase):
    """Tests for phase validation integrated with Game class."""

    def test_game_has_phase_validator(self):
        """Game instance has a phase validator."""
        game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')
        self.assertIsNotNone(game.phase_validator)
        self.assertIsInstance(game.phase_validator, PhaseValidator)

    def test_game_initial_phase_recorded(self):
        """Game initial phase is recorded in validator."""
        game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')

        # Initial setMinigame call should be recorded
        self.assertIsNotNone(game.phase_validator.current_phase)

    def test_game_phase_transitions_validated(self):
        """Game phase transitions go through validator."""
        game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')

        # Record initial state
        initial_transitions = len(game.phase_validator.transition_history)

        # Set to stock round (valid transition)
        game.setMinigame("StockRound")

        # Should have recorded the transition
        self.assertEqual(
            len(game.phase_validator.transition_history),
            initial_transitions + 1
        )

    def test_invalid_phase_transition_logged(self):
        """Invalid phase transitions are logged but allowed."""
        game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')

        # Try an invalid transition (this won't raise but will log)
        # StockRound -> BiddingForPrivateCompany is invalid
        game.setMinigame("StockRound")
        game.setMinigame("BiddingForPrivateCompany")

        # Transition still happens (non-strict mode)
        self.assertEqual(game.minigame_class, "BiddingForPrivateCompany")

    def test_variant_specific_limits(self):
        """Different variants have different operating round limits."""
        game_1830 = Game.start(['Alice', 'Bob'], variant='1830')
        game_1889 = Game.start(['Alice', 'Bob'], variant='1889')

        # 1830 allows 3 operating rounds per set
        self.assertEqual(game_1830.phase_validator.max_operating_rounds_per_set, 3)

        # 1889 allows 2 operating rounds per set
        self.assertEqual(game_1889.phase_validator.max_operating_rounds_per_set, 2)


class PhaseSequenceTests(unittest.TestCase):
    """Tests for realistic phase sequences."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = PhaseValidator(variant="1830")

    def test_typical_game_sequence(self):
        """Test a typical game phase sequence."""
        # Initial auction
        self.assertTrue(self.validator.validate_and_record(None, "BuyPrivateCompany"))

        # First stock round
        self.assertTrue(self.validator.validate_and_record("BuyPrivateCompany", "StockRound"))
        self.assertEqual(self.validator.stock_round_count, 1)

        # First operating round set (3 rounds for 1830)
        self.assertTrue(self.validator.validate_and_record("StockRound", "OperatingRound"))
        self.assertTrue(self.validator.validate_and_record("OperatingRound", "OperatingRound"))
        self.assertTrue(self.validator.validate_and_record("OperatingRound", "OperatingRound"))
        self.assertEqual(self.validator.operating_round_count, 3)

        # Second stock round
        self.assertTrue(self.validator.validate_and_record("OperatingRound", "StockRound"))
        self.assertEqual(self.validator.stock_round_count, 2)
        self.assertEqual(self.validator.operating_rounds_this_set, 0)  # Reset

        # Second operating round set
        self.assertTrue(self.validator.validate_and_record("StockRound", "OperatingRound"))
        self.assertEqual(self.validator.operating_rounds_this_set, 1)

    def test_auction_during_game(self):
        """Test mid-game auction phase."""
        self.validator.validate_and_record(None, "BuyPrivateCompany")
        self.validator.validate_and_record("BuyPrivateCompany", "StockRound")

        # Mid-game auction can happen during stock round
        self.assertTrue(self.validator.validate_and_record("StockRound", "Auction"))
        self.assertTrue(self.validator.validate_and_record("Auction", "StockRound"))

    def test_bidding_phase_flow(self):
        """Test bidding phase transitions."""
        self.validator.validate_and_record(None, "BuyPrivateCompany")

        # Can go to bidding
        self.assertTrue(
            self.validator.validate_and_record("BuyPrivateCompany", "BiddingForPrivateCompany")
        )

        # Can return to buy
        self.assertTrue(
            self.validator.validate_and_record("BiddingForPrivateCompany", "BuyPrivateCompany")
        )

        # Or can go directly to stock round
        self.assertTrue(
            self.validator.validate_and_record("BuyPrivateCompany", "BiddingForPrivateCompany")
        )
        self.assertTrue(
            self.validator.validate_and_record("BiddingForPrivateCompany", "StockRound")
        )


if __name__ == '__main__':
    unittest.main()
