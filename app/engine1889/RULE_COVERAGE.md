# Standard 1889 backend coverage

Target: standard/full Shikoku 1889 for 2–6 players, excluding the beginner option.
The rule-policy and component cross-check is the pinned production `G1889` in
`tobymao/18xx` revision `46a592e40494368390c9a731978a577ac4ecb1e0`, including its
published-rulebook metadata link. No uploaded 1889 PDF was provided; the uploaded
RTF specifies 1830. This document does not claim a page-by-page PDF comparison.

## Acceptance evidence

Tests are in `test_Engine1889.py` and `test_Engine1889API.py`.

Additional boundary suites are `test_Engine1889Edges.py`,
`test_EngineAuctionAndEmergency.py`, `test_EngineContractEdges.py`,
`test_EngineTopologyEdges.py` and `test_EngineAPIEdges.py`. The
[edge-case inventory](../../docs/ENGINE_EDGE_CASES.md) maps each reviewed case to
its named test for each applicable variant. Normal discovery also verifies
those test references and the generated checklist remain current.

`test_EngineReviewEdges.py` adds legacy-save history reconstruction, independent
action-discovery results, seven-stop Diesel routes, par preservation after actual
market moves, cheapest returned-train emergency funding, two-president discards
with restoration, and positive 5/6 Diesel trade-ins with exact price bounds.
The legacy migration also runs through real authenticated HTTP and SQLite:
reads preserve the old stored snapshot and revision, the next accepted action
persists the recovered bookkeeping, and incomplete/inconsistent history returns
409 without appending a state.

`test_EngineCoverageLoop.py` adds certificate buy/pass boundaries at every player
count, ER seller/buyer control overlap, MF power removal after corporate sale,
consent after a presidency change, strict snapshot metadata, invariant failures,
round dispatch and alias normalization, route quotations and required operating
steps. HTTP scenarios cover all player counts, invalid metadata conflicts and
rollback/retry after a database commit failure. See the
[iterative test audit](../../docs/ENGINE_TEST_AUDIT.md).

Competitive auctions select the lowest standing bidder after every pass/raise.
Emergency sales record one block per corporation per operating turn, survive
JSON/SQLite reload, and use the same restriction in bankruptcy funding estimates
and liquidation. A new operating turn resets that bookkeeping.

| Area | Implemented behavior and evidence |
|---|---|
| Setup | Every player count, correct money/certificates/private filtering, seven corporations, 52 hexes and 63 tiles. |
| Auction | Ordered purchases, competitive bids, escrow, refunds, first-company discount, no first-stock-round sales. |
| Stock | Legal par prices, president first, 50% float, full capital once, per-turn block sales, sell/buy ordering, sold-company restriction, market color exemptions. |
| Homes | All floated companies place their free home station at OR start; future companies' home tokens already block rivals. |
| Turns | Full auction/stock/OR loop, ordered operating steps, one normal lay and extra token, payouts/withholds, delayed 1/2/3-OR sets. Complete recordings exercise these together. |
| Map | Standard flat coordinates; matching town/city/label and next color; every preserved path and station; finite tile accounting; terrain and map-edge constraints. |
| Stations/routes | ¥40 extra stations, token supply, reservations and city blocking; legal railheads, no repeated vertices/track, no switching at junctions/crossings, train capacity and distinct trains/routes. |
| TR | K4 block while player-owned; first-5 closure. |
| MF | Unbuilt coastal-town port, player ownership and timing, once only, no connectivity, no closure on use, permanent port tile; exact reference game includes use. |
| ER | Seller-controlled interrupt with optional green lay/pass; wrong actor/tile rejected; preserves normal lay and restores original actor. Both pure-engine and real HTTP tests. |
| SMR | Pure mountain discount; mixed water/mountain excluded; repeated H-city construction costs preserved. |
| DR | IPO-only 10% IR exchange, ownership/60%/timing restrictions and closure; between-turn actor discovery. |
| SIR / UTF | Two-player SIR removal; UTF absent below four, survives as player-owned at first 5 with ¥50 revenue; corporation-owned closure. |
| Trains | Ordered finite depot, returned trains, immediate excess discards, corporate transfers with consent, unlimited Diesel generation, Diesel trade-in at train limit, all rust events. |
| Revenue | Real stop revenue; train-specific Diesel offboards; private income and corporate/player ownership; pool versus IPO payouts. |
| Emergency | Cheapest depot alternative, necessary sales only, personal contribution only when mandatory, no subsidy of another company's train, no presidency swaps in any company; immediate bankruptcy and unsaleable-stock scoring. |
| Endgame | Bank depletion finishes the required set, bankruptcy ends immediately, corporate treasury excluded, UTF included when eligible. |
| Isolation | Interleaved 1830/1889 games preserve each other's state and ¥7,000/$12,000 invariants; no module-global rule switching. |
| Transport | All roles, wrong-room/variant tokens, creator-only start/restart rejection, stale revisions, concurrent writers, rejected-action atomicity, ER interrupts, JSON reload and continued play. |
| Database | Additive legacy-engine migration is repeatable and preserves existing rows. Legacy endpoints cannot expose Python-room credentials or accept its gameplay. |

## Complete games and reference limitations

- **Independent upstream game 962:** 486 translated accepted actions, bank ending;
  exact source scores: 1230=3880, 545=4444, 253=4317, 147=3091. This game ends in
  phase 5; it does **not** establish phase 6/D coverage. It also runs entirely
  through the authenticated API and SQLite, with exact library-state comparison
  after every action and mid-game/final restoration.
- **Authored complete game:** 1,566 accepted public actions; all seven corporations
  float and operate; phases 2/3/4/5/6/D; bank ending after the required OR set.
  Expected scores: p1=2725, p2=2787, p3=4442, p4=2741. It is explicitly authored
  against this Python backend, not an independent reference recording.
- **Additional authored player-count games:** 2/3-player bank endings (720/813
  accepted actions), 5/6-player bankruptcy endings (502/109 actions). Together
  with the four-player scenarios these exercise complete games for every
  supported player count, including JSON restoration during play and after
  completion. They are regression recordings authored against this backend,
  with fixed expected scores, not independent reference games.
- **Historical upstream game 314 is not a valid exact-score acceptance game.**
  Its action 367 runs IR's 3-train through I2, which has both SR and AR stations
  and no IR station. That city is full and blocks IR. The first 403 translated
  actions are retained as a regression fixture, and the recorded illegal route
  is explicitly rejected. Allowing it to match the old final scores would weaken
  the blocking rule. Accordingly there is only **one independent complete 1889
  reference replay**, not two. Bankruptcy is covered by a rule-specific scenario;
  a second valid independent bankruptcy recording remains useful additional
  validation. The earlier preimplementation audit's two-replay expectation was
  based on recording metadata, before attempting either replay.

The existing three independent 1830 games and complete 1830 HTTP game remain
part of normal discovery. Passing tests establish these scenarios, not a proof
over every possible play sequence. Browser/frontend gameplay is separate work.
