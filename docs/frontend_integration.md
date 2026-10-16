# Building a frontend for Daemon18xx

This is the integration contract for an external browser, desktop, mobile or AI
client. Start the backend using [README.md](../README.md). The backend owns rules,
turn progression, revenue, ownership and scoring. Your application owns its UI,
lobby, credential distribution and polling. No frontend code belongs in this
repository.

## HTTP contract

Use one base URL and one variant (`1830` or `1889`) per room. Bodies and responses
are JSON. Send `Content-Type: application/json` on POST requests and
`Authorization: Bearer <room-token>` on authenticated requests. Cookie sessions
are not used. `/docs` and `/openapi.json` describe the request envelopes and
variant-specific action schemas. `GET /api/{variant}/schema` returns a standalone
JSON Schema (Draft 2020-12) for the full action request, including required fields,
parameter types, examples and accepted aliases. Its `x-contract-version` is 1.
Schemas describe payload structure; the rules engine still checks whether the
action is legal in the current game state. Existing action payloads remain
supported; this metadata does not replace runtime rules validation.

| Method | Path | Credential | Body / response |
|---|---|---|---|
| GET | `/api/{variant}/catalog` | none | Board, tile, market and component metadata; see rendering below. |
| GET | `/api/{variant}/schema` | none | Action-request JSON Schema, aliases, examples and error-code descriptions. |
| POST | `/api/{variant}/games` | none | `{"max_players":3}` → room and credentials. Integer seat count 2–6, default 3. |
| POST | `/api/{variant}/games/{room}/start` | creator | `{"player_names":["Alice","Bob","Carol"]}` → game view. Starts once. |
| GET | `/api/{variant}/games/{room}` | any token for this room | Current game view. |
| POST | `/api/{variant}/games/{room}/actions` | player | `{"expected_action_id":0,"action":{"type":"pass"}}` → committed game view. |
| GET | `/health` | none | `{"status":"ok"}` if the database/schema is readable; otherwise 503. |

Creation returns exactly these credential fields:

```json
{
  "room_code": "ABC123",
  "creator_token": "opaque-secret",
  "spectator_token": "different-secret",
  "player_tokens": ["seat-1-secret", "seat-2-secret", "seat-3-secret"]
}
```

Values above are illustrative. Keep the creation response private. Give each
player only their own token. Give observers the spectator token. The creator can
start and read but cannot play; a person who creates and plays needs both their
creator token and their seat token. Tokens belong to one room and remain valid
across server restarts; there is no recovery, revocation or rotation endpoint.

The number of names must equal the room's seat count. Names must be distinct and
nonblank. Array order is seating order: `player_tokens[0]` controls `p1`, the first
name, and so on. Retain the room code, variant and seat mapping in your client.
Do not put credentials in public URLs, analytics or shared logs. Browsers need
an allowed origin configured through `DAEMON18XX_CORS_ORIGINS` when using a
separate origin. Use HTTPS outside local development.

## Working JavaScript example

This uses standard `fetch`; no framework or backend-specific SDK is required.
Run it against a local server from an allowed browser origin or a JavaScript
runtime with fetch support. Replace the base URL for your deployment.

```javascript
const base = "http://127.0.0.1:8000";
const variant = "1889"; // Change to "1830" for the other game.
const prefix = `${base}/api/${variant}`;

async function request(path, { method = "GET", token, body } = {}) {
  const response = await fetch(prefix + path, {
    method,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(JSON.stringify(data.detail ?? data));
    error.status = response.status;
    error.code = data.code;
    throw error;
  }
  return data;
}

const room = await request("/games", {
  method: "POST", body: { max_players: 3 },
});
const path = `/games/${encodeURIComponent(room.room_code)}`;
await request(path + "/start", {
  method: "POST", token: room.creator_token,
  body: { player_names: ["Alice", "Bob", "Carol"] },
});

// In a real client, creation/hosting is separate from the player's session.
const playerToken = room.player_tokens[0];
let view = await request(path, { token: playerToken });
async function submit(action) {
  try {
    view = await request(path + "/actions", {
      method: "POST", token: playerToken,
      body: { expected_action_id: view.state.revision, action },
    });
  } catch (error) {
    if (error.status === 409) {
      view = await request(path, { token: playerToken });
      // Re-render and ask the player to reconsider the action against this state.
    }
    throw error;
  }
  return view;
}

await submit({
  type: "buy_private", company: variant === "1889" ? "TR" : "SV",
});
```

