# Python Shikoku 1889 backend

`app.engine1889` implements the standard full game for 2–6 players, with a
stateless Python rules library and an authenticated HTTP API. The beginner-game
option is excluded. The engine uses only the standard library. It never calls
Ruby, reads files, or uses a network during play.

```python
from app.engine1889 import new_game, apply_action, legal_actions, replay

state = new_game(['Alice', 'Bob', 'Carol'])
state = apply_action(state, {
    'type': 'buy_private', 'player': 'p1', 'company': 'TR',
})
assert replay(['Alice', 'Bob', 'Carol'], state['history']) == state
```

Every accepted action returns an independent JSON-compatible state and increments
`revision`. Rejected actions raise `app.engine1889.RuleError` and preserve input
state. Separate 1830/1889 modules select their own components and policies;
running either game never switches mutable module globals in the other.

Older schema-1 operating saves missing `operating_turn.emergency_sales` require
a complete accepted action history that reproduces the saved state. Loading
reconstructs the current turn's sale blocks without changing the revision or
input; the next accepted action persists them. Incomplete or inconsistent
histories raise `RuleError` (HTTP 409) instead of clearing the restriction.
Prototype pickle saves remain unsupported. Action-discovery results also return
independent lists, so editing a response cannot alter a game's trains.

## Standard components and differences

- ¥7,000 total; starting cash ¥420 for 2–4 players and ¥390 for 5–6.
- Seven corporations: AR, IR, SR, KO, TR, KU, UR. Flotation at 50%, full
  capitalization at ten times par, and all floated home stations at OR start.
- Par ¥65/70/75/80/90/100; standard 11-row market and certificate limits.
- The complete 52-hex flat-layout board and 63 physical tiles. City labels,
  preserved track, finite supplies, reservations, blocked cities and terrain
  costs are enforced. Additional stations cost ¥40 each.
- One stock purchase per turn; sales of each corporation form one block per turn.
  Sell–buy or buy–sell is allowed; sell–buy–sell is prohibited.
- Finite 2/3/4/5/6 trains, unlimited Diesels, rust, discards, returned trains,
  trade-ins, negotiated transfers, phase-dependent tile colors and OR sets.
- Diesel offboard values depend on the train running the route, not merely the
  presence of a Diesel elsewhere in the game.
- Forced funding uses treasury, then personal cash, then necessary stock sales.
  No presidential subsidy of another corporation's train and no emergency
  presidency transfers. Bankruptcy ends immediately; bank depletion ends after
  the required operating set. Final scores exclude corporate treasuries.

## Actions and private companies

All actions include `type` and authenticated `player`. Stock, operating, route,
train, offer, dividend and ending actions use the same field contract documented
in [the 1830 API guide](../engine1830/README.md), with these 1889 policies:

| Company | Behavior / action |
|---|---|
| TR | Blocks K4 while player-owned; normal closure at first 5. |
| MF | Player owner uses `lay_tile`, `special: 'MF'`, `tile: '437'`, an unbuilt coastal town B11/G10/I12/J9 and `rotation`. Available in stock rounds, between OR turns, or the owner's corporation's track step. No connectivity required; once only; does not close MF. The port tile cannot be upgraded. |
| ER | Selling to a corporation starts a mandatory actor interrupt for the seller. Seller may `lay_tile` at C4 with green 12/13/14/15/205/206 and `special: 'ER'`, or `pass`. The seller pays construction costs; the corporation's normal lay is preserved. Its original president resumes afterward. |
| SMR | Corporation ignores pure-mountain costs; mixed water/mountain and special-city costs remain payable. |
| DR | Player uses `exchange_private` (alias `exchange_dr`) for one 10% **IPO** IR share, on their stock turn or between turns. Enforce ownership, timing and certificate limits; closes DR. |
| SIR | No special power; absent at two players. |
| UTF | Absent below four players. Player-owned UTF survives first 5, earns ¥50 and cannot subsequently be sold to a corporation. Corporation-owned UTF closes normally. |

Corporate private purchases require phase 3/4, half-to-twice face value and an
accepted `offer` from the other party. Ordinary interplayer private sales are
prohibited. Company-specific actions do not let clients bypass pending ER or
train-discard interrupts. Phase 5 closes all other remaining privates.

`legal_actions(state, player)` includes out-of-turn offers, permitted DR exchanges
and MF port choices. Pending ER choices identify the **seller**, not the buying
corporation president. Candidate parameters still undergo authoritative rule
validation. Routes may use explicit vertices or ordered `[hex, path-index]`
segments; revenue is computed from the actual stops. Suggestions are bounded,
not a promise of globally optimal revenue.

## HTTP and persistence

Run the existing FastAPI server with `multiplayer/backend/requirements.txt`
installed. The supported JSON backend is:

1. `POST /api/1889/games` with `{"max_players": 3}` returns creator, spectator
   and player tokens.
2. Creator token: `POST /api/1889/games/{room}/start` with `player_names`.
3. Room token: `GET /api/1889/games/{room}` returns state, prices, certificate
   counts, depot availability, train limit, currency and that player's action hints.
4. Player token: `POST /api/1889/games/{room}/actions` with
   `{"expected_action_id": 0, "action": {"type": "buy_private", "company": "TR"}}`.
5. `GET /api/1889/catalog` exposes board, tiles, layout, market and component data.

Use `Authorization: Bearer <token>`. Actor identity is bound to the token. Stale
or concurrent writes return 409; invalid actions return 422; creator/spectator
writes return 403. SQLite atomically compares revisions and appends snapshots.
Each request restores authoritative state, including a pending seller interrupt.

An additive database migration records `games.engine`. New 1889 JSON rooms use
`python`; preexisting prototype rooms default to `legacy`. Legacy unauthenticated
HTTP and Socket.IO handlers reject Python rooms, including before a game starts.
The new API rejects legacy rooms. Prototype pickle snapshots are not converted
into standard 1889 games. Existing `/api/1830` and its saved-game migration remain
supported. The existing frontend still uses the legacy protocol and needs a
separate update to use these APIs.

## Validation and sources

Run `python -m unittest discover -q` with backend dependencies installed.
[Coverage and known reference limitations](RULE_COVERAGE.md) distinguishes exact
independent results from authored scenarios. The catalog and reference recording
derive from MIT-licensed `tobymao/18xx` at
`46a592e40494368390c9a731978a577ac4ecb1e0`; see [UPSTREAM_LICENSE](UPSTREAM_LICENSE).
`tools/import_1889_catalog.py` and `tools/import_1889_fixture.py` reproduce data
extraction and action translation without executing upstream code.

The [dual-game edge-case checklist](../../docs/ENGINE_EDGE_CASES.md) links each
reviewed boundary to its automated tests. Normal discovery verifies the links;
`python tools/render_edge_cases.py --check` verifies its generated documentation.
