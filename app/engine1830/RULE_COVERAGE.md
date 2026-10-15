# 1830 rule coverage and validation

> **Review update:** The original and follow-up review defects are corrected.
> Normal discovery includes `test_Engine1830Regressions.py` and
> `test_Engine1830Followup.py`, including the HTTP presidency-transfer regression.
> See [the follow-up validation](../../docs/1830_FOLLOWUP_REVIEW.md).


Specification: `docs/rules1830.rtf`, including its Tables 1–8. The backend is
`app.engine1830`, served by `multiplayer/backend/rules1830_api.py`. The older
`app.state` / minigame code is retained for existing consumers and is not the
implementation covered by this checklist. This work covers 1830; it does not
establish rules completeness for 1846, 1889, or every other 18xx title.

## Numbered rules

Every row below has implementation and automated acceptance coverage. Test names
are in `app/unittests/test_Engine1830.py` (`Rules1830Tests`),
`test_Engine1830Specials.py` (`SpecialRules1830Tests`), or
`test_engine1830.py` (additional independent scenarios). Whole-game tests in
`test_Engine1830FullGame.py` exercise the rules together, through final scoring.

| Rule | Implementation | Acceptance evidence |
|---|---|---|
| 1: objective and ending conditions | `scores`, `_end_game`, `_bank_check` | `test_bankruptcy_ends_immediately_and_scoring`, `test_bank_break_deferred_and_scores_exclude_treasury`; three recorded games |
| 2: setup, $2,400 distribution, separate funds/components | `new_game`, `data`, `board_data`, `validate_state` | `test_setup_all_player_counts_and_money`, `test_setup_component_inventory_and_isolation` |
| 3: stock / operating round sequence | `_start_stock`, `_start_operating`, `_end_corporation` | full public-API game and three reference games |
| 4: one buy, any sales, either order, consecutive passes and priority | `_stock_action`, `_buy_shares`, `_sell_shares` | `test_sell_then_buy_uses_proceeds`, `test_buy_then_sell_same_corporation_is_allowed`, `test_sold_company_restriction_is_per_player`, `test_consecutive_passes_and_priority` |
| 5: corporation operations and treasury | `_operating_action`, `_skip_to`, `_dividend`, `_buy_train` | `test_free_home_token_and_turn_authorization`, `test_float_capital_home_token_and_no_premature_train_use`; recorded games |
| 6: private revenue, player/corporate ownership | `_private_revenue`, `_buy_private` | `test_private_revenue_to_treasury_not_dividends`, `test_other_privates_do_not_discount_and_pay_revenue` |
| 7: first stock round; no certificate sales | `_continue_auction`, `_sell_shares`, `_buy_private` | `test_initial_private_order_and_prices`, `test_no_sales_in_first_stock_round`, `test_private_sales_prohibited_first_round_and_corporate_resale` |
| 7.1: buy offered private, bid later, or pass | `_auction_action` | initial-order, auction-minimum and competitive-auction tests |
| 7.2: original bidders only, minimum $5 raise, escrow and resumption | `_auction_action`, `_award_private`, `_continue_auction` | `test_auction_escrow_raise_and_release`, `test_competitive_auction_and_resume`, `test_auction_minimum_and_reserved_cash` |
| 7.3: SV discount/free acceptance; other privates stay at face value and pay revenue | `_auction_action`, `_private_revenue` | `test_sv_discount_and_forced_free_purchase`, `test_other_privates_do_not_discount_and_pay_revenue`, `test_bidding_keeps_stock_round_open_instead_of_discounting_sv` |
| 8: president certificate first; 10% and 20% certificates; 60% flotation | `_buy_shares`, `_award_private`, `_float` | `test_president_first_and_one_purchase_per_turn`, `test_flotation_capital_only_once_at_or_start`, `test_mh_exchange_can_float_corporation` |
| 8.1: six legal par prices, immutable par, free C&A/B&O stock | `_set_par`, `_award_private` | `test_par_prices_are_exact`, `test_market_movement_does_not_change_par`, `test_ca_free_prr_share_and_bo_presidency`, `test_bo_par_interrupts_auction` |
| 8.2: sale/down, sold-out/up, dividend/right/up, withhold/left/down, marker stacking | `_market_move`, `_stock_action`, `_dividend` | market-edge, fixed-par, sold-out and withhold tests; `test_sold_out_movement_preserves_top_to_bottom_stack_order` |
| 9: president holds greatest percentage; ties preserve incumbent | `_check_president` | `test_presidency_does_not_transfer_on_equal_holdings` |
| 10: five certificates per corporation, total limits, colored-zone exceptions, excess correction | `certificate_count`, `_holding_allowed`, `_stock_action` | certificate-table, yellow/orange/brown, brown-multiple-buy and holding-limit tests |
| 11: flotation and capital once, at first OR; token supply | `_float`, `_start_operating`, `data.CORPORATIONS` | `test_flotation_capital_only_once_at_or_start`, component inventory test |
| 12: no first-round sales, 50% pool ceiling, no president certificate in pool | `_sell_shares` | `test_sale_pays_pre_sale_price_and_pool_limits`, `test_president_cannot_dump_without_successor` |
| 13: presidency exchange without changing percentage ownership | `_check_president`, `_sell_shares`, certificate counting | presidency transfer tests; recorded games with presidency changes |
| 14: successor tie follows seating order, wrapping at last seat | `_check_president` | `test_presidency_transfer_and_wraparound_tie` |
| 15: only bank-mediated stock sales; proceeds before marker movement | `_buy_shares`, `_sell_shares`, `_pay` | `test_sale_pays_before_market_drop_and_sell_buy_allowed`, pool-limit tests |
| 16: operating order by value, rightmost column and marker stack | `_operating_order`, emergency-sale reordering | `test_operating_order_rightmost_then_stack`, `test_tied_market_prices_same_column_use_upper_row_first`, `test_emergency_sale_reorders_remaining_corporations`; exact recorded games |
| 17: ordered operations, no credit, private purchases during corporation turn | `_skip_to`, `_operating_action`, `_buy_private` | rejected early train purchase, late route execution and optional presidential funding; recorded games |
| 18: one lay OR upgrade; reachable track; city types; $80 water/$120 mountain; blocked and permanent hexes | `board.lay_tile`, `board.reachable` | track-terrain, disconnected/city/color, private-block and map-edge tests |
| 18.1: legal upgrades and preserved track, accessible network, returned tiles | `UPGRADES`, `board.preserved_mapping`, `board.lay_tile` | upgrade-preservation, rejected removed-track, tile-recycling and every-Table-6-replacement geometry tests |
| 18.2: OO / NY / B tiles restricted to printed locations | labels and printed-hex checks in `board.lay_tile` | actual OO/NY/B upgrades in recorded games; wrong-city/label rejection |
| 18.3: optional tile laying, including NYC/Erie | operating `skip`, home exceptions in `board.lay_tile` | complete game with skipped construction; Erie home test |
| 19: free home, additional $40/$100 tokens, connectivity, vacancy, reservations, no duplicate token on hex, one extra token | `board.place_token`, `reserved_home`, `reachable`, operating token flag | station-cost, duplicate/unreachable, reserved-home, blocked-city and DH token-limit tests |
| 19.1: Erie chooses either home city; no other tokens there before its base | `home_token`, `board.place_token` | `test_erie_can_choose_either_home_city_and_lay_disconnected`, reserved-home test |
| 20: trains, routes and revenue | `board.validate_routes`, `route_from_paths`, `_dividend` | route suites and reference games |
| 20.1: actual track connectivity, junctions/crossings, no repeated station/track, offboard termini, separate train routes, token on each route, capacity and Diesel length | `board.graph`, `validate_routes`, `node_info`, `blocked` | duplicate/disconnected/shared-track and token tests; `test_two_trains_can_share_city_but_not_track`; reference routes with separate cities in one hex and long Diesel routes |
| 20.2: train mandatory if a legal route exists; acquired trains run next turn | `_end_corporation`, `_buy_train`, ordered operating steps | mandatory-purchase, optional-funding and premature-route-use tests |
| 20.3: all visited stops count; phase-sensitive offboards; dividends to players and pool shares to treasury, IPO shares unpaid; private revenue separately to treasury | `board.validate_routes`, `_dividend`, `_private_revenue` | real-revenue, offboard-phase, dividends-pool-not-IPO and private-treasury tests; exact reference scores |
| 21: finite ordered depot, limits, immediate discards, returned trains, negotiated corporate transfers, Diesel trade-ins | `available_depot`, `_buy_train`, `_discard_train` | depot-order, other-president discard, authenticated train transfer, Diesel rust/trade-in tests, including trade-in at train limit |
| 22: all six train phases, tile colors, limits, rust, private closure, offboards and delayed 1/2/3 OR sets | `_phase_change`, `_stock_action`, fixed `or_total` | `test_phase_changes_rust_close_and_limits`, `test_train_depot_order_phase_rust_and_discard`; every recorded game reaches every phase |
| 23.1: player private sales and corporate purchases at ½–2× face after first 3; no corporate resale | `_offer`, `_agreement`, `_buy_private` | player-sale, seller-consent, corporate-phase/price, first-round and corporate-resale tests |
| 23.2: B&O closes on its first train, M&H closes on exchange, others on first 5; closed privates stop contributing | `_buy_train`, `_exchange_private`, `_phase_change`, `_private_revenue`, `scores` | B&O purchase, M&H exchange and phase-closure tests |
| 23.3: face value only for open player-owned privates; certificate entitlement | `scores`, `certificate_count` | final-scoring and certificate-count tests; full bank-ending game with open privates |
| 24: treasury first, mandatory personal contribution, legal forced share sales, protected affected presidency, negotiated alternative trains, bankruptcy | `_buy_train`, `_sell_shares`, `_bankrupt`, `_pay` | presidential-contribution-not-loan, optional-funding rejection, protected-presidency and emergency-reordering tests; two bankruptcy reference games |
| 25: immediate bankruptcy, unsaleable stock score, bank exhaustion after required OR set, continued bank payouts | `_bank_check`, `_end_corporation`, `_finish_operating_set`, `_end_game`, `scores` | deferred-bank and complete-set tests; exact independent endgame results below |