Read state after starting using the player's token: the start response contains
hints for the active actor, whereas subsequent authenticated reads/actions
contain hints for that player in both variants. The server supplies `action.player` from the
credential. Omit it from requests; attempting to impersonate another player
returns 403. Money, percentages, city indices, rotations and revisions use JSON
integers; revisions specifically reject strings, floats and booleans.

## Synchronization and failures

Poll the authenticated GET endpoint approximately every 1–2 seconds while a
room is open, backing off on failures. Stop polling when the client is closed.
There are no WebSocket/SSE subscriptions or automatic server notifications.

Only one request should be in flight per client session initially. Serialize
polls and submissions, or ignore responses older than the latest displayed
`state.revision`. Keep the revision returned by the server. Accepted actions
increment it exactly once, and the action response is sent after persistence.
Rejected actions do not append a snapshot. Competing writers at the same
revision produce one accepted successor and a conflict for the other writer.

| Status | Meaning | Client behavior |
|---|---|---|
| 200 | Successful read, creation, start or action | Render/retain the returned result. |
| 401 | Missing/malformed Bearer header | Obtain the room credential. |
| 403 | Wrong credential, insufficient role or impersonation | Correct the session/role; do not retry unchanged. |
| 404 | Missing room or wrong variant; unsupported endpoint | Check the code and variant. Prototype 1889 rooms are also rejected. |
| 409 | Stale revision, competing write, writer busy, not started, already started, or invalid saved-state migration | Inspect `detail`. Refresh if started; show waiting state before start. Migration errors require server-side attention. |
| 422 | Invalid request or illegal game action | Show `detail`; state remains unchanged. Validation details may be an array rather than a string. |
| 503 | Room allocation/writer unavailable, or failed readiness | Back off; do not assume a room was created. |

Controlled API errors retain their existing `detail` value and add a stable
machine-readable `code`, for example:

```json
{"code":"STALE_REVISION","detail":"Stale action version; reload the current state"}
```

`REQUEST_VALIDATION_FAILED` has an array of validation details. `RULE_VIOLATION`
means the payload reached the engine but the move was rejected. `STATE_CONFLICT`
covers transactional initialization/write conflicts and database writer busy
responses. `GAME_NOT_STARTED` and `SAVED_STATE_INVALID` distinguish waiting from
restore failures. Authorization uses `AUTH_REQUIRED`, `INVALID_CREDENTIAL`,
`ROLE_FORBIDDEN` and `PLAYER_MISMATCH`. Other codes and their descriptions are in
`/api/{variant}/schema` under `x-error-codes`. Use codes and HTTP statuses for
control flow rather than parsing English messages. Unexpected failures and
middleware responses still require normal HTTP/network error handling.

After a network timeout on a write, fetch the latest state before attempting
anything else. The write may have committed. There are no idempotency keys.
Never automatically rebase a move onto a new revision: another action may have
changed its price, actor or meaning. Refresh again after reconnecting.

## Game view and state

Both variants return:

```text
{
  state: { ...authoritative snapshot... },
  prices: { corporationId: integerMarketPrice, ... },
  certificates: { playerId: integerCount, ... },
  available_depot_trains: [trainId, ...],
  train_limit: integer
}
```

