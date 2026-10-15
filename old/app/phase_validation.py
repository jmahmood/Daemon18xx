"""Game phase transition validation and state machine.

This module enforces valid phase transitions and tracks game progression
through the various game phases (Initial Auction → Stock Rounds → Operating Rounds).

Phases:
- BuyPrivateCompany: Initial private company auction
- BiddingForPrivateCompany: Bidding on a specific private company
- StockRound: Players buy/sell stock
- Auction: Mid-game private company auction
- OperatingRound: Companies operate trains and pay dividends

Usage:
    from app.phase_validation import PhaseValidator, validate_transition

    validator = PhaseValidator()
    if validator.can_transition("StockRound", "OperatingRound"):
        # Proceed with transition
        validator.record_transition("StockRound", "OperatingRound")
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PhaseTransition:
    """Record of a phase transition."""
    from_phase: str
    to_phase: str
    timestamp: str
    stock_round_count: int = 0
    operating_round_count: int = 0


class PhaseValidator:
    """Validates and tracks game phase transitions."""

    # Valid phase transitions (from_phase -> list of valid to_phases)
    VALID_TRANSITIONS: Dict[str, Set[str]] = {
        # Initial auction can go to stock round or bidding
        "BuyPrivateCompany": {"StockRound", "BiddingForPrivateCompany"},

        # Bidding goes back to initial auction or to stock round
        "BiddingForPrivateCompany": {"BuyPrivateCompany", "StockRound"},

        # Stock round goes to operating round or another stock round (rare)
        "StockRound": {"OperatingRound", "StockRound", "Auction"},

        # Mid-game auction returns to stock round
        "Auction": {"StockRound"},

        # Operating round goes back to stock round or to another operating round
        "OperatingRound": {"StockRound", "OperatingRound"},
    }

    # Initial phases (game can start here)
    INITIAL_PHASES = {"BuyPrivateCompany"}

    # Terminal phases (game can end here)
    TERMINAL_PHASES = {"OperatingRound", "StockRound"}

    def __init__(self, variant: str = "1830"):
        """Initialize phase validator.

        Args:
            variant: Game variant (affects operating round limits)
        """
        self.variant = variant
        self.transition_history: List[PhaseTransition] = []
        self.current_phase: Optional[str] = None
        self.stock_round_count: int = 0
        self.operating_round_count: int = 0
        self.operating_rounds_this_set: int = 0  # Resets after each stock round

        # Variant-specific rules
        self.max_operating_rounds_per_set = self._get_max_operating_rounds(variant)

    def _get_max_operating_rounds(self, variant: str) -> int:
        """Get maximum operating rounds per set for variant.

        Args:
            variant: Game variant

        Returns:
            Maximum number of operating rounds before stock round
        """
        # Most 18XX games have 1-3 operating rounds per stock round
        # This varies by phase in the game
        variant_limits = {
            "1830": 3,
            "1846": 3,
            "1889": 2,
            "1817": 4,  # 1817 can have more
        }
        return variant_limits.get(variant, 3)

    def can_transition(self, from_phase: str, to_phase: str) -> bool:
        """Check if transition is valid.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition is allowed
        """
        # Allow initial phase to be set
        if from_phase is None and to_phase in self.INITIAL_PHASES:
            return True

        # Check if transition is in valid transitions map
        if from_phase not in self.VALID_TRANSITIONS:
            logger.warning(
                f"Unknown phase: {from_phase}",
                extra={'from_phase': from_phase, 'to_phase': to_phase}
            )
            return False

        valid_targets = self.VALID_TRANSITIONS[from_phase]
        if to_phase not in valid_targets:
            logger.warning(
                f"Invalid phase transition",
                extra={
                    'from_phase': from_phase,
                    'to_phase': to_phase,
                    'valid_targets': list(valid_targets)
                }
            )
            return False

        # Additional validation for operating round limits
        if from_phase == "OperatingRound" and to_phase == "OperatingRound":
            if self.operating_rounds_this_set >= self.max_operating_rounds_per_set:
                logger.warning(
                    f"Too many operating rounds in this set",
                    extra={
                        'current_count': self.operating_rounds_this_set,
                        'max_allowed': self.max_operating_rounds_per_set
                    }
                )
                return False

        return True

    def record_transition(self, from_phase: Optional[str], to_phase: str) -> None:
        """Record a phase transition.

        Args:
            from_phase: Previous phase (None if initial)
            to_phase: New phase
        """
        # Update counters
        if to_phase == "StockRound":
            self.stock_round_count += 1
            self.operating_rounds_this_set = 0  # Reset for new set

        if to_phase == "OperatingRound":
            self.operating_round_count += 1
            self.operating_rounds_this_set += 1

        # Record transition
        transition = PhaseTransition(
            from_phase=from_phase or "INIT",
            to_phase=to_phase,
            timestamp=datetime.now().isoformat(),
            stock_round_count=self.stock_round_count,
            operating_round_count=self.operating_round_count
        )
        self.transition_history.append(transition)
        self.current_phase = to_phase

        logger.info(
            f"Phase transition recorded",
            extra={
                'from_phase': from_phase,
                'to_phase': to_phase,
                'stock_rounds': self.stock_round_count,
                'operating_rounds': self.operating_round_count
            }
        )

    def validate_and_record(self, from_phase: Optional[str], to_phase: str) -> bool:
        """Validate and record a phase transition.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition is valid and recorded
        """
        if self.can_transition(from_phase, to_phase):
            self.record_transition(from_phase, to_phase)
            return True
        return False

    def get_valid_next_phases(self, from_phase: str) -> Set[str]:
        """Get all valid phases that can follow from_phase.

        Args:
            from_phase: Current phase

        Returns:
            Set of valid next phases
        """
        return self.VALID_TRANSITIONS.get(from_phase, set())

    def get_transition_history(self) -> List[PhaseTransition]:
        """Get full transition history."""
        return self.transition_history

    def get_phase_summary(self) -> Dict[str, int]:
        """Get summary of phase counts.

        Returns:
            Dictionary with phase statistics
        """
        return {
            'current_phase': self.current_phase,
            'stock_round_count': self.stock_round_count,
            'operating_round_count': self.operating_round_count,
            'operating_rounds_this_set': self.operating_rounds_this_set,
            'total_transitions': len(self.transition_history)
        }

    def reset(self) -> None:
        """Reset validator to initial state."""
        self.transition_history.clear()
        self.current_phase = None
        self.stock_round_count = 0
        self.operating_round_count = 0
        self.operating_rounds_this_set = 0


def validate_transition(from_phase: str, to_phase: str, variant: str = "1830") -> Tuple[bool, Optional[str]]:
    """Validate a phase transition (standalone function).

    Args:
        from_phase: Current phase
        to_phase: Target phase
        variant: Game variant

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = PhaseValidator(variant)
    validator.current_phase = from_phase

    if validator.can_transition(from_phase, to_phase):
        return True, None

    valid_phases = validator.get_valid_next_phases(from_phase)
    error_msg = f"Invalid transition from '{from_phase}' to '{to_phase}'. Valid: {valid_phases}"
    return False, error_msg
