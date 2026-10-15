# Follow-up validation of the 1830 fixes

> **Resolution:** Both findings below are corrected. Their reproduction cases
> now run in normal unittest discovery. The findings describe pre-fix behavior.

Reviewed the working tree on branch `1830` against the uploaded
`docs/rules1830.rtf`, especially §§9, 18–21, 24 and Table 1. This is a review of
the uncommitted fixes on top of `deb9684`, not a claim of complete rules coverage.

## Findings

### P1: a longer loop still bypasses the connectivity rules

Location: `app/engine1830/board.py`, `reachable`, lines 130–155.

The new immediate-backtracking check fixes the original I17 junction example,
but the search remembers only `(current vertex, previous vertex)`. It can return
to a junction through a loop, reuse a boundary segment, and then reach the other
branch. Submitted routes correctly reject this repeated track; construction and
station placement incorrectly accept the resulting connectivity.

Reproduction uses an existing C&O railhead in Columbus (H12), with these actual
1830 tiles. All fixture lays and upgrades pass `board.lay_tile`, and the state
passes accounting and component invariants:

| Hex | Tile / rotation | Purpose |
|---|---|---|
| H14 | 7 / 1 | Approach from Columbus |
| G13 | 9 / 2, then 24 / 2 | Junction with the inaccessible branch toward G15 |
| F12 | 8 / 3, then 28 / 5 | Loop junction |
| E13 | 7 / 5 | Loop side |
| F14 | 7 / 1 | Loop side |

With SV corporation-owned so G15 is available, `lay_tile G15, 8, rotation 5`
is accepted even though reaching its connecting edge requires repeating track.
With G15 and H16 constructed as controlled fixtures, `place_token H16` is also
accepted, while `route_candidates` finds **zero** legal routes to H16. This
violates the legal-route requirement in §§18–19 and the no-repeated-track rule
in §20.1.

Required correction: make railhead connectivity obey the same route constraints
as route validation, including earlier visited vertices/segments. Retaining only
the immediately previous vertex is insufficient. Preserve blocked-city and
offboard termination behavior, and verify performance on the recorded games.

At review time, the original connectivity finding was only partially fixed.
The resolution below closes the additional loop case.

### P1: an M&H presidency transfer can deadlock NYC's operating turn

Location: `app/engine1830/engine.py`, `_exchange_private`, lines 895–896;
`_operating_action`, lines 1079–1087.

This reproduction reaches the problem entirely through public actions, beginning
with a new three-player game:

1. Buy the six privates normally; p1 owns M&H.
2. P2 buys NYC's president certificate. P1 and p3 each acquire 20% NYC, so the
   company floats with three tied holdings and p2 retains the presidency.
3. End the stock round. NYC is scheduled to operate with `current_player=p2`.
4. Before the turn begins, p1 legally exchanges M&H for another 10% NYC.

The exchange changes NYC's president to p1 but leaves `current_player=p2`.
P1's next operating action is rejected with "Only the operating president may
act"; p2's is rejected with "Only president may operate corporation". Neither
can progress the game. The real ASGI/SQLite endpoint persists the exchange, then
returns **422** when the new president tries to continue.

Table 1 permits the exchange between railroad turns, and §9 assigns decisions to
the current president. Required correction: synchronize the operating actor when
an exchange changes the presidency of the company whose untouched turn is
scheduled. Preserve the round, order, treasury, home token and operating-step
state; do not start/pay for another turn. Cover transfers affecting the current
company, a future company and an unrelated company.

## Validation performed during review

- The normal suite runs **352 tests, all passed, no skips**, including the three
  independently recorded games with exact scores and the complete HTTP game.
- All nine cases in `test_Engine1830Regressions.py` pass, including the original
  immediate-junction case. Those cases do not cover the longer loop above.
- The malformed-hex HTTP test originally ran in the initial auction, where the
  invalid action was rejected before board lookup. This review strengthened it
  to use the actual operating president during an operating round. Arrays,
  objects, numbers and null return 422 and leave persisted state unchanged.
- `PYTHONPATH=. python tools/validate_1830_followup.py` runs four new
  expected-correct cases: **three assertion failures and one unexpected
  RuleError**, reproducing the two findings above, including the HTTP deadlock.
  This deliberately failing review harness is outside normal discovery. Its
  cases should move into `app/unittests/` alongside the eventual fixes.

The initial follow-up review did not change gameplay. The subsequent fixes and
validation are recorded below.

## Fixes and final validation

- `board.reachable` now retains visited vertices for each candidate path, rejecting
  loops that repeat track or stations. A path dominates another at the same
  directed edge only when its visited vertices are a subset; different legal
  approaches remain available. Blocked cities and offboards remain termini.
- `_exchange_private` updates the active player when NYC is the current operating
  corporation. It preserves the existing turn, treasury, board and operating
  order. Transfers affecting another corporation leave the current actor intact.
- The four original reproductions moved from the standalone review harness into
  `app/unittests/test_Engine1830Followup.py`. Two additional tests cover valid
  construction/token placement through the loop and transfers affecting a future
  or unrelated corporation. The current-company regression also verifies that
  capital, home tokens and operating steps are not reset.
- The complete suite runs **358 tests, all passed, no skips**, including all three
  recorded games with exact final scores, the full HTTP game, and the new HTTP
  presidency-transfer regression. The standalone failing harness has been removed.

These results establish regression coverage for the reported cases, not a proof
that every possible 1830 game state is correct.

## Other known unfinished work

The existing frontend still lacks complete 1830 stock/operating controls. The
separate 1889 backend is still unable to execute a full game; its stock/operating
loop, map/configuration, isolation and variant-rule requirements remain in
`docs/1889_VALIDATION.md`. These 1830 fixes do not resolve either workstream.
