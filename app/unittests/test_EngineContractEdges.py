"""Shared input and stock boundaries must hold in each independent engine."""

import unittest
from copy import deepcopy

from app import engine1830, engine1889
from app.engine1830 import engine as e1830
from app.engine1889 import engine as e1889
from app.unittests import test_Engine1830 as f1830
from app.unittests import test_Engine1889 as f1889


class SharedContractEdgeTests(unittest.TestCase):
    def variants(self):
        for module, engine, fixtures, cid in (
            (engine1830, e1830, f1830, "NYC"),
            (engine1889, e1889, f1889, "IR"),
        ):
            self.module, self.e, self.cid = module, engine, cid
            self.f = (
                fixtures.Rules1830Tests
                if module is engine1830
                else fixtures.Rules1889Tests
            )("runTest")
            self.f.setUp()
            yield

    def test_invalid_names_and_reserved_duplicate_or_malformed_ids(self):
        for _ in self.variants():
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
                with self.assertRaises(self.module.RuleError):
                    self.module.new_game(names)
            for ids in (
                ["same", "same"],
                ["one"],
                ["bank", "other"],
                ["depot", "other"],
                [self.cid, "other"],
                [1, "other"],
                [[], "other"],
                ["", "other"],
            ):
                with self.assertRaises(self.module.RuleError):
                    self.module.new_game(["A", "B"], player_ids=ids)

    def test_custom_ids_trimmed_names_and_independent_result_history(self):
        for _ in self.variants():
            state = self.module.new_game([" Alice ", "Bob"], ["alice", "bob"])
            self.assertEqual(state["players"]["alice"]["name"], "Alice")
            old = deepcopy(state)
            private = next(iter(state["privates"]))
            action = dict(type="buy_private", player="alice", company=private)
            result = self.module.apply_action(state, action)
            action["company"] = "changed"
            result["history"][0]["player"] = "changed"
            self.assertEqual(state, old)
            self.assertEqual(result["players"]["alice"]["name"], "Alice")

    def test_source_prices_empty_sources_and_insufficient_cash(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            c = f.shares(self.cid, "p2", 20)
            c["ipo"] -= 10
            c["pool"] = 10
            self.e._position(
                f.s,
                c,
                next(
                    [r, col]
                    for r, row in enumerate(self.e.MARKET)
                    for col, cell in enumerate(row)
                    if cell and cell["price"] == 90 and cell["zone"] == "white"
                ),
            )
            f.reject("buy_shares", corporation=self.cid, source="unknown")
            f.cash(f.s["players"]["p1"], 89)
            f.reject("buy_shares", corporation=self.cid, source="pool")
            f.cash(f.s["players"]["p1"], 300)
            f.act("buy_shares", corporation=self.cid, source="pool")
            self.assertEqual(f.s["players"]["p1"]["cash"], 210)
            f.act("end_turn")
            f.reject("buy_shares", corporation=self.cid, source="pool")
            before = f.s["players"]["p2"]["cash"]
            f.act("buy_shares", corporation=self.cid, source="ipo")
            self.assertEqual(f.s["players"]["p2"]["cash"], before - 100)

    def test_par_rejects_noninteger_and_unlisted_values_atomically(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            for price in (True, 100.0, "100", 0, -1, 66, 101):
                f.reject("buy_shares", corporation=self.cid, price=price)
            f.act("buy_shares", corporation=self.cid, price=100)
            self.assertEqual(f.s["corporations"][self.cid]["par"], 100)

    def test_private_purchase_half_and_twice_face_bounds(self):
        for _ in self.variants():
            for upper in (False, True):
                f = self.f
                f.setUp()
                f.operating()
                cid = f.s["current_corporation"]
                actor = f.s["current_player"]
                private = next(
                    p
                    for p in f.s["privates"].values()
                    if p["owner"] == actor and p["id"] != "BO"
                )
                face, pid = private["value"], private["id"]
                f.reject("buy_private", company=pid, buyer=cid, price=face)
                f.s["phase"] = "4" if upper else "3"
                for price in (face // 2 - 1, 2 * face + 1, True, "10"):
                    f.reject("buy_private", company=pid, buyer=cid, price=price)
                price = 2 * face if upper else face // 2
                before = f.s["corporations"][cid]["cash"]
                f.act("buy_private", company=pid, buyer=cid, price=price)
                self.assertEqual(f.s["privates"][pid]["owner"], cid)
                self.assertEqual(f.s["corporations"][cid]["cash"], before - price)

    def test_sale_units_ownership_pool_cap_and_sold_company_restriction(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            f.s["stock_round"] = 2
            c = f.shares(self.cid, "p1", 50)
            for amount in (0, 5, -10, True, 10.0, "10", 60):
                f.reject("sell_shares", corporation=self.cid, percent=amount)
            f.act("sell_shares", corporation=self.cid, percent=10)
            f.reject("buy_shares", corporation=self.cid)
            f.act("end_turn")
            f.act("buy_shares", corporation=self.cid, source="pool")
            self.assertEqual(f.s["corporations"][self.cid]["holdings"]["p2"], 10)
            # Isolate the exact pool ceiling independently of presidency checks.
            trial = deepcopy(f.s)
            corp = trial["corporations"][self.cid]
            corp["pool"] += corp["ipo"]
            corp["ipo"] = 0
            self.assertEqual(corp["pool"], 50)
            with self.assertRaisesRegex(self.module.RuleError, "50%"):
                self.e._sell_shares(trial, "p1", self.cid, 10)

    def test_total_certificate_limit_blocks_buy_and_requires_selling_before_pass(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            f.s["stock_round"] = 2
            others = (
                ("CPR", "NYNH", "ERIE", "C&O")
                if self.module is engine1830
                else ("AR", "SR", "KO", "TR")
            )
            for cid in others[:3]:
                f.shares(cid, "p1", 50)
            f.shares(others[3], "p1", 60)
            if self.module is engine1830:
                f.shares("PRR", "p1", 20)
            limit = self.e.CERT_LIMITS[3]
            self.assertEqual(self.e.certificate_count(f.s, "p1"), limit)
            f.cash(f.s["players"]["p1"], 2000)
            f.reject("buy_shares", corporation=self.cid, price=100)
            f.shares(self.cid, "p1", 20)
            f.reject("end_turn")
            f.act("sell_shares", corporation=others[0], percent=10)
            f.act("end_turn")

    def test_excess_corporation_holding_must_be_sold_before_passing(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            f.s["stock_round"] = 2
            f.shares(self.cid, "p1", 70)
            f.reject("end_turn")
            f.act("sell_shares", corporation=self.cid, percent=10)
            f.act("end_turn")

    def test_closed_or_corporate_privates_do_not_count_as_personal_certificates(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            before = self.e.certificate_count(f.s, "p1")
            owned = [p for p in f.s["privates"].values() if p["owner"] == "p1"]
            self.assertEqual(len(owned), 2)
            owned[0]["closed"] = True
            owned[1]["owner"] = self.cid
            self.assertEqual(self.e.certificate_count(f.s, "p1"), before - 2)

    def test_buy_then_sell_same_corporation_is_permitted(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            f.s["stock_round"] = 2
            f.shares(self.cid, "p1", 20)
            f.act("buy_shares", corporation=self.cid)
            f.act("sell_shares", corporation=self.cid, percent=10)
            self.assertEqual(f.s["corporations"][self.cid]["holdings"]["p1"], 20)

    def test_emergency_sales_require_a_route_and_a_cash_shortfall(self):
        for _ in self.variants():
            f = self.f
            f.operating()
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject(
                "emergency_sell", corporation=f.s["current_corporation"], percent=10
            )
            f.setUp()
            f.operating()
            (f.washington if self.module is engine1830 else f.route)()
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject(
                "emergency_sell", corporation=f.s["current_corporation"], percent=10
            )

    def test_1830_brown_multiple_buys_cannot_change_corporation(self):
        f = f1830.Rules1830Tests("runTest")
        f.setUp()
        f.stock()
        for cid in ("NYC", "CPR"):
            c = f.shares(cid, "p1", 20)
            e1830._position(f.s, c, [5, 0])
        f.act("buy_shares", corporation="NYC")
        f.act("buy_shares", corporation="NYC")
        f.reject("buy_shares", corporation="CPR")

    def test_permanent_hexes_wrong_label_and_skipped_color_are_rejected(self):
        for _ in self.variants():
            f, b = self.f, self.e.topology
            f.stock()
            tile = "57" if self.module is engine1830 else "5"
            for color in ("red", "gray"):
                coord = next(h for h, t in f.s["board"].items() if t["color"] == color)
                with self.assertRaisesRegex(self.module.RuleError, "Permanent"):
                    b.lay_tile(deepcopy(f.s), self.cid, coord, tile, 0, special="test")
            f.s["phase"] = "3"
            white = "J14" if self.module is engine1830 else "E2"
            with self.assertRaisesRegex(self.module.RuleError, "yellow|one color"):
                b.lay_tile(deepcopy(f.s), self.cid, white, "14", 0, special="test")
            label_hex = "E23" if self.module is engine1830 else "I4"
            label_tile = "14" if self.module is engine1830 else "5"
            with self.assertRaisesRegex(self.module.RuleError, "matching|label"):
                b.lay_tile(
                    deepcopy(f.s), self.cid, label_hex, label_tile, 0, special="test"
                )

    def test_tile_supply_exhaustion_and_insufficient_terrain_treasury(self):
        for _ in self.variants():
            f, b = self.f, self.e.topology
            f.operating()
            cid = f.s["current_corporation"]
            coord, tile, cost = (
                ("J14", "57", 80) if self.module is engine1830 else ("D5", "8", 80)
            )
            rotation = 0
            if self.module is engine1889:
                for candidate in range(6):
                    try:
                        b.lay_tile(
                            deepcopy(f.s), cid, coord, tile, candidate, special="test"
                        )
                    except self.module.RuleError:
                        continue
                    rotation = candidate
                    break
                else:
                    self.fail("No terrain-test rotation")
            trial = deepcopy(f.s)
            trial["tiles"][tile] = 0
            with self.assertRaisesRegex(self.module.RuleError, "supply"):
                b.lay_tile(trial, cid, coord, tile, rotation, special="test")
            trial = deepcopy(f.s)
            trial["corporations"][cid]["cash"] = cost - 1
            with self.assertRaisesRegex(self.module.RuleError, "treasury|funds"):
                b.lay_tile(trial, cid, coord, tile, rotation, special="test")

    def test_private_block_is_removed_by_closure_or_corporate_ownership(self):
        for _ in self.variants():
            f, b = self.f, self.e.topology
            f.operating()
            cid = f.s["current_corporation"]
            if self.module is engine1830:
                private, coord, tile, rotation = "SV", "G15", "9", 1
            else:
                private, coord, tile, rotation = "ER", "C4", "14", 1
                f.s["phase"] = "3"
            with self.assertRaisesRegex(self.module.RuleError, "private blocks"):
                b.lay_tile(deepcopy(f.s), cid, coord, tile, rotation, special="test")
            for closed in (False, True):
                trial = deepcopy(f.s)
                if closed:
                    trial["privates"][private]["closed"] = True
                else:
                    trial["privates"][private]["owner"] = cid
                b.lay_tile(trial, cid, coord, tile, rotation, special="test")
                self.assertEqual(trial["board"][coord]["tile"], tile)

    def test_phase_changes_wait_for_next_set_before_two_or_three_operating_rounds(self):
        for _ in self.variants():
            for phase, total in (("3", 2), ("5", 3)):
                f = self.f
                f.setUp()
                f.operating()
                self.assertEqual(f.s["or_total"], 1)
                self.e._phase_change(f.s, phase)
                self.assertEqual(f.s["or_total"], 1)
                (f.to_train if self.module is engine1830 else f.train_step)()
                f.act("end_turn")
                for _ in range(3):
                    f.act("pass")
                self.assertEqual(f.s["or_total"], total)

    def test_train_transfer_exact_consent_party_ownership_price_and_consumption(self):
        for _ in self.variants():
            f = self.f
            f.operating()
            buyer, actor = f.s["current_corporation"], f.s["current_player"]
            seller, owner, stranger = (
                ("NYC", "p1", "p2") if self.module is engine1830 else ("AR", "p2", "p3")
            )
            f.shares(seller, owner, 20)
            (f.train if self.module is engine1830 else f.give_train)(seller, "2-0")
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject("buy_train", train="2-0", price=50, consent=True)
            offer = dict(kind="train", item="2-0", seller=seller, buyer=buyer, price=50)
            for change in (
                dict(player=stranger),
                dict(seller=buyer),
                dict(buyer=seller),
                dict(price=0),
                dict(price=True),
                dict(kind="unknown"),
            ):
                f.reject("offer", **dict(offer, **change))
            f.act("offer", player=owner, **offer)
            f.act("offer", player=owner, **offer)
            self.assertEqual(len(f.s["offers"]), 1)
            f.reject("buy_train", train="2-0", price=51)
            before = f.s["corporations"][buyer]["cash"]
            f.act("buy_train", train="2-0", price=50)
            self.assertEqual(f.s["corporations"][seller]["cash"], 50)
            self.assertEqual(f.s["corporations"][buyer]["cash"], before - 50)
            self.assertEqual(f.s["offers"], [])
            f.reject("buy_train", train="2-0", price=50)

    def test_bankruptcy_rejects_without_route_or_while_cash_or_stock_can_fund_train(
        self,
    ):
        for _ in self.variants():
            f = self.f
            f.operating()
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject("bankrupt")
            f.setUp()
            f.operating()
            (f.washington if self.module is engine1830 else f.route)()
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject("bankrupt")
            cid, actor = f.s["current_corporation"], f.s["current_player"]
            f.cash(f.s["corporations"][cid], 0)
            f.cash(f.s["players"][actor], 0)
            f.reject("bankrupt")
            f.act("emergency_sell", corporation=cid, percent=10)
            f.reject("bankrupt")

    def test_first_stock_round_rejects_an_otherwise_saleable_bundle(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            f.shares(self.cid, "p1", 50)
            f.reject("sell_shares", corporation=self.cid, percent=10)
            f.s["stock_round"] = 2
            f.act("sell_shares", corporation=self.cid, percent=10)
            self.assertEqual(f.s["corporations"][self.cid]["pool"], 10)

    def test_flotation_exact_threshold_and_capital_only_once(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            threshold = 60 if self.module is engine1830 else 50
            c = f.shares(self.cid, "p1", threshold - 10)
            self.assertFalse(c["floated"])
            self.assertEqual(c["cash"], 0)
            f.shares(self.cid, "p2", 10)
            self.assertTrue(c["floated"])
            self.assertEqual(c["cash"], 0)
            for _ in range(2):
                self.e._start_operating(f.s)
                self.assertEqual(c["cash"], 1000)
                self.assertTrue(c["home_placed"])
                self.module.validate_state(f.s)

    def test_normal_train_limit_depot_order_and_fixed_price(self):
        for _ in self.variants():
            f = self.f
            f.operating()
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject("buy_train", train="3-0")
            f.reject("buy_train", train="2-0", price=79)
            for i in range(4):
                f.act("buy_train", train="2-" + str(i))
            f.reject("buy_train", train="2-4")

    def test_returned_train_costs_face_and_does_not_rewind_phase(self):
        for _ in self.variants():
            f = self.f
            f.operating()
            self.e._phase_change(f.s, "4")
            f.s["trains"]["3-0"]["used"] = True
            (f.to_train if self.module is engine1830 else f.train_step)()
            f.reject("buy_train", train="3-0", price=179)
            cid = f.s["current_corporation"]
            cash = f.s["corporations"][cid]["cash"]
            f.act("buy_train", train="3-0", price=180)
            self.assertEqual(f.s["phase"], "4")
            self.assertEqual(f.s["corporations"][cid]["cash"], cash - 180)

    def test_yellow_exempts_total_count_but_only_orange_relaxes_company_holding(self):
        for _ in self.variants():
            f = self.f
            f.stock()
            c = f.shares(self.cid, "p1", 60)
            for zone in ("y", "o"):
                position = next(
                    [r, col]
                    for r, row in enumerate(self.e.MARKET)
                    for col, cell in enumerate(row)
                    if cell and cell["zone"] == zone
                )
                self.e._position(f.s, c, position)
                self.assertEqual(self.e.certificate_count(f.s, "p1"), 2)
                if zone == "y":
                    f.reject("buy_shares", corporation=self.cid)
                else:
                    f.act("buy_shares", corporation=self.cid)
                    self.assertEqual(
                        f.s["corporations"][self.cid]["holdings"]["p1"], 70
                    )
