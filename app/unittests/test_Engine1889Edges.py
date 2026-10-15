"""Isolated 1889 boundary cases supplement the complete-game recordings."""

import json
import unittest
from copy import deepcopy

from app.engine1889 import (
    new_game,
    apply_action,
    migrate_state,
    legal_actions,
    scores,
    RuleError,
)
from app.engine1889 import engine as E, board as B
from app.engine1889.data import MARKET, BOARD_DATA
from app.unittests import test_Engine1889 as fixtures


class Rules1889EdgeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Rules1889Tests("runTest")
        self.f.setUp()

    def test_invalid_player_counts_names_and_ids(self):
        for names in (
            None,
            "AB",
            [],
            ["A"],
            list("ABCDEFG"),
            ["A", "A"],
            ["A", " A "],
            ["A", " "],
            ["A", 1],
        ):
            with self.subTest(names=names), self.assertRaises(RuleError):
                new_game(names)
        for ids in (
            ["same", "same"],
            ["one"],
            ["bank", "other"],
            ["depot", "other"],
            ["IR", "other"],
            [1, "other"],
            [[], "other"],
            ["", "other"],
        ):
            with self.subTest(ids=ids), self.assertRaises(RuleError):
                new_game(["A", "B"], player_ids=ids)

    def test_custom_ids_trimmed_names_and_nested_state_independence(self):
        s = new_game([" Alice ", "Bob"], ["alice", "bob"])
        self.assertEqual(s["players"]["alice"]["name"], "Alice")
        original = deepcopy(s)
        action = dict(type="buy_private", player="alice", company="TR")
        result = apply_action(s, action)
        self.assertEqual(s, original)
        self.assertEqual(result["revision"], 1)
        action["company"] = "ER"
        result["board"]["E2"]["tokens"][0].append("IR")
        self.assertEqual(s, original)
        self.assertEqual(result["history"][0]["company"], "TR")

    def test_action_type_identity_versions_and_malformed_fields_are_atomic(self):
        for action in (
            None,
            [],
            {},
            dict(type=1, player="p1"),
            dict(type="pass", player="unknown"),
            dict(type="pass", player="p2"),
            dict(type="unknown", player="p1"),
            dict(type="pass", player="p1", expected_action_id=9),
        ):
            old = deepcopy(self.f.s)
            with self.assertRaises(RuleError):
                apply_action(self.f.s, action)
            self.assertEqual(self.f.s, old)
        for field in (
            "player",
            "company",
            "corporation",
            "train",
            "source",
            "buyer",
            "seller",
            "kind",
            "item",
            "special",
            "trade_in",
            "tile",
            "hex",
        ):
            action = dict(type="pass", player="p1")
            action[field] = []
            with self.subTest(field=field), self.assertRaises(RuleError):
                apply_action(self.f.s, action)
        with self.assertRaises(RuleError):
            apply_action(self.f.s, dict(type="pass", player="p1"), expected_revision=1)

    def test_schema_and_variant_rejections_preserve_saved_state(self):
        for field, value in (("schema_version", 999), ("variant", "1830")):
            s = deepcopy(self.f.s)
            s[field] = value
            original = deepcopy(s)
            with self.assertRaises(RuleError):
                migrate_state(s)
            self.assertEqual(s, original)

    def test_auction_first_private_price_order_and_bid_cash_commitments(self):
        f = self.f
        f.reject("buy_private", company="MF")
        f.reject("buy_private", company="TR", price=0)
        f.reject("bid", company="ER", price=44)
        f.act("bid", company="ER", price=400)
        f.act("pass")
        f.act("pass")
        f.reject("bid", company="SIR", price=85)
        f.act("bid", company="ER", price=405)
        self.assertEqual(f.s["players"]["p1"]["cash"], 15)
        f.reject("bid", player="p1", company="ER", price=410)

    def test_other_unsold_privates_pay_income_without_discount(self):
        f = self.f
        f.act("buy_private", company="TR")
        before = f.s["players"]["p1"]["cash"]
        for _ in range(3):
            f.act("pass")
        self.assertEqual(f.s["players"]["p1"]["cash"], before + 5)
        self.assertEqual(f.s["auction"]["discount"], 0)
        f.act("buy_private", company="MF")

    def test_single_bid_is_resolved_at_bid_price_and_seating_resumes(self):
        f = self.f
        f.act("bid", company="MF", price=35)
        f.act("buy_private", company="TR")
        self.assertEqual(f.s["privates"]["MF"]["owner"], "p1")
        self.assertEqual(f.s["players"]["p1"]["cash"], 385)
        self.assertEqual(f.s["current_player"], "p3")

    def test_stock_president_first_one_buy_and_no_brown_multi_buy(self):
        f = self.f
        f.stock()
        f.reject("buy_shares", corporation="IR", percent=10, price=100)
        f.reject("buy_shares", corporation="IR", source="pool", price=100)
        f.act("buy_shares", corporation="IR", price=100)
        f.reject("buy_shares", corporation="AR", price=65)
        f.reject("buy_shares", corporation="IR", percent=20)

    def test_stock_insufficient_cash_and_empty_or_unknown_sources(self):
        f = self.f
        f.stock()
        f.cash(f.s["players"]["p1"], 129)
        f.reject("buy_shares", corporation="IR", price=65)
        f.shares("IR", "p2", 20)
        for source in ("pool", "wrong"):
            f.reject("buy_shares", corporation="IR", source=source)

    def test_stock_pool_uses_market_price_ipo_uses_fixed_par(self):
        f = self.f
        f.stock()
        c = f.shares("IR", "p2", 20)
        c["ipo"] -= 10
        c["pool"] = 10
        E._position(f.s, c, [1, 3])  # market 90, par 100
        cash = f.s["players"]["p1"]["cash"]
        f.act("buy_shares", corporation="IR", source="pool")
        self.assertEqual(f.s["players"]["p1"]["cash"], cash - 90)
        f.act("end_turn")
        cash = f.s["players"]["p2"]["cash"]
        f.act("buy_shares", corporation="IR", source="ipo")
        self.assertEqual(f.s["players"]["p2"]["cash"], cash - 100)
        self.assertEqual(f.s["corporations"]["IR"]["par"], 100)

    def test_stock_sale_pool_cap_ownership_units_and_president_protection(self):
        f = self.f
        f.stock()
        f.s["stock_round"] = 2
        c = f.shares("IR", "p1", 50)
        for amount in (0, 5, -10, True, 10.0, "10", 60):
            f.reject("sell_shares", corporation="IR", percent=amount)
        f.reject("sell_shares", corporation="IR", percent=40)
        c["ipo"] -= 50
        c["pool"] = 50
        f.reject("sell_shares", corporation="IR", percent=10)

    def test_stock_sale_pays_pre_sale_price_and_moves_once_per_share(self):
        f = self.f
        f.stock()
        f.s["stock_round"] = 2
        f.shares("IR", "p1", 50)
        before = f.s["players"]["p1"]["cash"]
        f.act("sell_shares", corporation="IR", percent=20)
        self.assertEqual(f.s["players"]["p1"]["cash"], before + 200)
        self.assertEqual(f.s["corporations"]["IR"]["position"], [2, 3])

    def test_presidency_equal_holdings_keep_incumbent_and_successor_tie_wraps(self):
        f = self.f
        f.stock()
        f.s["stock_round"] = 2
        c = f.shares("IR", "p3", 30)
        f.shares("IR", "p1", 30)
        f.shares("IR", "p2", 30)
        self.assertEqual(c["president"], "p3")
        f.s["current_player"] = "p3"
        f.act("sell_shares", corporation="IR", percent=10)
        self.assertEqual(f.s["corporations"]["IR"]["president"], "p1")

    def test_certificate_count_president_once_closed_and_corporate_privates_excluded(
        self,
    ):
        f = self.f
        f.stock()
        before = E.certificate_count(f.s, "p1")
        f.shares("IR", "p1", 30)
        self.assertEqual(E.certificate_count(f.s, "p1"), before + 2)
        f.s["privates"]["TR"]["closed"] = True
        f.s["privates"]["SMR"]["owner"] = "IR"
        self.assertEqual(E.certificate_count(f.s, "p1"), before)

    def test_excess_holdings_must_be_corrected_before_end_turn(self):
        f = self.f
        f.stock()
        f.s["stock_round"] = 2
        f.shares("IR", "p1", 70)
        f.reject("end_turn")
        f.act("sell_shares", corporation="IR", percent=10)
        f.act("end_turn")
        self.assertEqual(f.s["current_player"], "p2")

    def test_total_certificate_limit_rejects_buy_and_requires_correction(self):
        f = self.f
        f.stock()
        f.s["stock_round"] = 2
        for cid in ("AR", "SR", "KO"):
            f.shares(cid, "p1", 50)
        f.shares("TR", "p1", 60)
        self.assertEqual(E.certificate_count(f.s, "p1"), 19)
        f.cash(f.s["players"]["p1"], 2000)
        f.reject("buy_shares", corporation="IR", price=65)
        # A zone change can put a player above the certificate limit.
        f.shares("KU", "p1", 20)
        f.reject("end_turn")
        f.act("sell_shares", corporation="AR", percent=10)
        f.act("end_turn")

    def test_dougo_exchange_at_certificate_limit_replaces_private_certificate(self):
        f = self.f
        f.stock()
        for cid in ("AR", "SR", "KO"):
            f.shares(cid, "p2", 50)
        f.shares("TR", "p2", 60)
        f.shares("IR", "p1", 20)
        self.assertEqual(E.certificate_count(f.s, "p2"), 19)
        f.act("end_turn")
        f.act("exchange_private", player="p2")
        self.assertEqual(E.certificate_count(f.s, "p2"), 19)

    def test_dougo_cannot_exchange_when_only_pool_shares_remain(self):
        f = self.f
        f.stock()
        f.shares("IR", "p1", 50)
        f.shares("IR", "p3", 50)
        f.act("end_turn")
        f.reject("exchange_private", player="p2")

    def test_consecutive_passes_priority_and_no_floated_corporations(self):
        f = self.f
        f.stock()
        f.act("pass")
        f.act("buy_shares", corporation="IR", price=65)
        f.act("end_turn")
        for _ in range(3):
            f.act("pass")
        self.assertEqual(f.s["priority"], "p3")
        self.assertEqual(f.s["round"], "stock")
        self.assertEqual(f.s["stock_round"], 2)

    def test_sold_out_rise_does_not_change_par_or_stack_order(self):
        f = self.f
        f.stock()
        for cid in ("IR", "AR"):
            f.shares(cid, "p1", 50)
            f.shares(cid, "p2", 50)
        for _ in range(3):
            f.act("pass")
        for cid in ("IR", "AR"):
            self.assertEqual(f.s["corporations"][cid]["position"], [0, 3])
            self.assertEqual(f.s["corporations"][cid]["par"], 100)
        self.assertEqual(f.s["or_order"][:2], ["IR", "AR"])

    def test_market_boundaries_and_ragged_rows(self):
        f = self.f
        c = f.shares("IR", "p1", 20)
        for start, direction, expected in (
            ([0, 14], "right", [0, 14]),
            ([0, 0], "up", [0, 0]),
            ([10, 0], "down", [10, 0]),
            ([5, 0], "left", [6, 0]),
            ([1, 14], "right", [0, 14]),
            ([1, 14], "down", [1, 14]),
        ):
            E._position(f.s, c, start)
            E._market_move(f.s, c, direction)
            self.assertEqual(c["position"], expected)

    def test_operating_order_price_column_row_then_stack(self):
        f = self.f
        f.stock()
        for cid in ("IR", "AR", "SR"):
            f.shares(cid, "p1", 50)
        E._position(f.s, f.s["corporations"]["IR"], [1, 3])  # 90
        E._position(f.s, f.s["corporations"]["AR"], [0, 2])  # 90, left
        E._position(f.s, f.s["corporations"]["SR"], [1, 3])
        self.assertEqual(E._operating_order(f.s), ["IR", "SR", "AR"])

    def test_wrong_operating_actor_and_out_of_order_or_duplicate_steps(self):
        f = self.f
        f.operating()
        f.reject("skip", player="p2")
        f.reject("end_turn")
        f.reject("buy_train", train="2-0")
        f.route()
        f.reject("lay_tile", hex="E2", tile="5", rotation=4)
        f.train_step()
        f.reject("dividend", kind="withhold")
        f.reject("run_routes", routes=[])
        f.reject("skip")

    def test_runnable_train_cannot_be_skipped_and_revenue_is_computed(self):
        f = self.f
        f.operating()
        f.route()
        f.give_train("IR", "2-0")
        f.reject("dividend", kind="payout")
        f.reject("run_routes", routes=[])
        routes = B.route_candidates(f.s, "IR", "2-0", limit=1)
        revenue = B.validate_routes(f.s, "IR", routes)
        f.act("run_routes", routes=routes, revenue=999999)
        self.assertEqual(f.s["operating_turn"]["revenue"], revenue)
        f.act(
            "run_routes", routes=routes
        )  # §8.3: claims may be corrected before dividends.

    def test_dividends_pool_versus_ipo_withhold_and_zero_revenue(self):
        for payout, revenue in ((True, 100), (False, 100), (True, 0)):
            self.setUp()
            f = self.f
            f.operating()
            c = f.s["corporations"]["IR"]
            c["ipo"] -= 20
            c["pool"] = 20
            f.s["operating_turn"].update(routes=[], revenue=revenue)
            before = {p: a["cash"] for p, a in f.s["players"].items()}
            treasury = c["cash"]
            f.act("dividend", payout=payout)
            c = f.s["corporations"]["IR"]
            self.assertEqual(
                c["cash"], treasury + (20 if payout and revenue else revenue)
            )
            self.assertEqual(
                f.s["players"]["p1"]["cash"],
                before["p1"] + (50 if payout and revenue else 0),
            )
            self.assertEqual(c["position"], [0, 4] if payout and revenue else [0, 2])

    def test_private_income_is_separate_and_closed_privates_stop_paying(self):
        f = self.f
        f.stock()
        f.s["privates"]["SMR"]["owner"] = "IR"
        f.s["privates"]["TR"]["closed"] = True
        c = f.s["corporations"]["IR"]
        before = f.s["players"]["p1"]["cash"]
        E._private_revenue(f.s)
        self.assertEqual(c["cash"], 15)
        self.assertEqual(f.s["players"]["p1"]["cash"], before)

    def test_track_bad_hex_rotation_unknown_tile_phase_type_and_disconnect(self):
        f = self.f
        f.operating()
        for args in (
            dict(hex="missing", tile="5"),
            dict(hex="E2", tile="missing"),
            dict(hex="E2", tile="5", rotation=True),
            dict(hex="E2", tile="5", rotation=6),
            dict(hex="E2", tile="12"),
            dict(hex="E2", tile="8"),
            dict(hex="G4", tile="5", rotation=0),
        ):
            f.reject("lay_tile", **args)

    def test_track_upgrade_preserves_station_and_recycles_original_tile(self):
        f = self.f
        f.operating()
        count = f.s["tiles"]["5"]
        f.route()
        f.s["phase"] = "3"
        f.s["operating_turn"].update(step="track", laid=False)
        f.act("lay_tile", hex="E2", tile="12", rotation=4)
        self.assertEqual(f.s["tiles"]["5"], count)
        self.assertEqual(f.s["board"]["E2"]["tokens"], [["IR"]])
        self.assertEqual(f.s["corporations"]["IR"]["home_city"], 0)

    def test_track_supply_exhaustion_and_removed_track_rejected(self):
        f = self.f
        f.operating()
        # Component guard is tested directly; an exhausted tile is unavailable.
        trial = deepcopy(f.s)
        trial["tiles"]["5"] = 0
        with self.assertRaisesRegex(RuleError, "supply"):
            B.lay_tile(trial, "IR", "E2", "5", 4)
        f.route()
        f.s["phase"] = "3"
        f.s["operating_turn"].update(step="track", laid=False)
        f.reject("lay_tile", hex="E2", tile="12", rotation=0)

    def test_permanent_hexes_label_and_exact_color_progression(self):
        f = self.f
        f.operating()
        for coord in ("F1", "J1"):
            with self.assertRaisesRegex(RuleError, "Permanent"):
                B.lay_tile(deepcopy(f.s), "IR", coord, "5", 4, special="test")
        f.s["phase"] = "5"
        with self.assertRaisesRegex(RuleError, "one color"):
            B.lay_tile(deepcopy(f.s), "IR", "E2", "12", 4, special="test")
        with self.assertRaisesRegex(RuleError, "label"):
            B.lay_tile(deepcopy(f.s), "IR", "I4", "5", 4, special="test")

    def test_player_owned_private_blocks_until_closed_or_corporate_owned(self):
        f = self.f
        f.operating()
        for private_id, coord, tile, rotation in (
            ("ER", "C4", "12", 1),
            ("TR", "K4", "12", 0),
        ):
            f.s["phase"] = "3"
            with self.assertRaisesRegex(RuleError, "private blocks"):
                B.lay_tile(deepcopy(f.s), "IR", coord, tile, rotation, special="test")
        f.s["privates"]["ER"]["owner"] = "IR"
        B.lay_tile(f.s, "IR", "C4", "14", 1, special="test")
        self.assertEqual(f.s["board"]["C4"]["tile"], "14")

    def test_every_initial_tile_exit_checks_board_edges_and_impassable_borders(self):
        f = self.f
        f.stock()
        for private in f.s["privates"].values():
            private["closed"] = True
        f.cash(f.s["corporations"]["IR"], 3000)
        tested = 0
        for coord, old in f.s["board"].items():
            if old["color"] != "white":
                continue
            for tid, spec in BOARD_DATA["tiles"].items():
                if spec["color"] != "yellow" or tid == "437":
                    continue
                for rotation in range(6):
                    new = B.tile_for(tid, rotation)
                    if [n["kind"] for n in old["nodes"]] != [
                        n["kind"] for n in new["nodes"]
                    ] or new["label"] != old["label"]:
                        continue
                    for v in {v for p in new["paths"] for v in p if v.startswith("e")}:
                        edge = int(v[1:])
                        other = f.s["board"].get(B.neighbor(coord, edge))
                        bad = (
                            other is None
                            or edge in old["borders"]
                            or (edge + 3) % 6 in other["borders"]
                            or (
                                other["color"] == "gray"
                                and not any(
                                    "e" + str((edge + 3) % 6) in p
                                    for p in other["paths"]
                                )
                            )
                        )
                        if bad:
                            with self.assertRaises(RuleError):
                                B.lay_tile(
                                    deepcopy(f.s),
                                    "IR",
                                    coord,
                                    tid,
                                    rotation,
                                    special="test",
                                )
                            tested += 1
                            break
        self.assertGreater(tested, 50)

    def test_home_reservation_and_one_additional_station_per_turn(self):
        f = self.f
        f.operating()
        with self.assertRaisesRegex(RuleError, "reserved"):
            B.place_token(deepcopy(f.s), "IR", "I2", teleport=True)
        # A full real-board route to the second city F3.
        f.route()
        f.s["board"]["F3"] = B.tile_for("5", 2)
        f.s["tiles"]["5"] -= 1
        f.act("place_token", hex="F3")
        self.assertEqual(f.s["board"]["F3"]["tokens"], [["IR"]])
        f.reject("place_token", hex="F3")

    def test_depot_order_prices_train_limit_and_new_train_waits_until_next_turn(self):
        f = self.f
        f.operating()
        f.route()
        f.train_step()
        f.reject("buy_train", train="3-0")
        f.reject("buy_train", train="2-0", price=79)
        f.act("buy_train", train="2-0")
        f.reject("run_routes", routes=B.route_candidates(f.s, "IR", "2-0", limit=1))
        for tid in ("2-1", "2-2", "2-3"):
            f.act("buy_train", train=tid)
        f.reject("buy_train", train="2-4")

    def test_mandatory_purchase_cheapest_alternative_and_no_optional_subsidy(self):
        f = self.f
        f.operating()
        f.route()
        f.train_step()
        f.reject("end_turn")
        f.cash(f.s["corporations"]["IR"], 0)
        f.act("buy_train", train="2-0")
        self.assertEqual(f.s["corporations"]["IR"]["cash"], 0)
        f.reject("buy_train", train="2-1")

    def test_train_transfer_requires_exact_other_party_offer_and_pays_seller(self):
        f = self.f
        f.operating()
        f.shares("AR", "p2", 50)
        f.give_train("AR", "2-0")
        f.train_step()
        f.reject("buy_train", train="2-0", price=50, consent=True)
        f.act(
            "offer",
            player="p2",
            kind="train",
            item="2-0",
            seller="AR",
            buyer="IR",
            price=50,
        )
        f.reject("buy_train", train="2-0", price=51)
        before = f.s["corporations"]["IR"]["cash"]
        f.act("buy_train", train="2-0", price=50)
        self.assertEqual(f.s["corporations"]["AR"]["cash"], 50)
        self.assertEqual(f.s["corporations"]["IR"]["cash"], before - 50)
        self.assertEqual(f.s["offers"], [])
        f.reject("buy_train", train="2-0", price=50)

    def test_offer_requires_owner_party_distinct_entities_and_valid_price(self):
        f = self.f
        f.operating()
        f.shares("AR", "p2", 50)
        f.give_train("AR", "2-0")
        offer = dict(kind="train", item="2-0", seller="AR", buyer="IR", price=50)
        for change in (
            dict(player="p3"),
            dict(seller="SR"),
            dict(buyer="AR"),
            dict(price=0),
            dict(price=True),
            dict(kind="unknown"),
        ):
            f.reject("offer", **dict(offer, **change))
        f.act("offer", player="p2", **offer)
        f.act("offer", player="p2", **offer)
        self.assertEqual(len(f.s["offers"]), 1)

    def test_other_president_discards_interrupt_and_cannot_discard_unowned_train(self):
        f = self.f
        f.operating()
        f.shares("AR", "p2", 50)
        for tid in ("3-0", "3-1", "3-2", "3-3"):
            f.give_train("AR", tid)
        E._phase_change(f.s, "4")
        self.assertEqual(legal_actions(f.s, "p2")["player"], "p2")
        f.reject("discard_train", corporation="AR", train="3-0", player="p1")
        f.reject("discard_train", corporation="AR", train="2-0", player="p2")
        f.reject("exchange_private", player="p2")
        f.reject("lay_tile", special="MF", hex="G10", tile="437", player="p2")
        f.act("discard_train", corporation="AR", train="3-0", player="p2")
        self.assertEqual(f.s["current_player"], "p1")
        self.assertEqual(f.s["pending_discards"], [])
        self.assertIn("3-0", E.available_depot(f.s))

    def test_diesel_not_available_before_six_and_trade_in_needs_eligible_owned_train(
        self,
    ):
        f = self.f
        f.operating()
        f.train_step()
        self.assertNotIn("D-0", E.available_depot(f.s))
        f.reject("buy_train", train="D-0")
        E._phase_change(f.s, "6")
        f.cash(f.s["corporations"]["IR"], 2000)
        f.reject("buy_train", train="D-0", trade_in="5-0")
        f.give_train("IR", "2-0")
        f.reject("buy_train", train="D-0", trade_in="2-0")

    def test_phase_changes_do_not_rewind_or_change_current_or_set_length(self):
        f = self.f
        f.operating()
        self.assertEqual(f.s["or_total"], 1)
        E._phase_change(f.s, "3")
        self.assertEqual(f.s["or_total"], 1)
        E._phase_change(f.s, "2")
        self.assertEqual(f.s["phase"], "3")
        f.train_step()
        f.act("end_turn")
        for _ in range(3):
            f.act("pass")
        self.assertEqual(f.s["or_total"], 2)

    def test_private_sale_cannot_resell_closed_company_or_buy_for_other_operator(self):
        f = self.f
        f.operating()
        f.s["phase"] = "3"
        f.act("buy_private", company="SMR", buyer="IR", price=50)
        f.reject("buy_private", company="SMR", buyer="IR", price=50)
        f.s["privates"]["TR"]["closed"] = True
        f.reject("buy_private", company="TR", buyer="IR", price=20)
        f.reject("buy_private", company="TR", buyer="AR", price=20)

    def test_dougo_does_not_consume_normal_buy_and_respects_window_and_ipo_supply(self):
        f = self.f
        f.stock()
        f.shares("IR", "p1", 20)
        f.act("end_turn")
        f.act("exchange_private", player="p2")
        f.act("buy_shares", corporation="AR", price=65, player="p2")
        self.assertEqual(f.s["corporations"]["IR"]["holdings"]["p2"], 10)
        self.setUp()
        f = self.f
        f.operating()
        f.route()
        turn = deepcopy(f.s["operating_turn"])
        f.act("exchange_private", player="p2")
        self.assertEqual(f.s["operating_turn"], turn)

    def test_dougo_exchange_updates_current_president_without_changing_other_operator(
        self,
    ):
        for operating_ir in (True, False):
            self.setUp()
            f = self.f
            f.operating()
            c = f.s["corporations"]["IR"]
            c["holdings"].update(p1=20, p2=20, p3=10)
            c["president"] = "p1"
            if not operating_ir:
                f.shares("AR", "p3", 50)
                f.s.update(current_corporation="AR", current_player="p3")
            f.act("exchange_private", player="p2")
            self.assertEqual(f.s["corporations"]["IR"]["president"], "p2")
            self.assertEqual(f.s["current_player"], "p2" if operating_ir else "p3")

    def test_mitsubishi_wrong_owner_tile_auction_interrupt_and_pending_special(self):
        f = self.f
        f.reject("lay_tile", player="p2", special="MF", hex="G10", tile="437")
        f.operating()
        f.reject("lay_tile", hex="G10", tile="437")
        f.reject("lay_tile", player="p1", special="MF", hex="G10", tile="437")
        f.reject("lay_tile", player="p2", special="MF", hex="G10", tile="58")
        f.s["phase"] = "3"
        f.act(
            "offer",
            player="p3",
            kind="private",
            item="ER",
            seller="p3",
            buyer="IR",
            price=40,
        )
        f.act("buy_private", company="ER", buyer="IR", price=40)
        f.reject("lay_tile", player="p2", special="MF", hex="G10", tile="437")
        f.reject("exchange_private", player="p2")
        f.s = migrate_state(json.loads(json.dumps(f.s)))
        self.assertEqual(legal_actions(f.s, "p3")["types"], ["lay_tile", "pass"])
        f.act("pass", player="p3")
        self.assertEqual(f.s["current_player"], "p1")

    def test_surviving_utf_has_value_revenue_certificate_and_cannot_be_sold(self):
        f = self.f
        f.stock(4)
        owner = f.s["privates"]["UTF"]["owner"]
        f.shares("IR", "p1", 50)
        E._start_operating(f.s)
        E._phase_change(f.s, "5")
        self.assertEqual(E.certificate_count(f.s, owner), 1)
        before = scores(f.s)[owner]
        E._private_revenue(f.s)
        self.assertEqual(scores(f.s)[owner], before + 50)
        self.assertEqual(scores(f.s)[owner], f.s["players"][owner]["cash"] + 150)
        f.act(
            "offer",
            player=owner,
            kind="private",
            item="UTF",
            seller=owner,
            buyer="IR",
            price=150,
        )
        f.reject("buy_private", company="UTF", buyer="IR", price=150)

    def test_bank_break_zero_negative_payouts_and_required_or_set_completion(self):
        f = self.f
        f.operating()
        f.s["or_total"] = 2
        E._pay(f.s, "bank", "p1", f.s["bank"])
        self.assertTrue(f.s["bank_broken"])
        E._pay(f.s, "bank", "p2", 10)
        self.assertEqual(f.s["bank"], -10)
        f.train_step()
        f.act("end_turn")
        self.assertFalse(f.s["finished"])
        self.assertEqual(f.s["or_number"], 2)
        f.train_step()
        f.act("end_turn")
        self.assertEqual(f.s["end_reason"], "bank")
        self.assertEqual(legal_actions(f.s)["types"], [])
        f.reject("pass")
        self.assertEqual(f.s["result"], scores(f.s))

    def test_final_score_excludes_corporate_cash_and_closed_privates(self):
        f = self.f
        f.stock()
        f.shares("IR", "p1", 50)
        before = scores(f.s)["p1"]
        f.cash(f.s["corporations"]["IR"], 500)
        self.assertEqual(scores(f.s)["p1"], before)
        f.s["privates"]["TR"]["closed"] = True
        self.assertEqual(scores(f.s)["p1"], before - 20)

    def test_emergency_sale_reorders_only_remaining_corporations(self):
        f = self.f
        f.operating()
        f.shares("AR", "p2", 50)
        f.shares("AR", "p1", 10)
        f.shares("SR", "p2", 50)
        E._start_operating(f.s)
        self.assertEqual(f.s["or_order"], ["IR", "AR", "SR"])
        f.route()
        f.train_step()
        f.cash(f.s["corporations"]["IR"], 0)
        f.cash(f.s["players"]["p1"], 0)
        f.act("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(f.s["or_order"], ["IR", "SR", "AR"])
        self.assertEqual(f.s["current_corporation"], "IR")

    def test_insufficient_treasury_rejects_terrain_payment(self):
        f = self.f
        f.operating()
        f.cash(f.s["corporations"]["IR"], 79)
        # D5 is a printed mountain hex; tile 8 rotation 0 fits the board.
        for rotation in range(6):
            funded = deepcopy(f.s)
            funded["corporations"]["IR"]["cash"] = 80
            try:
                B.lay_tile(funded, "IR", "D5", "8", rotation, special="test")
            except RuleError:
                continue
            with self.assertRaisesRegex(RuleError, "funds"):
                B.lay_tile(deepcopy(f.s), "IR", "D5", "8", rotation, special="test")
            break
        else:
            self.fail("No fitting terrain-test tile")

    def test_bankruptcy_requires_a_route_and_insufficient_total_legal_funding(self):
        f = self.f
        f.operating()
        f.train_step()
        f.reject("bankrupt")
        self.setUp()
        f = self.f
        f.operating()
        f.route()
        f.train_step()
        f.cash(f.s["corporations"]["IR"], 0)
        f.cash(f.s["players"]["p1"], 0)
        f.reject("bankrupt")  # Saleable stock still funds the train.
        f.act("emergency_sell", corporation="IR", percent=10)
        f.reject("bankrupt")  # Cash now funds the train.

    def test_action_discovery_out_of_turn_offers_and_exchange_not_unrelated_players(
        self,
    ):
        f = self.f
        f.operating()
        self.assertIn("exchange_private", legal_actions(f.s, "p2")["types"])
        self.assertIn("lay_tile", legal_actions(f.s, "p2")["types"])
        f.route()
        self.assertIn("exchange_private", legal_actions(f.s, "p2")["types"])
        f.shares("AR", "p2", 50)
        f.give_train("AR", "2-0")
        offers = legal_actions(f.s, "p2")["choices"]["offers"]
        self.assertTrue(any(x.get("item") == "2-0" for x in offers))
        unrelated = legal_actions(f.s, "p3")["choices"].get("offers", [])
        self.assertFalse(any(x.get("item") == "2-0" for x in unrelated))