## Component tables

| Table | Implementation and validation |
|---|---|
| 1: six privates, prices, revenues and powers | `data.PRIVATES`, `_award_private`, `_exchange_private`, special tile/token actions. C&A/PRR and B&O/presidency gifts tested; C&SL extra disconnected lay tested; D&H mountain cost, free immediate token and paid deferred disconnected token tested; M&H limits/timing/closure tested. |
| 2: eight corporations, homes and token counts | `data.CORPORATIONS`; inventory, home, reservation and token tests. Counts exclude the stock-market marker, which is represented separately. |
| 3: total certificate limits | `CERT_LIMITS = {2:28,3:20,4:16,5:13,6:11}`; president counts once; colored zones exempt. |
| 4: train quantities, prices and phase effects | `TRAIN_TYPES`, `PHASES`, `RUSTS`; finite inventory tests and all-phase recorded games. Six Diesels, as printed in this edition. |
| 5: initial personal cash | `new_game`, tested at every supported player count. |
| 6: tile replacements | `UPGRADES` plus independent track preservation. Every allowed pair has at least one preserving rotation; the correction below is explicit. |
| 7: tile inventory | `board_data`, `state.tiles`; all 85 tiles conserved after every action. |
| 8: bank money | $12,000 total is conserved through every accepted action, including bid escrow. Bank may go negative after exhaustion to represent the rulebook's paper IOUs. Physical banknote denominations are not needed for the backend's integer-dollar accounting. |

