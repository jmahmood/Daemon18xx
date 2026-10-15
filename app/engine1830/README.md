# Python 1830 backend

This package implements the **1830 rules in `docs/rules1830.rtf`**. It is separate
from the older `app.state` / minigame prototype. The rules engine uses only the
Python standard library and accepts and returns JSON-compatible state; it does
not read files, access a database, use a network, or execute Ruby during games.

```python
from app.engine1830 import new_game, apply_action, replay, RuleError

state = new_game(['Alice', 'Bob', 'Carol'])
next_state = apply_action(state, {
    'type': 'buy_private', 'player': 'p1', 'company': 'SV',
}, expected_revision=0)
assert state['privates']['SV']['owner'] is None
assert next_state['privates']['SV']['owner'] == 'p1'
restored = replay(['Alice', 'Bob', 'Carol'], next_state['history'])
assert restored == next_state
```

`RuleError` means the action was rejected; the input state remains unchanged.
Each successful action increments `revision` once. Names must be distinct; the
supplied name order is seating order, with the first seat initially holding
priority. Pass a separate `player_ids` list to `new_game` when embedding the
engine in another authenticated transport.

## Actions

All actions carry `type` and an authenticated `player` ID. Identifiers are
`p1`–`p6` by default. Company IDs are `SV`, `CS`, `DH`, `MH`, `CA`, `BO`;
corporation IDs are `PRR`, `NYC`, `CPR`, `B&O`, `C&O`, `ERIE`, `NYNH`, `B&M`.

| Round / action | Fields and behavior |
|---|---|
| Initial `buy_private` | `company`; optional `price` must equal the offered price. |
| Initial `bid` | `company`, integer `price`; later privates require at least a $5 raise. Escrow is unavailable for other spending. |
| Initial `pass` | Pass on the offered private, or withdraw from a competitive auction. |
| B&O gift `par` | The gift recipient chooses `price` from 67, 71, 76, 82, 90, 100 before play resumes. |
| Stock `buy_shares` | `corporation`, `source` (`ipo` or `pool`, default `ipo`), optional `percent` (10 normally, 20 for a new presidency), `price` for a new par. |
| Stock `sell_shares` | `corporation`, `percent` in 10% units; a bundle sells at its pre-sale price. |
| Stock `end_turn` / `pass` | Ends the player's turn. A turn without a deal counts as a pass. Multiple sales and sell–buy–sell are allowed before ending. |
| Operating `lay_tile` | `hex`, base tile ID `tile`, `rotation` 0–5. Optional `special: CS` or `DH`; DH can include `place_token: true`. |
| Operating `home_token` | Erie chooses `city` 0 or 1 on its home hex; other homes are automatic. |
| Operating `place_token` | `hex`, optional `city` index (default 0). |
| Operating `skip` | Skips track or token placement; routes may be skipped only when no train can run. |
| Operating `run_routes` | `routes`, each with `train` ID and either `vertices` or `paths` as below. |
| Operating `dividend` | Boolean `payout`; resolves all submitted route revenue, then enters train buying. |
| Operating `buy_train` | `train`, optional negotiated `price` for an intercorporation sale, optional Diesel `trade_in`. Mandatory presidential contributions are automatic when affordable. |
| Interrupt `discard_train` | `corporation`, `train`; its president must resolve excess trains immediately. |
| Operating `emergency_sell` | `corporation`, `percent`; only while raising a mandatory train shortfall. |
| Operating `bankrupt` | Only when legally saleable shares plus personal and corporate cash cannot fund the cheapest depot train. Resolves liquidation and ends the game immediately. |
| Operating `end_turn` | Finishes a corporation after dividends and required train purchase; advances the complete round sequence. |
| `exchange_private` | M&H owner's action, optional `source` (`ipo` / `pool`); during their stock turn or between turns. Does not consume a normal stock buy. |
| `offer` | `kind` (`private` / `train`), `item`, `seller`, `buyer`, `price`. One party submits an authenticated offer; the other accepts by submitting the matching purchase. Offers are consumed on acceptance. |
| `buy_private` after auction | `company`, `buyer`, `price`. Negotiated player or corporate purchase requires the other party's recorded offer. A president facing a mandatory train purchase may sell a private to another player during the train step when treasury plus personal cash is insufficient; this does not consume a stock turn. A president buying their own private needs no second identity. |

Optional `par` is accepted as an alias for the new presidency's `price`.
`dividend` also accepts `kind: payout` / `withhold`. The aliases `exchange_mh`
and `bankruptcy` are accepted. Clients should prefer the primary names above.

