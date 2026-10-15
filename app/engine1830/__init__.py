"""Pure Python, JSON state/action API for the uploaded 1830 rules.

``new_game`` and ``apply_action`` never mutate caller-owned state.
"""

from .engine import (
    new_game,
    migrate_state,
    apply_action,
    legal_actions,
    scores,
    validate_state,
    replay,
    check_invariants,
)
from .errors import RuleError

__all__ = [
    "new_game",
    "migrate_state",
    "apply_action",
    "legal_actions",
    "scores",
    "validate_state",
    "RuleError",
    "replay",
    "check_invariants",
]