## Edition decisions and clarified conflicts

- **Table 6 has an inconsistent entry:** its tile 28 row lists 45. No rotation
  of 45 preserves tile 28's track, contradicting §18.1. The backend uses **46**
  instead, which preserves it; 28 → 45 remains illegal. This correction is
  explicit in the component data and has a positive/negative regression test.
- Table 2 includes a market marker in each corporation's token total. The state
  counts station tokens separately: 4/4/4/3/3/3/2/2, with each corporation's
  market position represented by `position`.
- M&H exchange is allowed on its owner's stock turn or in a between-turn window.
  An arbitrary client boolean cannot create such a window during another turn.
- Equal-price, equal-column markers in different rows operate upper row first;
  markers in the same cell use stack order. Forced sales reorder corporations
  that have not yet operated, while keeping the operating corporation's turn.
- Routes are demonstrated by players, as in table play. The backend computes
  every traversed stop's revenue and rejects invalid paths or skipped
  intermediate cities. Route suggestions are bounded and are not represented
  as a guaranteed globally optimal solver. The rulebook does not require other
  players to identify a better route than the one demonstrated.
- Random place-card dealing is represented by caller-supplied seating order;
  passing the same names/actions always reproduces the same game. Shuffle names
  before `new_game` if random seating is desired.

## Independent full-game results

Source: `tobymao/18xx`, revision `46a592e40494368390c9a731978a577ac4ecb1e0`.
The fixtures contain translated public actions, with undo/redo and programmed
client actions expanded into ordinary accepted actions. Test expectations retain
the independent source game's final scores. The Python runtime does not load or
execute the upstream rules engine.

| Source game | Ending | Exact final scores, source player IDs |
|---|---|---|
| `1830_game_end_bank` | Bank exhausted | 15698: 12025; 13430: 13048; 15688: 12109 |
| `29133` | Bankruptcy | 4836: 887; 4631: 1477; 4639: 951; 1668: 416 |
| `26855` | Bankruptcy | 1627: 1831; 82: 2127; 117: 310; 330: 2212 |

Every replay asserts completion, exact score equality, the expected ending,
all phase transitions 3/4/5/6/D, JSON serialization, and the accepted action count.
An additional game is authored directly against this API and checks full-history
replay equality. Game 29133 also executes entirely through the authenticated
ASGI HTTP API and SQLite snapshots, then restores the identical final state.

Transport tests separately cover unauthorized reads, creator-only start,
restart rejection, spectator/creator action rejection, impersonation, illegal
moves, stale revisions, and competing database writers. Rule tests verify
rejected actions leave the original state unchanged. The core's invariants run
after every accepted action, not only at game end.

A passing suite is reproducible evidence for these scenarios and the numbered
rule coverage; it is not a mathematical proof over every possible game state.

## Home progression, saved states and action discovery

`test_Engine1830StateAndActions.py` covers Erie's mandatory home-token choice
before routes/dividends, schema-1 home-city migration and safe token repair,
unknown schemas and blocked repairs, out-of-turn private/train offer discovery,
M&H exchange timing and pending-par/discard interruptions. HTTP cases verify
atomic Erie rejection, migration without a revision change on read, persistence
on the next accepted action and conflict responses for unsupported saves.