Both variants also return `currency` (`"USD"` for 1830, `"JPY"` for 1889) and
player-specific `legal_actions`. `legal_actions` contains `player`,
`active_player` (absent when finished), `types` and `choices`.
These are action categories and candidate parameters, not an exhaustive list of
legal tile rotations, prices or routes; a suggested category can still be
rejected for specific parameters. `buy_private` during the initial auction is
accepted even though discovery advertises `bid` instead.

Treat snapshots as read-only and replace them after accepted actions/refreshes.
Useful state fields are:

| Fields | Meaning |
|---|---|
| `variant`, `schema_version`, `revision` | Variant, save format version and concurrency version. The API path is not a versioned API contract. |
| `players`, `player_order`, `priority` | Players keyed by ID (`id`, `name`, `cash`, `bankrupt`), seating order and priority deal. Do not derive seats from JSON object iteration order. |
| `round`, `phase` | Round is `auction`, `stock`, `operating` or `finished`; train phase is a string such as `"2"`, `"6"`, `"D"`. |
| `current_player`, `current_corporation` | Normal current actor/operator. Interrupts and private powers can require another actor; see below. |
| `stock_round`, `or_number`, `or_total`, `operating_turn` | Round counters and the operator's `step`, routes, revenue and construction bookkeeping. |
| `pending_par`, `pending_discards`, `pending_special` | Required interruptions. `pending_special` exists only in 1889. |
| `corporations`, `privates`, `trains` | Components keyed by stable IDs. Corporation `holdings` are percentages; `ipo` and `pool` are remaining percentages. Use the view's `prices` for current share prices; `par` is separate. Train ownership and rust status are authoritative. |
| `board`, `tiles` | Current map hexes and remaining physical tile counts. |
| `bank`, `bank_broken`, `end_after_set` | Bank and deferred ending flags. A negative bank does not by itself mean the game is over. |
| `offers`, `history`, `log` | Outstanding negotiation records, accepted actions and readable event messages. The response includes full history; there is no pagination endpoint. |
| `finished`, `end_reason`, `result` | Terminal flag, reason (`bank` or `bankruptcy`) and scores keyed by player ID. Display final scores from `result`. |

Resolve required interrupts before normal controls: a pending par choice,
excess-train discards by the affected presidents, or 1889's ER seller choice.
Use fresh state after each action; presidents, actors and steps can change during
a private exchange or train purchase. Do not hide every action merely because
`current_player` is another seat: permitted offers, M&H/DR exchanges and MF lays
can occur out of turn. For both variants, use the authenticated player's discovery hints
and `active_player` to distinguish personal options from the main turn.

## Action field reference

All entries below are `action` objects inside the revision envelope. Identifiers
are case-sensitive strings. A train ID such as `"2-0"` identifies a physical train;
`"2"` is its type. Optional means the field may be omitted, not sent as null.
The rules engine decides which actions and prices are permitted in current state.

