# Daemon18xx

Daemon18xx is an authoritative Python backend for **1830** and **standard/full
Shikoku 1889**, for 2–6 players. It validates actions, advances the complete game
sequence, calculates revenue and scoring, and persists games behind an
HTTP/JSON API. Frontends are independent projects; none are included here.

Use it as a running server or import its stateless, standard-library-only rules
engines. The server handles credentials, SQLite snapshots and concurrent-action
conflicts. Clients submit actions and render the returned state.

## Start

From the repository root, using Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

The interactive API reference is at `/docs`, its OpenAPI schema at `/openapi.json`,
and database readiness at `/health`. No external database or Node installation
is required. Stop with Ctrl+C; restarting with the same database resumes games.

For a background service with persistent storage and automatic restart:

```bash
docker compose up -d --build
```

Compose binds port 8000 to localhost and stores games in its `games` volume.
Use `docker compose logs -f backend` for logs and `docker compose down` to stop.
`docker compose down -v` deletes the game volume. Put an HTTPS reverse proxy in
front of the server when hosting it publicly.

## Connect a frontend

Read **[Frontend integration](docs/frontend_integration.md)**. This is the
client contract for humans and AI coding agents: endpoints, authentication,
working JavaScript, action fields, state/board rendering, and recovery behavior.

The basic flow is:

1. Create a room at `POST /api/{variant}/games` (`1830` or `1889`).
2. Distribute the returned player credentials privately; retain the creator token.
3. Start with the creator token and one name per seat.
4. Read state, submit player actions with the current revision, and poll for updates.

There are no accounts, join service, WebSocket subscriptions, or turn timers.
Clients own their lobby and credential distribution. The game advances when an
accepted action requires it; no separate game-loop worker is needed.

## Configuration

Set environment variables before starting the process:

| Variable | Default | Purpose |
|---|---|---|
| `DAEMON18XX_DATABASE` | `data/games.sqlite3` | SQLite path; relative paths resolve from the working directory. Startup creates its parent directory. |
| `DAEMON18XX_CORS_ORIGINS` | empty | Comma-separated browser frontend origins, e.g. `http://localhost:5173,https://play.example.com`. Empty means no cross-origin browser access. |

Compose sets the database path to `/data/games.sqlite3` inside the container.
Back up the database using SQLite's backup facility; it contains both games and
room credentials. To resume an existing installation, explicitly point the server
at its existing SQLite file. The former `multiplayer/backend/game.db` is no longer
the default. Existing Python-engine snapshots retain their migration support;
prototype pickle games are unsupported.

## Use the library

```python
from app.engine1889 import new_game, apply_action, legal_actions, replay

state = new_game(["Alice", "Bob", "Carol"])
next_state = apply_action(state, {
    "type": "buy_private", "player": "p1", "company": "TR",
}, expected_revision=0)
assert state["revision"] == 0
assert next_state["revision"] == 1
assert replay(["Alice", "Bob", "Carol"], next_state["history"]) == next_state
```

`app.engine1830` exposes the same core functions. Accepted actions return an
independent JSON-compatible state; rejected actions raise the variant's
`RuleError` without modifying the input. Library callers supply trusted player
identities and persistence. Core syntax targets Python 3.8; the server and test
workflow are validated on Python 3.12.

## Develop and validate

With the server dependencies installed, run from the repository root:

```bash
python -m unittest discover -q
python tools/render_edge_cases.py --check
```

`app/engine1830/` and `app/engine1889/` contain rules and board data; `backend/`
contains HTTP and persistence; `app/unittests/` contains engine, replay, API and
server tests. `tools/` contains optional fixture/catalog importers and the
edge-inventory renderer.

The [1830 coverage](app/engine1830/RULE_COVERAGE.md),
[1889 coverage](app/engine1889/RULE_COVERAGE.md), and
[executable edge-case inventory](docs/ENGINE_EDGE_CASES.md) record validation and
its limits. The source rules are [1830](docs/rules1830.rtf) and
[1889](docs/rules1889.pdf); the [1889 audit](docs/1889_RULEBOOK_AUDIT.md) records
edition decisions. Optional beginner 1889 and other 18xx titles are outside scope.

Board data and reference recordings derive from MIT-licensed `tobymao/18xx`;
retain the [1830 attribution](app/engine1830/UPSTREAM_LICENSE) and
[1889 attribution](app/engine1889/UPSTREAM_LICENSE).
