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

## 1889 engine

`app.engine1889` implements standard Shikoku 1889 in pure Python, including its
full game loop, seven private powers/components, unlimited Diesels and endings.
Use the authenticated `/api/1889` API. It runs independently alongside 1830.

- [1889 engine and API guide](app/engine1889/README.md)
- [1889 acceptance coverage and reference limitations](app/engine1889/RULE_COVERAGE.md)
- [Uploaded 1889 rulebook audit and iteration results](docs/1889_RULEBOOK_AUDIT.md)

## Run the backend

```bash
python -m venv .venv
.venv/bin/python -m pip install -r multiplayer/backend/requirements.txt
cd multiplayer/backend
../../.venv/bin/python server.py
```

Use the authenticated `/api/1830` or `/api/1889` endpoints; FastAPI documents them at `/docs`.
The server persists JSON snapshots in SQLite and checks revisions transactionally
to prevent concurrent actions from overwriting each other. Creator, player and
spectator credentials have distinct permissions.

## Tests

From the repository root, with backend dependencies installed:

```bash
.venv/bin/python -m unittest discover -v
```

The suite includes rule acceptance/rejection checks, independent exact-score
recordings for both variants, deterministic replay, an authored 1889 game through
every train phase, authored 1889 endings for every player count, and complete recorded games through authenticated HTTP/SQLite.
Cash, shares, trains and tile-supply invariants are checked after every accepted
action.

The [1830/1889 edge-case checklist](docs/ENGINE_EDGE_CASES.md) maps 226 rule and
transport boundaries to named tests. Its [JSON source](docs/ENGINE_EDGE_CASES.json)
is checked during normal discovery for missing tests and stale documentation.

The core targets Python 3.8 compatibility. Runtime validation was performed on
Python 3.12; Python 3.8 syntax compatibility is also checked.

## Earlier prototypes

The existing `app.state`, `app.base`, and minigame modules remain available for
legacy consumers. New integrations use `app.engine1830` or `app.engine1889`; the earlier modules
are not the rules controller for the new API. The existing multiplayer frontend
uses the earlier 1889 WebSocket interface and needs a separate update to connect
to these JSON APIs. 1846 and other variants are not implemented by these backends.