| Action `type` | Fields and usage |
|---|---|
| `buy_private` (auction) | `company`; optional `price` must equal the current offered price. First company is SV in 1830, TR in 1889. |
| `bid` | `company`, integer `price`. Bids on later companies escrow cash. |
| `pass` | Auction pass/withdrawal; stock pass; ER decline in 1889. Prefer `end_turn` to complete stock/operating turns. |
| `par` | `price`; resolves 1830 B&O's pending gift par choice. |
| `buy_shares` | `corporation`, optional `source` (`ipo` default or `pool`), optional `percent`; a new presidency also needs `price` (par). Normal shares are 10%; a new presidency is 20%. |
| `sell_shares` | `corporation`, `percent` in 10% units. |
| `end_turn` | Finish a stock turn or a corporation's operating turn, subject to mandatory steps. |
| `lay_tile` | `hex`, base catalog ID `tile`, optional `rotation` 0–5 (default 0), optional `special`; see private powers. 1830 DH may also set `place_token: true`. |
| `home_token` | 1830 Erie: `city` 0 or 1; resolves its home choice before later required operations. Other homes are automatic. |
| `place_token` | `hex`, optional `city` index (default 0). |
| `skip` | Skip a track/token step, or routes only if no train can run. Cannot skip required dividends or train funding. |
| `run_routes` | `routes` array of train/path objects; see geometry below. Server computes revenue. |
| `run_best_routes` | 1889 only, no route parameters; exact maximum combined allocation. Search can be expensive on dense boards. |
| `dividend` | Boolean `payout`; distribute or withhold computed revenue. |
| `buy_train` | `train`, optional negotiated `price` for a corporate transfer, optional `trade_in` train ID for a Diesel. Required legal personal contributions are calculated by the engine. |
| `discard_train` | `corporation`, `train`; required excess-train interrupt controlled by its president. |
| `emergency_sell` | `corporation`, `percent`; sell shares during mandatory train funding. |
| `bankrupt` | Declare inability to fund the required train; allowed only after the engine's funding checks. |
| `exchange_private` | M&H (1830) or DR (1889); optional `source`. M&H uses `ipo` or `pool`, DR only `ipo`. |
| `offer` | `kind` (`private` or `train`), `item` ID, `seller`, `buyer`, integer `price`. The other party accepts with the matching purchase. IDs identify actual owners/buying corporation, not always human actors. |
| `buy_private` (negotiated) | `company`, `buyer`, `price`. Usually requires the other party's matching offer; a president buying their own private needs no separate actor's consent. Normal interplayer sales are prohibited in 1889. |

Use these primary action names. Compatibility aliases exist but are unnecessary
for new clients. Negotiated offers are stateful and checked against current
ownership/presidency; submitting a purchase does not bypass consent.

1830 corporation IDs: `PRR`, `NYC`, `CPR`, `B&O`, `C&O`, `ERIE`, `NYNH`, `B&M`.
Private IDs: `SV`, `CS`, `DH`, `MH`, `CA`, `BO`.
1889 corporation IDs: `AR`, `IR`, `SR`, `KO`, `TR`, `KU`, `UR`.
Private IDs: `TR`, `MF`, `ER`, `SMR`, `DR`, `SIR`, `UTF` (some absent by player
count). A private and a corporation can share an ID; keep component types distinct.

Private-power controls must account for these differences:

- 1830 CS/DH construction uses `lay_tile` with `special: "CS"` or `"DH"`.
  M&H uses `exchange_private`; B&O's gift can interrupt the auction for `par`.
- 1889 MF uses `lay_tile`, `special: "MF"`, `tile: "437"`, `hex` and `rotation`.
  Its one-time port option is available to its player owner on eligible coastal
  town hexes, including permitted out-of-turn windows.
- 1889 ER sale creates `pending_special` for the **seller**. Submit `lay_tile`
  with `special: "ER"`, `hex: "C4"`, tile and rotation, or `pass`. Seller pays
  costs; then the buying corporation's president resumes.
- 1889 DR uses `exchange_private` for an IPO IR share, including permitted
  out-of-turn windows. SMR's terrain benefit is automatic; TR/SIR/UTF require
  no extra power button. UTF survival/revenue depends on its owner at phase 5.

## Board, tiles and routes

Fetch the catalog once per variant per server release. Both variants expose:

- `variant`, `contract_version: 1`, `action_schema_url`, `currency`, `layout`,
  `edge_deltas`, `market`, `par_prices`, `certificate_limits`, `rusts`, `upgrades`.
- `board`: parsed initial geometry, and `tile_geometry`: parsed rotation-zero
  tile geometry keyed by base tile ID. Rotate edge numbers modulo six to preview
  other orientations; node/path indices stay fixed.
- `components`: named objects under `corporations` (`name`, `home`,
  `token_supply`), `privates` (`name`, `value`, `revenue`, `blocked_hexes`),
  `train_types` (`initial_count`, `price`, `stops`, `unlimited`) and `phases`
  (`train_limit`, `tile_colors`, `operating_rounds`). The full private inventory
  is listed; use the started state's privates to see which are in this game.
