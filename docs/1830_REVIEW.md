# 1830 review: confirmed missing behavior

> The follow-up review identified a further connectivity case and an M&H
> presidency-transfer deadlock; both are now corrected. The findings below
> describe historical behavior. See [the follow-up validation](1830_FOLLOWUP_REVIEW.md).

Reviewed branch `1830`, commit `deb9684`, against `docs/rules1830.rtf` and the
actual implementation at that commit. **The findings below describe the pre-fix state.** The existing
full-game recordings are useful regression coverage, but their passing results
do not exercise the cases below. The earlier completeness claim needs to be
qualified by these findings.

The initial review did not change gameplay. Its original standalone regression
script (now promoted to `app/unittests/test_Engine1830Regressions.py`) expressed expected-correct behavior in eight
focused cases. On the reviewed commit, all eight fail: four assertions fail and
four actions raise unexpected exceptions. Some cases share a root cause; there
are six distinct findings.

## P1: bankruptcy can become an unrecoverable dead end

Location: `app/engine1830/engine.py`, `_bankrupt`, lines 1031–1042.

The calculation of available emergency funds assumes that the affected president
can sell down to 20%. Retaining 20% does not necessarily preserve the presidency:
if another player holds 30%, the president must retain at least 30% (§24.3).
`_sell_shares` correctly refuses a sale that transfers the affected presidency,
but `_bankrupt` counts its proceeds anyway.

Reproduction: president owns 40%, another player owns 30%, remaining 30% is IPO;
market price is $67; treasury and president's cash are zero; cheapest depot train
is $80. Selling 10% raises $67 and leaves both players at 30%. Another sale is
correctly rejected because it would transfer control. Buying the $80 train is
impossible, yet bankruptcy is rejected because the calculation counts another
$67 that cannot legally be raised. The corporation also cannot end its turn.

Required correction: compute liquidation value using exactly the same presidency
and pool restrictions as an actual forced sale. Use that legal valuation for the
bankruptcy decision. Test the boundary with a tied replacement shareholder and
with cash immediately below the cheapest train price.

Regression: `test_bankruptcy_allowed_after_all_legal_stock_sales`.

## P1: reserved home cities do not follow upgrades

Locations: `app/engine1830/board.py`, `reserved_home`, line 160 and home placement
in `place_token`; `app/engine1830/engine.py`, `_start_corporation`, line 667.

The code assumes that every non-Erie home is city index 0. A legal upgrade of
New York G19 to tile 54, rotation 0, maps old city 0 to new city 1 and old city 1
to new city 0. Existing tokens are transferred, but the unplaced NYNH home
reservation is not. The reservation and automatic home placement still target
new city 0 instead of new city 1 (§§18.1, 19).

If C&O already occupies old city 1, the legal upgrade moves its token to new
city 0. Once NYNH floats, ending the stock round raises `No vacant station
position` even though the correct reserved home, new city 1, is vacant. This
blocks the transition into the operating round. Without the C&O token, NYNH is
silently given the wrong base city instead.

Required correction: maintain home reservations as persistent city identities
and transform them using the same mapping as station tokens on every upgrade.
Use the resulting city for home placement and reservation blocking.

Regressions: `test_unfloated_home_reservation_follows_city_mapping` and
`test_home_upgrade_cannot_deadlock_end_of_stock_round`.

## P1: city mapping merges separate cities and moves Erie's base

Location: `app/engine1830/board.py`, `preserved_mapping`, lines 221–244.

The mapping generator uses a Cartesian product and accepts non-injective
mappings even when old and new tiles both contain two separate cities. For
example, tile 59 rotation 0 to tile 64 rotation 0 returns `[0, 0]`: both old
cities become the same new city. Track and station identities are consequently
not preserved (§§18.1–18.2).

An even simpler public-action reproduction violates Erie's explicit rule that
its chosen base may not move (§19.1): choose city 1 as Erie's home before laying
a tile, then lay tile 59 in rotation 0. Both original printed cities have no
exits, so the first accepted mapping is `[0, 0]`; Erie's token is moved from
city 1 to city 0. The existing Erie test always lays a tile before choosing the
home, so it misses this legal order of play.

Required correction: preserve separate city identities when city counts are
unchanged; preserve printed city identity when placing the first tile; permit
merging only where an explicit legal replacement actually merges cities.
Check city mappings independently of current occupancy, so adding tokens does
not change which rotations the rules consider legal.

Regressions: `test_separate_cities_cannot_collapse_on_upgrade` and
`test_erie_base_does_not_move_when_first_tile_is_laid`.

## P1: reachability permits an illegal reverse across a junction

Location: `app/engine1830/board.py`, `reachable`, lines 143–150.

The traversal prevents changing branches directly at an edge on one tile, but
allows crossing a hex boundary and immediately walking back. That backtrack
can then enter another branch. The route validator correctly rejects this
repeated-track maneuver; the station/construction reachability test accepts it.
A legal station must be connected to a railhead by a legal route (§19), not just
by this reversed walk.

