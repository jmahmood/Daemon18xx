# Additional backend edge cases — implementation completed

Completed backend validation record, 2026-10-15.
Scope: standard/full 1889, plus shared 1830 library, restore and HTTP boundaries.
Beginner rules and browser controls remain outside this review.

**All 26 items below are now addressed, with named automated coverage.**
Items group related boundary inputs; the count is not a count of individual tests.

The [261-case inventory](ENGINE_EDGE_CASES.md) now includes `BACKLOG-01` through
`BACKLOG-26`, with exact test names and generated source links. The inventory
maps each completed contract to its executable regressions.

Primary rules: [uploaded 1889 PDF](rules1889.pdf), especially §§4–12 and 15.2.
See [the clause audit](1889_RULEBOOK_AUDIT.md) for edition decisions. The
completion introduced 35 regression tests. The obsolete prototype and its tests
have since been removed; run the README validation commands for the
current backend suite.

## Completion record

The generated inventory's [Backlog section](ENGINE_EDGE_CASES.md#backlog) contains
precise executable test references for every item. The tests live in
[test_EngineBacklogValidation.py](../app/unittests/test_EngineBacklogValidation.py),
[test_EngineBacklog1889.py](../app/unittests/test_EngineBacklog1889.py),
[test_EngineBacklogAPI.py](../app/unittests/test_EngineBacklogAPI.py) and
[test_EngineBacklogRoutes.py](../app/unittests/test_EngineBacklogRoutes.py).

| Completed items | Implementation and validation |
|---|---|
| BACKLOG-01 | Emergency share sales commit 1889 to a depot purchase; matching corporate consent is preserved on rejection. Ordinary affordable transfers remain legal before emergency sales. |
| BACKLOG-02 | Both games liquidate bankruptcy shares in printed corporation order. Reordered JSON inputs produce identical states; 1889 also checks real HTTP/SQLite persistence. |
| BACKLOG-03–05 | Strict revision types and history length; valid lifecycle/order/actor relationships; malformed saves produce controlled RuleError/HTTP 409 responses. HTTP versions reject coercion. Supported legacy migrations remain covered by the full suite. |
| BACKLOG-06–10 | Shared structural validation covers whole-unit bank/escrow, share units/holders/presidency, train uniqueness/status/ownership, station arrays/supply/homes, and complete board/tile catalogs. Balanced corruptions are tested, alongside valid zero/negative bank balances. |
| BACKLOG-11 | Route suggestions accept nonnegative integer limits or None; zero returns no suggestions. Malformed quotation collections and unknown identifiers raise RuleError without mutation in both variants. |
| BACKLOG-12–18 | Regression coverage for last-IPO DR and pool rejection, DR before par, nonzero unpaid dividends/presidency, next OR in the same set, live-auction MF, exhausted ER supply/pass, and 100% emergency holding correction. Last-IPO cases also use HTTP/SQLite. |
| BACKLOG-19–21 | Independent cyclic/junction/crossing optima, explicit foreign-corporation train eligibility, and bankruptcy precedence over a previously broken bank all pass. |
| BACKLOG-22 | Separate ASGI processes synchronize before SQLite writes: concurrent starts and actions yield one commit and one conflict. Lock timeout returns a controlled conflict; the same revision succeeds after release. |
| BACKLOG-23 | Atomic room creation retries collisions up to five times, validates credentials across all roles, rolls back failed partial slot insertion, and returns HTTP 503 after allocation exhaustion or lock timeout without exposing partial credentials. |
| BACKLOG-24 | DR acquires stock and resets stock passes/last transaction; an out-of-turn exchange does not consume another player's turn, and no exchange consumes a normal buy. MF construction is not a stock transaction and changes neither passes nor priority. Own/out-of-turn cases are asserted. |
| BACKLOG-25 | Corrected OPERATING-06, PRIVATE-13 and PRIVATE-18 wording; added matching current rulebook tests to their mappings and regenerated the checklist. |
| BACKLOG-26 | All 18 eligible two-train combinations on the 27-tile late-game board match an independent exhaustive oracle; dictionary-reordered boards give identical results. The batch has a 60-second timeout, with 30 seconds and 128 MiB peak traced Python allocations per position. No approximate fallback is used. |

Structural restore checks require a nonnegative integer revision matching the
history length. There is no new exception that invents missing history. Existing
1830 home inference and 1889 verified emergency-sale recovery still apply.
This validates the listed invariants; it does not replay every complete history
on every state read or claim to authenticate arbitrary caller-provided saves.

The final helper review also tested `limit=None` on runnable networks, exposing
and correcting an 1830 comparison against None that an empty-network test could
not reach. Both variants now exercise zero, bounded and unbounded suggestions
on real paths, with nonzero route quotations and input independence.

Three in-memory fault checks removed the emergency-depot guard, restored
dictionary-order liquidation, or omitted shared share-ledger validation. Each
made its new regression assertions fail. The fault checks changed no files.

The stock-pass decision follows §4.1.1's stock-transaction wording: acquiring an
IPO share through DR is a stock transaction, while laying an MF tile is not.
The special exchange continues to be independent of the ordinary buy allowance.

### Independent route evidence and resource scope

The test-only oracle builds geometry directly from board data, enumerates legal
simple paths and exhaustively combines edge sets. It does not call the engine's
route enumerator, validator, reachability or bitmask allocator. The four small
cyclic/blocking cases have explicit known maxima: 290, 140, 240 and 140.

The real-board base is independent recording 962 immediately before translated
action 471, with 27 laid tiles. Controlled train/phase projections cover all
unordered pairs of 3/4/5 in phase 5, 4/5/6 in phase 6, and 5/6/D in phase D.
Their fixed expected maxima, in that order, are:

- Phase 5: 340, 390, 430, 430, 470, 510.
- Phase 6: 430, 470, 510, 510, 550, 580.
- Phase D: 510, 550, 630, 580, 650, 650.

A diagnostic run took approximately 0.14–1.48 seconds per position with tracing,
with peak traced allocations below 1.5 MiB. These are measured results for this
board family, not a universal resource guarantee for every possible network.
The phase-6/D projections are explicitly **not** independent full-game recordings;
the previously documented complete-recording validation limit remains below.
