# 1889 readiness audit and dual-game implementation checklist

> Historical audit before the uploaded Japanese rulebook. See the
> [current rulebook comparison and corrections](1889_RULEBOOK_AUDIT.md).


> Historical preimplementation audit. The standard Python 1889 backend is now
> implemented at `app.engine1889` and `/api/1889`. See the [current coverage and
> reference-recording limitation](../app/engine1889/RULE_COVERAGE.md). The legacy
> frontend still needs a separate update. Findings below describe the earlier
> prototype; the two-reference-game gate was revised after game 314 proved to
> contain a blocked-city route.

## Finding

**1889 is not presently functional through a complete game.** The playable 1830
backend is `app.engine1830` plus `/api/1830`. The existing 1889 frontend still uses
`app.state`, mutable module-level configuration, and the earlier Socket.IO
handlers. Adding an 1889 configuration to that old route will not make it a
complete game. Both titles should use the validated state/action controller,
with explicit variant rules and one authenticated transport contract.

This is an implementation audit, not a claim that the work below is complete.
No 1889 rulebook was uploaded: the uploaded RTF is 1830. The target assumed here
is the standard/full game of **Shikoku 1889**, excluding beginner-game options.
Rule differences were cross-checked against the production `G1889` implementation
in [tobymao/18xx at revision 46a592e40494368390c9a731978a577ac4ecb1e0](https://github.com/tobymao/18xx/tree/46a592e40494368390c9a731978a577ac4ecb1e0/lib/engine/game/g_1889).
Its [metadata](https://github.com/tobymao/18xx/blob/46a592e40494368390c9a731978a577ac4ecb1e0/lib/engine/game/g_1889/meta.rb)
links the published rulebook. Edition-specific approval should use that rulebook;
this audit does not claim a line-by-line review of an uploaded 1889 rules PDF.

## Confirmed blockers

| Evidence | Consequence |
|---|---|
| A `StockRoundMove(PASS)` in an 1889 `Game` returns `False` from `isValidMove`; `apply_move` leaves its turn counter unchanged. | The public legacy engine cannot advance a stock round. |
| `OperatingRoundMove.fromMove` raises `NotImplementedError`. | The legacy server cannot deserialize an operating action into a working game move. |
| Two separately started 1889 games share the identical mutable corporation instance. | Concurrent games can contaminate each other's money, stock and trains. |
| `Game.isOngoing()` always returns `True`. | The legacy loop has no working terminal condition. |
| `app/config/1889.py` explicitly contains a simplified market; `multiplayer/shared/1889_map.py` explicitly contains a simplified map. Their home coordinates disagree with the full board. | These are placeholders, not complete components for legal track, stations or routes. |
| The frontend renders `Stock Round UI coming soon...` and its action handler submits only `BuyPrivateCompanyMove`. | A successful TypeScript build does not make stock or operating play possible. |
| The new controller hard-codes 1830's bank, flotation, market, private IDs, tile data, token costs and ending invariants. | Changing only `variant` would apply incorrect rules and component data. |
| Feeding `yellow_30\|brown_60\|diesel_100` to the new board decoder raises `ValueError: too many values to unpack`. | 1889 offboard revenue requires a phase/train-aware representation. |
| The legacy move handler broadcasts success even when `apply_move` returns unchanged state; the latest move number defaults to zero. | Rejections can appear accepted; persisted history/version ordering is unreliable. |
| The legacy unauthenticated room-info endpoint returns raw game/player database records; gameplay trusts client-supplied player IDs and excludes only spectators. | Both games need the authenticated, identity-bound transport already implemented for 1830, not these legacy handlers. |

These were established through source inspection and focused runtime probes.
The existing serialization smoke test creates, serializes and restores an 1889
game; it does not execute its stock and operating rounds or validate its rules.

## Required rule and component changes

| Area | 1889 target | Required change |
|---|---|---|
| Money | ¥7,000 total, including initial player money. Starting cash: ¥420 each for 2–4, ¥390 each for 5–6. | Variant bank/invariant/starting-cash data. The current cash helper is already correct; the multiplayer README's ¥2,500 divided by players is not. |
| Certificates | 2/3/4/5/6 players: 25/19/14/12/11. | Variant limits; preserve president-certificate counting and applicable yellow/orange exceptions. |
| Par and market | Par ¥65, 70, 75, 80, 90, 100; actual ragged 11-row market, with yellow/orange zones and no brown zone. | Replace the synthetic 15-column grid and do not reuse 1830's par list or brown-buy rules. |
| Flotation | 50%, full capitalization at ten times par. | Parameterize flotation threshold; retain IPO/pool distinction and capital paid once at first operation. |
| Stock sales | Shares of one corporation sold as a block in the player's turn; 1889 sell/buy ordering differs from 1830 sell–buy–sell. | Per-turn sold-block bookkeeping and explicit variant transaction ordering. |
| Private eligibility | 2 players: omit SIR and UTF; 3 players: omit UTF; 4–6: all seven. | Remove the incorrect cheapest-five/cheapest-six filtering in server and serializer. Standard 3-player game has six privates. |
| Corporations | AR, IR, SR, KO, TR, KU, UR. | Keep correct identities but replace placeholder home data. |
| Home hexes | AR K8; IR E2; SR I2; KO K4; TR F9; KU C10; UR B7. | Use the actual board, home timing and reservations. |
| Station tokens | AR/IR/SR/KO: 2; TR/UR: 3; KU: 1. Extra tokens cost ¥40 each. | The configured token supplies are correct; parameterize cost instead of 1830's later ¥100 tokens. |
| Map and tile inventory | Full Shikoku map; flat layout; fixed gray, red and green hexes; actual finite tile manifest, labels and upgrades. | Dedicated catalog and layout-aware adjacency. Preserve track/cities on upgrades, finite supplies and station reservations. |
| Terrain | ¥80 terrain costs, including mountains, water and specified special-city construction. | Replace zero-base-cost multipliers with printed hex costs; retain terrain identity for SMR. |
| Trains | Six 2s, five 3s, four 4s, three 5s, two 6s; unlimited Diesels. Prices 80/180/300/450/630/1100, Diesel 800 with eligible trade-in. | Generate new Diesel instances as needed; current legacy roster has only one instance per type and the 1830 engine has six Diesels. |
| Phases | Limits 4 → 3 at first 4 → 2 at first 5; 2s rust on 4, 3s on 6, 4s on D. | Reuse common mechanisms with variant definitions and exact event timing. |
| Operating rounds | One initially, two after phase 3, three after phase 5, with changes at the appropriate next stock-round boundary. | Correct legacy comment/config limiting 1889 to two rounds. |
| Offboards | Ordinary yellow/brown values; additional Diesel-specific values, e.g. F1 30/60/100 and J1/L7 20/40/80. | Store revenue tiers by phase/train. A Diesel's value must not incorrectly apply to an ordinary 5 or 6 train in the same phase. |
| Private sales | Corporate purchases after first 3, permitted face-value bounds; no ordinary interplayer private sales in standard 1889. | Do not inherit the 1830 player-to-player private sale rule. |
| Emergency funding | Presidential cash cannot subsidize buying another corporation's train; emergency sales must not swap presidencies, including other corporations. | Explicit emergency-purchase and forced-sale policies; 1830's permissive alternatives cannot be inherited blindly. |
| Endgame | Immediate bankruptcy or bank exhaustion at the required operating-set boundary; correct yen accounting and final valuation. | Reuse the common ending controller with 1889 money and private-company exceptions. |

### Private-company acceptance checklist

- **TR:** blocks K4 while player-owned; normal closure on first 5.
- **MF:** player owner places one special port tile on an eligible unbuilt coastal
  town, B11/G10/I12/J9, without corporate connectivity. Enforce permitted timing,
  including no interruption of another player's corporation turn; using the
  ability does not itself close MF.
- **ER:** blocks C4 while player-owned. When sold to a corporation, the **selling
  player** immediately receives the optional green-tile action on C4. This
  interrupts the buying corporation's turn and does not consume its normal lay;
  the selling player pays applicable costs. Resume the correct actor afterward.
- **SMR:** corporation ignores eligible pure-mountain construction cost;
  mountain-plus-river hexes do not get that exemption.
- **DR:** player can exchange it for a 10% **IPO** share of IR, with ownership,
  certificate and timing validation; no Bank Pool source. Exchange closes DR.
- **SIR:** no special power; omitted from the standard two-player game.
- **UTF:** eligible only at 4–6 players. If still player-owned at the first 5,
  remains open, revenue rises to ¥50 and it can no longer be sold to a
  corporation. If corporation-owned it closes normally. Continued revenue,
  certificate counting and endgame value must use the surviving state.

## Implementation sequence that preserves both games

1. **Extract a shared pure-Python controller.** Retain `app.engine1830` and
   `/api/1830` as compatibility entry points. Select immutable variant data and
   rule policies from `state.variant` on each call. Never switch module globals
   to run another game's rules: concurrent 1830/1889 games must be independent.
2. **Add the standard 1889 catalog and policies.** Separate component definitions
   from board topology, transactions and round mechanics. Parameterize money,
   par/market, flotation, certificates, station costs, sale ordering, train supply,
   private filtering, special powers, emergencies and closure behavior.
3. **Extend topology and private interrupts.** Add layout-aware coordinates,
   phase/train-specific revenue, port tile handling, pure/mixed terrain identity,
   and ER's seller-controlled interrupt/resume. Do not turn 1889 abilities into
   variants of 1830's CS/DH/MH abilities merely because they look similar.
4. **Unify the authenticated transport.** Either expose a variant-selected shared
   API with existing 1830 aliases or an equivalent `/api/1889` adapter using the
   same state/action contract. Save variant and schema version in JSON snapshots;
   bind actors to player credentials; use revision-checked transactions and
   structured rule errors. Explicitly isolate legacy rooms instead of loading
   legacy pickle snapshots into the new schema without migration.
5. **Make the client playable for both.** Add game selection and variant-aware
   catalogs, currencies, player counts and private lists. Implement stock actions,
   track rotations, stations, train routes/dividends, train purchases, negotiations,
   forced discards/funding, private interrupts and final results. Use one supported
   transport; updates may use polling, Socket.IO or another stream, but writes
   must retain authenticated identities and expected revisions. Update all map,
   market, player and corporation views from authoritative state.
6. **Validate both together.** Keep all existing 1830 acceptance, replay and API
   tests passing while adding the acceptance gates below. Update `multiplayer/STATUS.md`
   and earlier README statements that currently overstate 1889 readiness.

## Completion gates

- Rule-specific positive and negative tests for every difference and private
  ability above, covering all supported player counts.
- Two **complete**, independently recorded standard 1889 games replay to their
  reference final scores and correct endings: upstream `1889/314.json`
  (three-player bankruptcy, 457 source actions) and `1889/962.json`
  (four-player bank exhaustion, 522 source actions). Expand programmed actions
  and resolve undo/redo just as with the 1830 fixtures. The two other available
  five-player recordings were manually ended after 47/50 actions and are useful
  supplementary scenarios, not proof of game completion.
- At least one full 1889 recording driven through the authenticated API,
  persisted, restored and continued, including actor changes for ER's interrupt.
- 1830's three exact-score recorded games and its HTTP game remain green.
- Interleave 1830 and 1889 actions in one process; verify no shared mutable
  companies, markets, supplies or policies and separate money invariants.
- Cross-room/variant authentication tests, stale/concurrent submissions,
  rejected-action atomicity, spectators, restart and reconnect behavior.
- Browser workflow for **each** game: create, join, auction, stock round, legal
  company operation, persist/reload, special interrupt, and display final results.
  A production build alone is not a browser gameplay check.

## Checks actually run during this audit

- Full installed-dependency test suite: **342 passed, no skips**. These remain
  evidence for the existing tested code, chiefly the new 1830 implementation;
  they do not establish 1889 rule coverage.
- Frontend `npm run build`: passed TypeScript and Vite production build.
- Legacy 1889 stock-pass probe: rejected by the public validator; state unchanged.
- Legacy operating-action deserialization probe: `NotImplementedError`.
- Legacy independent-game probe: corporation instance shared across games.
- 1889 three-tier offboard decode probe against the new 1830 decoder: `ValueError`.
- No 1889 recorded-game replay or full browser game has been claimed as run.

No gameplay implementation was changed by this audit. It defines the concrete
work required before either an 1889-complete backend or a playable dual-game
frontend can be claimed.