Reproduction from B&O's base: lay tile 9 at I17, rotation 1; in a later turn,
upgrade it to tile 23, rotation 4. Its paths are edge 4–1 and edge 4–2. The
traversal reaches edge 2 by walking toward I19 and immediately reversing over
the same boundary. The code accepts tile 57 at H16, rotation 2, and then a B&O
station there. Before placing that station, enumerating every simple legal
route on this small network finds only I15–I19: none reaches H16. The station
has been placed without a legal connection to the original railhead.

Required correction: use consistent directional/path traversal constraints for
route validation and network reachability. Prevent reverse/repeated-track walks
from creating otherwise inaccessible token or construction locations.

Regression: `test_token_connectivity_cannot_reverse_across_junction`.

## P2: emergency private-company sales are missing

Location: `app/engine1830/engine.py`, `_buy_private`, lines 995–1003.

Section 24.3 explicitly allows the president to sell a private company to a
willing buyer immediately during an operating round to fund a required train.
It is optional, unlike the obligation to raise funds through permitted stock
sales. The current handler requires every player-to-player private sale to occur
in a stock round, so this funding option cannot be used.

Reproduction: B&O has a runnable route but no train or cash; its president owns
D&H. Another player records an authenticated offer to buy D&H for $100.
Accepting that offer during the required train-purchase step raises
`Player sales only after first stock round`, even in stock-round set 2. The
quoted error hides the actual issue: the current round is an operating round.

Required correction: add the §24.3 exception while retaining real counterparty
consent, available cash, certificate limits, ownership, and the current
president's authority. Do not enable unrelated player private trades during
arbitrary corporation turns.

Regression: `test_emergency_private_sale_is_permitted_by_section_24`.

## P2: malformed hex parameters escape rule validation

Locations: `app/engine1830/engine.py`, `apply_action` field validation at lines
1268–1285; `app/engine1830/board.py`, `lay_tile`, line 249.

`hex` is omitted from the action's validated string fields. A JSON action with
`"hex": []` reaches a dictionary lookup and raises `TypeError: unhashable type:
'list'` rather than `RuleError`. The HTTP adapter catches `RuleError` and
`ValueError`, so this becomes an internal server error rather than a structured
422 rejection. The input game state remains unchanged, but the endpoint's
validation contract is broken.

Required correction: validate coordinates and all structured action parameters
before lookup, returning a rule/schema error for malformed client input. Add a
real HTTP negative test as well as the pure-engine regression.

Regression: `test_malformed_hex_is_a_rule_error`.

## Checks actually performed

- Existing suite, with installed backend dependencies:
  `python -m unittest discover -q`: **342 passed, no skips**.
- Fresh review regressions:
  `PYTHONPATH=. python tools/review_1830_regressions.py`: **8 cases failed**,
  reproducing the six findings above. This script deliberately exits nonzero
  until the reviewed behaviors are corrected; it is outside normal test
  discovery so the baseline result remains distinguishable from new failures.
- Rulebook text was extracted from the uploaded RTF and compared for the cited
  sections, particularly §§18–19 and §24.
- Source changes, test fixture behavior, city mappings, and actual public
  `apply_action` results were inspected. Mid-game setups use the same controlled
  fixture helpers as the existing unit suite; these are not claimed as extra
  complete-game recordings.

The existing frontend is also still the earlier 1889 client and has no complete
1830 stock/operating controls, as already documented. A browser-playable 1830
application remains separate work from correcting these backend defects.

## Resolution

Initial fixes on branch `1830` address all six original reproductions. Follow-up
validation identified an additional connectivity case, now corrected as
documented in the follow-up review:

- Bankruptcy funding and liquidation use the same legal share-sale validation,
  including retention of the affected presidency when another holder has 30%.
- Home-city reservations and automatic home placement follow upgrade mappings.
- Equal-count city upgrades preserve separate cities; initial Erie construction
  preserves the chosen base city.
- Reachability rejects immediate reversal across a hex boundary, protecting both
  construction and station placement at the reported junction.
- Mandatory emergency funding permits a consensual private sale to another
  player without advancing the stock turn. Ordinary operating-round trades,
  affordable purchases, and missing counterparty consent remain rejected.
- Malformed hex coordinates raise `RuleError`; HTTP returns 422 without changing
  persisted state or revision.

The original eight regression cases now run under normal unittest discovery,
with an additional emergency-sale restriction test and an HTTP malformed-input
persistence test. Passing these checks does not establish that no other defects
exist, nor does it complete the separate frontend or 1889 work.

Validation after fixes: `/workspace/.venvs/daemon18xx/bin/python -m unittest
discover -q` ran **352 tests, all passed, no skips**, including all three recorded
games with exact final-score checks and the complete ASGI/SQLite game.
