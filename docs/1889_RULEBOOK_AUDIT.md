# 1889 uploaded-rulebook implementation audit

Authority: the user-uploaded Japanese translation, retained as
[rules1889.pdf](rules1889.pdf), 26 pages, PDF creation date 2020-05-24.
SHA-256: `e3bd7adb8f842d175009334ca4875a644768521013d245b6f20b1731a8bc2eb4`.
The user confirmed the standard/full game for 2–6 players; §16's optional
beginner game is excluded. Section and page citations use the printed rulebook.
The pinned G1889 implementation is a secondary cross-check. The uploaded rules
supersede the earlier audits' assumption that no 1889 rulebook was available.

## Implementation loop and closed tasks

Each pass compared rules with executable behavior, added failing regressions for
new findings, implemented fixes, executed the tests and compared the rules again.

| Pass | Newly identified tasks | Result |
|---|---|---|
| 1 | Pay capital at the fifth IPO share (§5.6.4); clockwise competitive auctions (§5.7); emergency correction of excess holdings (§10.6.2); retain private value at bankruptcy (§12.1). | Regressions failed before changes and pass afterward. |
| 2 | Require usable new track/revenue change on upgrades (§6.2); start public-stock play left of the last private purchaser (§5.7); permit MF during the initial auction (§15.2). | Implemented and tested, including rejection atomicity and saved-game restoration. |
| 3 | Permit route corrections before dividends and lock afterward (§8.3); provide an exact combined-train maximum, rather than bounded suggestions. | Added `best_routes` and `run_best_routes`; tested global allocation, Diesel values, empty/zero routes, identity and HTTP persistence. |
| 4 | MF throughout its owner's operating turn; DR exchange during stock/operating turns, immediate presidency transfer, and orange-zone holding exemption (§15.2). | Added failing regressions and corrected timing/ownership policies. Forced interrupts still take precedence. |
| 5 | Update priority after private-only pass cycles (§5.7); make optimizer output independent of dictionary order; handle identical and excess unrunnable trains. | All targeted regressions pass. |
| 6 | Recompare all numbered rules and rerun both games' full acceptance suites. | Full suite passed 565, then 566 tests. |
| 7 | Final source review: auction order and final-private priority must survive JSON key reordering. | New failing regression corrected with canonical printed-company order; final full suite rerun. |
| 8 | Review private abilities between route declaration and dividend: ER changes stop values, and MF can create a route after an empty claim. | Reproduced four failing subcases; payments now revalue nonempty claims and reject empty claims when trains can run. Paid dividends remain final. |
| 9 | Independently check allocation and remaining recent-change interactions. | A branch-based oracle matches all 320 combinations of stop values, train mixes, railheads, city blocking, grouped offboards and Diesel values. Added a known optimum beyond the first 100 suggestions, invalid correction atomicity and DR flotation during another operation. No additional rules defects found. |
| 10 | Exercise both fixes through authenticated HTTP/SQLite and restore; fault-check regression assertions. | Both transport scenarios pass, including wrong actor, stale retry and rejected-action persistence. Removing either production fix in memory causes its regression assertions to fail. |
| 11 | Recheck MF after an already-paid zero dividend, with and without an owned train. | Payment/route correction stays locked; a newly connected trainless corporation must buy a train before ending its turn. Both boundaries pass without further code changes. |
| 12 | Implement the 26-item review backlog with strict restore/ledger contracts, emergency depot commitment, deterministic bankruptcy and DR/MF stock-pass policy. | Named unit and HTTP regressions cover every item; existing 1830 and 1889 rules/migrations remain in full discovery. |
| 13 | Independently validate cyclic and late-game routes; test process-level persistence, allocation collisions and lock retries. | Four known cyclic/blocking maxima and all 18 eligible late-game train pairs agree with a separate exhaustive oracle; separate ASGI workers produce one SQLite commit and one conflict. |
| 14 | Recheck helper tests on runnable paths instead of empty networks, refresh the inventory and run final discovery. | Corrected the 1830 unbounded-route comparison; both variants cover zero/bounded/unbounded limits and nonzero quotations. |

The rulebook tests are in
[test_Engine1889Rulebook.py](../app/unittests/test_Engine1889Rulebook.py), with
follow-up interactions and the independent allocator oracle in
[test_Engine1889InteractionAudit.py](../app/unittests/test_Engine1889InteractionAudit.py).
The [executable inventory](ENGINE_EDGE_CASES.md) now maps **261 cases**:
227 unit cases and 34 HTTP/replay cases. It checks that all named test references
exist and its readable checklist matches the JSON source.
The [resolved backlog](ENGINE_EDGE_CASE_BACKLOG.md) records the new contracts,
individual completion evidence, resource bounds and remaining reference limits.