- Original raw `hexes` and `tiles` fields, and tuple-shaped `corporations`,
  `privates`, `train_types`, `phases` tables, retained for compatibility. New
  clients should use the named `components` objects for those tables.

1889 uses flat layout and unlimited Diesels; 1830 uses pointy layout and a finite
Diesel supply. `unlimited` distinguishes the roster policies without treating
1889's initial Diesel count as its total supply.

Draw the **current** geometry from `state.board[hex]`: `color`, `nodes`, `paths`,
`rotation`, `tokens`, `label`, `tile`, and terrain/cost information where present.
Draw available tiles from the catalog and remaining counts from `state.tiles`.
Cities/offboards/towns are distinct revenue nodes. `tokens[cityIndex]` lists
corporations occupying that node; do not flatten multi-city hexes.

Nodes use `n0`, `n1`, etc.; tile edges use `e0`–`e5`. Rotation adds its integer
value modulo 6 to each printed edge number. Current state paths already have
rotated edge numbers; do not rotate those paths a second time. Map a coordinate
to letter-row and numeric-column. The neighbor deltas for edges 0 through 5 are:

| Variant | `(row delta, column delta)` for edges 0, 1, 2, 3, 4, 5 |
|---|---|
| 1830 | `(1,-1), (0,-2), (-1,-1), (-1,1), (0,2), (1,1)` |
| 1889 | `(0,2), (-1,1), (-1,-1), (0,-2), (1,-1), (1,1)` |

The opposite edge is `(edge + 3) % 6`. Only coordinates in `state.board` exist.
Catalog `tiles` entries retain compact track `code` strings for compatibility;
new clients can render `tile_geometry` directly without parsing that notation.
Gameplay geometry comes from `state.board`, including all accepted rotations,
upgrades and token placements.

Submit either explicit vertices or ordered tile path indices, per train:

```json
{
  "type": "run_routes",
  "routes": [
    {"train": "2-0", "paths": [["I15", 1], ["J14", 1]]}
  ]
}
```

The example is a representation example, not a universally legal route. Path
indices refer to that hex's current `paths` array and do not change merely
because of rotation. Vertex form uses e.g.
`{"train":"2-0","vertices":["I15:n0","I15:e0","J14:e3","J14:n0"]}`.
Routes must follow real contiguous track, include the operator's station and
satisfy stop limits/blocking; routes in one allocation cannot share track.
Client-provided revenue is ignored. In 1889 an unpaid route claim may be replaced
before dividends; 1830 allows one route submission per turn. Manual legal routes
are accepted under tabletop responsibility for maximizing revenue; only 1889's
`run_best_routes` promises an exact automatic allocation.

## Implementation checklist for an AI coding agent

1. Keep the frontend in its own repository. Configure a server base URL and variant.
2. Implement create/start or accept an existing room code, variant and seat token.
   Do not invent account, join, list-room, rename, undo or subscription endpoints.
3. Build one transport adapter with the revision envelope, structured errors,
   sequential requests, polling, reconnect refresh and private credential storage.
4. Render current state and catalog data. Preserve IDs, strings, integer amounts,
   node indices and per-variant response differences.
5. Provide auction, stock, track/token, route/dividend, train/funding, negotiation,
   private-power and mandatory-interrupt controls. Treat discovery as advisory.
6. Handle spectators, non-active players, waiting rooms and finished scores.
7. Verify both variants against a real server: a legal action, wrong-player move,
   stale submission, two competing clients, reconnect, server restart, an
   interrupt and a finished-game view. Server fixtures in `app/unittests/fixtures/`
   and API tests provide complete action sequences; tests sometimes seed special
   states directly and are not all client setup recipes.

For engine changes, consult the variant RULE_COVERAGE.md files, source rulebooks
and [edge inventory](ENGINE_EDGE_CASES.md). Those are validation references;
this document and runtime OpenAPI are the client integration entry points.