`legal_actions(state, player)` provides action categories and candidate choices
for the requested player, including authenticated offers and legal between-turn
M&H exchanges. `player` identifies who may perform the returned actions;
`active_player` identifies the current turn or mandatory interrupt controller.
Offers include candidate `kind`, `item`, `seller` and `buyer` fields in
`choices.offers`, and valid M&H sources appear in `choices.exchange_sources`. Parameterized candidates still require validation by
`apply_action`; it does not enumerate every legal rotation, negotiated price,
or combination of routes.

## Routes and board geometry

A route may use explicit vertices:

```python
{'train': '2-0', 'vertices': [
    'I15:n0', 'I15:e0', 'J14:e3', 'J14:n0',
]}
```

Or ordered tile path indexes:

```python
{'train': '2-0', 'paths': [['I15', 1], ['J14', 1]]}
```

`n0` identifies the first revenue center on a tile; `e0` identifies edge 0.
Path indexes refer to that hex's current `paths` list in the state. Rotation
changes edge numbers, not path indexes. `board.neighbor(hex, edge)` exposes the
map's coordinate convention. Separate city nodes remain distinct through
upgrades. Revenue is calculated from the traversed cities, towns and offboards;
client-provided revenue values have no effect.

`board.route_candidates(state, corporation, train_id, limit=100)` offers example
legal routes. The limit caps suggestions, never route validation. As in table
play, players demonstrate their chosen routes; the backend checks their legality
and collects every stop's revenue. It does not promise an exhaustive optimal
route solver or silently replace submitted routes with its suggestions.

## HTTP API

Install `multiplayer/backend/requirements.txt` and start `python server.py` from
`multiplayer/backend`. Routes are documented by FastAPI at `/docs`:

1. `POST /api/1830/games` with `{"max_players": 3}` returns the creator,
   spectator and player tokens. Retain them privately.
2. `POST /api/1830/games/{room}/start` with `{"player_names": [...]}` and
   `Authorization: Bearer <creator_token>` starts one game, once.
3. `GET /api/1830/games/{room}` with any room token returns the state and
   derived market prices, certificate counts and available depot trains.
4. `POST /api/1830/games/{room}/actions` with a player token and
   `{"expected_action_id": 0, "action": {"type": "buy_private", "company": "SV"}}`
   submits an action. The server binds the player identity from the token.
5. `GET /api/1830/catalog` returns the static tile and map definitions.

The transport stores JSON snapshots in SQLite. A compare-and-append transaction
serializes competing writers, returns HTTP 409 for stale submissions and never
persists a rejected action. Rules errors return 422; invalid authorization returns
401/403. Creator and spectator credentials cannot submit gameplay actions.
Legacy 1889 WebSocket handlers reject 1830 rooms; clients use this HTTP API.
Credentials are never included in the rules state or returned game history.

## Validation and source data

Run the complete suite, including HTTP and persistence checks, with the backend
virtual environment activated:

```bash
python -m unittest discover -v
```

[Rule coverage](RULE_COVERAGE.md) maps every numbered rule and component table
to the implementation and acceptance tests, including the documented Table 6
correction. Three independently recorded games replay to exact reference scores;
one also runs through the authenticated HTTP API.

Board geometry and recorded-game fixtures derive from `tobymao/18xx` revision
`46a592e40494368390c9a731978a577ac4ecb1e0`. The implementation of gameplay rules
here is Python. Attribution and the upstream license are in
[UPSTREAM_LICENSE](UPSTREAM_LICENSE). `tools/import_1830_fixture.py` reproduces
fixture translation from an upstream recording, checks the independent result,
and writes accepted public actions. No network or upstream checkout is needed
for the regression suite.

Home-city indices are stored as `corporations[cid]["home_city"]` and remapped with station tokens on upgrades, including reservations for corporations that have not floated. Schema-1 saves without this field are migrated to schema 2 using printed home track and the current tile. Existing Erie home tokens preserve their chosen city. Misplaced NYNH home tokens move to the correct city when its slot is free; conflicting occupied slots return a migration error.

Railhead connectivity follows simple paths: cities and track vertices cannot be
revisited to unlock a branch through a loop. The search retains non-dominated
visited-path masks for each directed edge, so valid alternate paths remain
available. An M&H exchange transferring the presidency of NYC immediately before
its operating turn updates the active player while preserving that turn's steps,
funds, home token and operating order.

Erie must choose its home city before placing an additional token, running trains
or declaring dividends. It may lay its initial home tile or skip construction
before making that choice. Unsafe advances are rejected atomically.

`migrate_state(state)` returns an independent schema-2 snapshot without changing
revision or history; `apply_action` also migrates legacy library inputs. HTTP
reads migrate in memory, and the next accepted action persists the upgraded
state at the next revision. Unsupported schemas and unrepairable home mappings
return HTTP 409 without changing the saved snapshot.