## Clause-to-implementation comparison

The test column gives representative executable evidence, supplemented by the
inventory's named edge cases and whole-game replays. `Rules1889Tests` lives in
`test_Engine1889.py`; `Rules1889EdgeTests` in `test_Engine1889Edges.py`.

| Rules | Implemented behavior | Representative evidence |
|---|---|---|
| §§1–2,2.1–2.3 | Standard game, public corporation/private certificates, market, board and revenue data. | `test_setup_all_player_counts_and_complete_components`; catalog generation and API tests. |
| §2.4 | ¥7,000 includes starting money; negative bank balances represent continued payments after exhaustion. | All-count setup, money invariants after every accepted action, `test_bank_break_zero_negative_payouts_and_required_or_set_completion`. |
| §§2.5,18 table 1 | Six 2s, five 3s, four 4s, three 5s, two 6s and unlimited Diesels; exact prices. | Component tests, depot-order tests, `test_diesel_revenue_uses_train_type_and_supply_is_unlimited`. |
| §§2.6,6.6,21 | Standard finite tiles, upgrades and recycling. Translation omits the full tile chart; pinned component data supplies it. | Supply/recycling tests, catalog importer, full-map recordings. |
| §§3.1–3.2 | Deterministic caller-supplied seating/IDs represent the dealt seat order; players and components are isolated. | `test_custom_ids_trimmed_names_and_nested_state_independence`; dual-engine isolation. |
| §§3.3,18 table 2 | ¥420 at 2–4 players, ¥390 at 5–6; certificate limits 25/19/14/12/11; omit SIR at two, UTF below four. | All-count setup and exact certificate-boundary tests. |
| §§3.4,14 | Player holdings and money inspectable; optional tabletop secrecy and etiquette are discussed below. | Authenticated state views, credential isolation, actor and role tests. |
| §§4.1.1,5.2.1–5.2.2 | Clockwise stock turns, consecutive passes and priority left of last transaction. | `test_consecutive_passes_priority_and_no_floated_corporations`. |
| §4.1.2 | Private income first; corporation order by price/rightmost/stack; track, token, routes, dividend, train sequence. Private purchases during own phase-3/4 operation. | Operating-order/step tests, all-phase game, private-purchase tests. |
| §§4.2.1–4.2.6 | All six phases, colors, train limits, rust, private closure, Diesel availability and train-specific offboards. OR-set length changes after the next stock round. | Phase/rust/limit tests and authored game through every phase. |
| §§5.1.1,5.4.1 | Yellow/orange certificate exemptions; orange ownership exemption; president certificate counts once; correct excess before passing. | Color/certificate tests; every count's exact buy/pass boundary. |
| §§5.1.2–5.1.4 | Immutable par versus current market, separate IPO/pool, explicit round state. | `test_stock_pool_uses_market_price_ipo_uses_fixed_par`; actual market-move tests. |
| §5.2.3 | Sold-out movement in descending operating order and correct marker stacking. | `test_sold_out_rise_does_not_change_par_or_stack_order`; shared sold-out stacking regressions. |
| §§5.3.1–5.3.3 | One certificate buy; sell blocks at pre-sale price; sell–buy or buy–sell, not sell–buy–sell; no rebuy after selling that round. | Purchase/source/price/order/block tests. |
| §5.4.2 | Pool cannot reach 60%: maximum 50%. | `test_stock_sale_pool_cap_ownership_units_and_president_protection`. |
| §5.5 | 20% president certificate remains with a player; larger holding succeeds, incumbent wins ties, clockwise successor tie-break. | Presidency transfer/tie/wrap tests; DR mid-operation transfer regression. |
| §§5.6–5.6.3 | President first, exact par choices, 50% IPO threshold, independent corporate accounts; homes at first OR start. | Setup/par/float/home tests and complete-game replays. |
| §5.6.4 | Full capital paid immediately when the fifth share leaves the IPO; funded once. | New capital/stock-bankruptcy-trigger tests and real HTTP/SQLite flotation test. Older unfunded saves retain a first-OR fallback. |
| §5.7 | Ordered private auction, bid escrow, minimum +¥5, original bidders only, clockwise after high bidder, refunds, resumption, private-only income/discount/free purchase, no first-round share sales. Last private buyer determines first public actor. | New clockwise/last-winner/priority tests plus updated shared and HTTP auctions. |
| §§5.8.1–5.8.4 | Ragged market, boundary arrows, sold-out rise, sale drop per 10%, payout/withhold movement, bottom-of-stack arrival. | Market-boundary, dividend, sale and stacking tests. |
| §§6.1–6.2 | One normal tile, home/network connectivity, preserve every path/station, next color/labels, usable new track or reachable revenue change. | Track tests; new disjoint-path and junction-reversal rejection, legal new branch, revenue-only upgrade. |
| §§6.3–6.4 | No off-map/blank-gray/water exits; match cities/towns and special labels. | Exit/border, printed-type, permanent-hex and label tests. |
| §6.5 | Pay terrain on construction; no repeat ordinary terrain cost; repeat Kotohira H-city cost; SMR pure-mountain exemption only. | `test_smr_only_discounts_pure_mountains_and_h_costs_repeat`; insufficient treasury tests. |
| §§7.1–7.3 | Free home at first OR start, at most one extra station per operation, connectivity/reservations/vacancy, fixed ¥40 extra token, no removal, full rival cities block through running. | Home, token-supply/cash/reservation and topology suites. |
| §§8.1–8.2 | Simple connected routes; own station; two or more stops within train capacity; no shared track, reversal or through-running at blocked cities/offboards. Distinct track through one hex and shared cities across trains remain legal. | Topology suite, real blocked-I2 rejection, seven-stop Diesel regression. |
| §8.3 | Sum all traversed stops; train-specific Diesel revenue; exact global allocator; replace unpaid route claims; paid claims locked. | New allocator/correction tests, identical 2-trains, global 310-versus-greedy-210 example, Diesel assignment, zero revenue and dictionary-order determinism. Route policy is stated below. |
| §§9.1.1–9.1.4 | All payout or all withhold; pool dividends to treasury, IPO portion retained by bank; no/zero revenue moves left. | `test_dividends_pool_versus_ipo_withhold_and_zero_revenue`; payout/cash/par tests. |
| §§10.1–10.2 | Mandatory train only with a route; phase limits; discard only when required. | Mandatory/optional funding, train limit, multi-president discard and restoration tests. |
| §§10.3–10.5 | Rust events, finite depot order, returned trains, fixed bank price, agreed corporate transfer at ¥1+, Diesel trade-in 4/5/6 for ¥300. | Depot/rust/consent/price and exact ¥800 trade-in boundary tests. |
| §§10.6–10.6.2 | Treasury first; necessary personal funds and stock sales; cheapest bank/pool train; no subsidized corporate transfer or emergency presidency swaps. Forced sale outside orange corrects excess to 60%. | Existing emergency suite plus new excess-correction/orange tests. |
| §10.7 | A corporation may sell its last train. | Negotiated transfer tests where seller loses its sole train, with exact ownership/payment assertions. |
| §§11.1–11.4 | Player-to-corporation private sales only in phases 3/4 at ½–2× face, authenticated consent, revenue to current owner, closure at first 5 except player UTF. | Private-sale, income, ownership, UTF and authenticated ER tests. |
| §§12.1,13 | Bankruptcy immediate only if legal funding insufficient; unsaleable shares and remaining open privates retain value; bankrupt player may win. Corporate treasury excluded. | New bankrupt-winner/private-value regression, final scoring and full bankruptcy games. |
| §12.2 | Bank exhaustion remains triggered after replenishment; finish normal OR set even if trigger occurs during stock. | Bank/set tests plus new immediate-flotation bank trigger. |
| §§15.1–15.2, TR | Private certificates count; player-owned TR/ER block construction; corporate/closed ownership removes block. | Blocking/ownership tests and private income/certificate tests. |
| §15.2, MF | One permanent port at an unbuilt B11/G10/I12/J9; owner only, no connectivity, no closure; initial auction, stock and own OR allowed, another player's active OR excluded. | New initial-auction/all-own-step tests; existing wrong-owner, one-use, permanent tile and forced-interrupt tests. |
| §15.2, ER | Seller immediately resolves green C4 opportunity, pays cost, then original president resumes; normal lay retained. | Pure-engine/HTTP interrupts, same-owner seller/buyer tests and restore cases. Optionality clarification below. |
| §15.2, SMR | Pure-mountain discount; river/mountain and H-city costs remain payable. | Real-map construction-cost tests. |
| §15.2, DR | Exchange for IPO IR 10%, close private; no ordinary purchase consumed; can act during stock/OR turns; ordinary holding/certificate exemptions apply; current IR president changes immediately. | New out-of-turn stock/mid-operation/orange regressions plus source/limit/ownership tests. |
| §15.2, SIR/UTF | Correct player-count filtering; UTF player survival, ¥50 income and post-5 sale ban; corporate UTF closes. | All-count setup and UTF survival/value/income/closure tests. |
| §15.3 | Seven correct homes and token supplies. | Component and all-floated-home tests. |
| §§17–20 | Rules/errata precedence, setup tables and terminology; credits/history are not game actions. | This audit, data definitions, component and setup tests. |

