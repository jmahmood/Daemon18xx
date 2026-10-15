"""Pure Python, JSON state/action API for the standard Shikoku 1889 rules.

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
    best_routes,
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
    "best_routes",
    "check_invariants",
]
