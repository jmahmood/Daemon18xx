# Daemon18xx

> **Review status:** The reported 1830 review defects are corrected, including
> loop connectivity and M&H turn control. See [the follow-up validation](docs/1830_FOLLOWUP_REVIEW.md).


A railroad board-game backend. The **1830** implementation follows the
uploaded [rules of play](docs/rules1830.rtf) and is written entirely in Python.
It uses JSON-compatible state and actions, with no dependencies outside the
standard library in the rules engine.

## 1830 engine

```python
from app.engine1830 import new_game, apply_action

state = new_game(['Alice', 'Bob', 'Carol'])
state = apply_action(state, {
    'type': 'buy_private', 'player': 'p1', 'company': 'SV',
})
```

The engine includes the initial auction, stock and operating rounds, all eight
corporations, the complete board and finite tile inventory, private-company
abilities, route validation and revenue, train phases and rusting, emergency
funding, bankruptcy, bank exhaustion and final scoring. Actions are atomic;
rejected moves leave the original state unchanged. Accepted histories can be
replayed deterministically.

- [Engine and API guide](app/engine1830/README.md)
- [Rule-by-rule implementation and test checklist](app/engine1830/RULE_COVERAGE.md)
- [Board-data and recorded-game attribution](app/engine1830/UPSTREAM_LICENSE)

The coverage document records edition decisions, including correction of the
printed tile 28 → 45 replacement to 28 → 46 to preserve track under §18.1.
Station-token counts exclude the separately represented market marker.

## Run the backend

```bash
python -m venv .venv
.venv/bin/python -m pip install -r multiplayer/backend/requirements.txt
cd multiplayer/backend
../../.venv/bin/python server.py
```

Use the authenticated `/api/1830` endpoints; FastAPI documents them at `/docs`.
The server persists JSON snapshots in SQLite and checks revisions transactionally
to prevent concurrent actions from overwriting each other. Creator, player and
spectator credentials have distinct permissions.

## Tests

From the repository root, with backend dependencies installed:

```bash
.venv/bin/python -m unittest discover -v
```

The suite includes rule acceptance and rejection checks, three independent
recorded games with exact final-score comparisons, deterministic replay, and
an entire recorded game played through the authenticated HTTP API and SQLite.
Cash, shares, trains and tile-supply invariants are checked after every accepted
action.

The core targets Python 3.8 compatibility. Runtime validation was performed on
Python 3.12; Python 3.8 syntax compatibility is also checked.

## Earlier prototypes

The existing `app.state`, `app.base`, and minigame modules remain available for
legacy consumers. New 1830 integrations use `app.engine1830`; the earlier modules
are not the rules controller for the new API. The existing multiplayer frontend
uses the earlier 1889 WebSocket interface; the new 1830 backend uses the API
above. Completeness of 1846, 1889 or other 18xx titles is outside this 1830
implementation.