## Route and edition decisions

The default follows §8.3's tabletop procedure: the president declares routes,
may correct them before the dividend decision, and is responsible for maximizing
revenue. `best_routes(state, corporation)` supplies an exact maximum and
`run_best_routes` submits it as an authenticated action. Payments lock the claim;
subsequent route changes reject atomically. Submitted manual claims are checked
for legality, not automatically rejected for being suboptimal. Automatic
optimality rejection was offered as a preference question; without an answer,
the existing tabletop model is retained rather than silently changing it.

Private abilities may change the board before payment. Dividends recompute
nonempty claims using the current stops, and an earlier empty claim no longer
suffices if an MF port has made an owned train runnable. The president must
submit routes before paying. A port after an already-paid zero dividend keeps
that payment final, but a trainless corporation must buy a train if the port
creates a route. Pure-engine and HTTP/SQLite regressions cover these boundaries.

The exact solver enumerates all legal simple routes without a suggestion-count
limit, then jointly allocates disjoint track among trains. It handles shorter
routes improving the total, identical trains, Diesel-specific offboards, unused
trains, zero revenue and independent return values. Paths are canonicalized so
dictionary reordering cannot change an automatic action's replay. Dense late-game
networks can make this exact combinatorial search expensive. It is invoked by
explicit computation/action, not every state read.

