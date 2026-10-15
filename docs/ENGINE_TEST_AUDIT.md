# Iterative 1830 / 1889 backend test audit

Scope: the pure Python standard 1830 and Shikoku 1889 engines and their
authenticated HTTP/SQLite backends. The case inventory is a finite set of reviewed
rule boundaries and failure modes; it is not a proof over every possible game.

## Audit loop

1. Added exact certificate-limit purchase/pass/correction boundaries for every
   player count in both engines, same-controller ER sale/lay/pass restoration,
   and MF corporate-sale power removal. All passed.
2. Measured engine/board branch coverage and reviewed unexecuted paths. Added
   malformed-save metadata/invariant cases, changed-president train consent,
   failed-purchase offer retention, all-count HTTP auctions, metadata conflicts,
   and injected database commit failure with rollback and same-revision retry.
   The metadata tests initially failed: 1830 accepted another variant's tag;
   schema validators and the 1889 migration accepted boolean/float versions.
   Added variant guards and strict integer schema checks. Regressions passed.
3. Added complete authored 1889 games at 2, 3, 5 and 6 players, with restoration
   during play and after completion. Added route quotations from paths/vertices,
   skipped routes versus runnable trains, required dividend/train steps, and
   auction/terminal action discovery. These passed after correcting two test
   assumptions: advisory discovery may also offer negotiations; a newly purchased
   train cannot normally be present before routes in the same operating turn.
4. Added wrong-round/unknown action rejection in all three rounds for both
   variants, plus 1889 action-alias result/history equivalence. All passed.
5. Coverage review added corporate-train presidential funding: 1830 permits
   assistance up to face value; 1889 forbids it. Both variants retain consent
   on rejection and allow a subsequent treasury-funded purchase. Added Erie
   action-discovery assertions before the initial track skip. These pass.
6. Added the remaining reachable coverage scenarios: competitive B&O auction
   award followed by restored par interruption, partial 1830 legacy home metadata,
   and a contiguous route quotation that fails to end at a revenue center.
   All pass.
7. Re-ran the full suite and reviewed the remaining coverage branches. See the
   validation results and residual-path classification below.

The new suite is [test_EngineCoverageLoop.py](../app/unittests/test_EngineCoverageLoop.py).
The [inventory](ENGINE_EDGE_CASES.md) contains **202 reviewed cases**: 178 unit
cases and 24 HTTP/replay integration cases. Its discovery check verifies every
named test exists and the readable checklist matches its JSON source. Assertions
were also reviewed; a valid test name alone does not establish rule coverage.

## Complete authored 1889 scenarios

| Players | Accepted actions | Ending | Final phase | Expected player scores |
|---|---:|---|---|---|
| 2 | 720 | Bank | 5 | 145, 145 |
| 3 | 813 | Bank | 5 | 110, 90, 105 |
| 4 (existing) | 1,566 | Bank | D | 2725, 2787, 4442, 2741 |
| 5 | 502 | Bankruptcy | 6 | 20, 615, 80, 100, 90 |
| 6 | 109 | Bankruptcy | 4 | 445, 230, 375, 390, 395, 400 |

These fixtures were authored exclusively with accepted public actions against the
Python engine. They provide deterministic regressions and full-loop coverage at
every player count. They are **not independent reference recordings**. Tests
check fixed scores/endings, conservation invariants after each accepted action,
restoration, terminal action rejection, and required OR-set completion for bank
endings. The existing four-player game also operates all seven corporations and
reaches every phase.

## Validation

- Final stable full discovery: **543 tests passed, no skips**, in 56.605 seconds
  on Python 3.12. All 18 new test methods and their player-count, variant and
  failure subcases are included. The final instrumented additions also pass.
- Controlled faults: the certificate-boundary test rejects **22 of 22** deliberately
  wrong settings: all counts using the three-player limit in each engine, and
  each of the ten variant/player-count limits changed by either +1 or -1.
  Faults were injected temporarily in memory; production tables were restored.
- The 202 inventory references and generated document pass their consistency
  checks. Changed Python files parse with Python 3.8 syntax; runtime is Python 3.12.
- `git diff --check` passes.

Reproduce ordinary validation from the repository root with
`python -m unittest discover -q` and `python tools/render_edge_cases.py --check`.
Optional instrumentation uses `coverage run --branch
--source=app.engine1830,app.engine1889 -m unittest discover -q` followed by
`coverage report -m`; coverage is a development tool, not an engine dependency.

## Measured paths and closure criterion

Coverage includes both engines, boards, catalogs and rule errors, measured with
branch instrumentation across full discovery and the final targeted additions.
No source lines or branches were excluded from the measurement.

| Core module | Statements | Branches |
|---|---:|---:|
| 1830 controller | 838/840 (99.76%) | 321/324 (99.07%) |
| 1830 board | 316/320 (98.75%) | 135/140 (96.43%) |
| 1889 controller | 824/831 (99.16%) | 294/304 (96.71%) |
| 1889 board | 317/322 (98.45%) | 132/138 (95.65%) |
| All measured core modules | 2345/2363 (99.24%) | 892/916 (97.38%) |

Remaining unexercised paths were reviewed rather than hidden with coverage
exclusions:

- Generic mapping alternatives that remove, merge or change node types are
  blocked by standard tile replacements or the construction node-kind guard.
- A queued reachability path becoming superseded is a defensive check; the
  breadth-first queue processes shorter paths before longer supersets. Capacity
  overflow after leaving a revenue node is likewise prevented by the earlier
  stop-capacity check. Public reachability/capacity boundaries have assertions.
- Moving an un-parred market marker and dispatching an unknown saved round are
  defensive internal cases outside states produced by accepted standard actions.
- Standard 1889 has no brown stock zone, B&O par interruption or schema other
  than its current schema 1. Those inherited compatibility branches cannot be
  reached in standard 1889 play. Its home-placement fallback runs after normal
  OR initialization has already placed all floated companies' homes. The simple
  internal `train_limit` compatibility helper is not called by the tested public
  API; actual train-limit changes and enforcement are tested.
- 1889's catalog has no encoded impassable-border entries using the generic
  decoder branch; map borders and illegal crossings are tested through actual
  board construction. The 1830 auction completion check has an infeasible
  pending-par exit because that interruption already returned earlier.

The closure criterion is that every identified rule/transport boundary has
reviewed assertions, the complete suite passes, and no remaining executable
coverage path reveals another standard-game rule scenario requiring a test.
No unaddressed rule-boundary case remains in this audit's 202-row inventory.
This is deliberately narrower than claiming every possible game or malformed
JSON object has been tested. The independent-evidence limits below still apply.

## Evidence limits

There is one valid independent complete 1889 reference game (962), ending in
phase 5. A valid independent bankruptcy or phase 6/D recording would strengthen
integration validation; authored fixtures do not close that independence limit.
Historical game 314 contains an illegal blocked-city route and remains an
explicit rejection regression. No 1889 rulebook PDF was uploaded; the pinned
G1889 reference and standard full-game scope remain as documented in
[1889 coverage](../app/engine1889/RULE_COVERAGE.md).

Browser integration, beginner variants, 1846, load testing and a guaranteed
optimal-route solver are outside this backend test audit. No claim of 100%
branch coverage or exhaustive correctness is made.