The uploaded §5.7 explicitly specifies clockwise competitive bidding. This
supersedes the earlier pinned implementation's lowest-bidder policy for **1889
only**; 1830 behavior remains unchanged. §15.2 likewise does not restrict MF to
its owner's track step or DR to turn boundaries. These restrictions were removed.
ER is treated as an optional special ability, consistent with the original
English description's “may immediately place” and pinned special-track pass
behavior; the Japanese ability description omits that optional phrasing. Passing
still resolves the immediate interrupt, rather than postponing the ability.

Caller-supplied seating models the physical seat-card draw without adding random
state to a deterministic core. Physical component arrangement, note keeping,
optional corporate-cash secrecy and social etiquette (§14) are not additional
backend actions. Browser integration and beginner rules are outside this scope.
The translation labels §21's tile chart as omitted, so complete map/tile geometry
continues to use the pinned, licensed G1889 component catalog.

## Validation and reference recordings

- The 24 new rulebook tests pass, including authenticated HTTP/SQLite, restoration,
  actor checks, terminal restrictions, global allocation and money conservation.
- Nine follow-up interaction tests cover the two dividend fixes, invalid route
  replacements, DR flotation/bank exhaustion, paid-zero MF/train obligations,
  the 320-scenario independent oracle and the beyond-100 optimum. Two use real
  authenticated HTTP/SQLite with full library-state comparison after each action;
  their starting board/holdings are seeded fixtures, not independent game records.
- Three in-memory fault checks omit each dividend fix or cap exact allocation at
  100 routes. Each causes the corresponding regression's value/rule assertions to
  fail. Production files are unchanged by these fault checks.
- The six-player authored bankruptcy score changes from p2=230 to **260**:
  §12.1 retains MF's ¥30 face value. Its action history is unchanged. Other
  authored and independently recorded final scores remain unchanged.
- Three independent 1830 complete replays and its complete HTTP game remain in
  discovery. 1889 game 962 still replays to its recorded final scores through
  both the library and authenticated HTTP/SQLite.
- A supplementary exact-route scan found game 962's translated action 304 claims
  120 where 140 was possible. Its recorded payout remains final under the
  tabletop policy; it is not evidence that every source route was optimal.
- Historical game 314 still has an illegal blocked-city route and remains a
  rejection regression. An independent 1889 bankruptcy/phase-6/D recording would
  strengthen cross-validation; authored full games already cover both endings,
  all phases, all seven corporations and all supported player counts.

Rulebook, interaction and backlog regressions remain in the backend suite.
The obsolete prototype and its tests have been removed; historical aggregate
test counts no longer describe the current repository.
Reproduce with `python -m unittest discover -q`. Both games' complete acceptance
and HTTP suites remain in discovery. No further implementation or missing-test
defects were identified in the follow-up scope; the independent-recording limit
above remains additional validation work rather than an uncovered rule boundary.
The 261 inventory mappings/generated-document check passes, changed Python files
parse under Python 3.8 grammar, formatting checks pass, and `git diff --check`
reports no whitespace errors. Passing this finite audit is not a mathematical
proof over every possible play sequence.
