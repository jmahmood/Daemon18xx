"""Less common rulebook cases and adversarial requests, §§7–25 / Tables 1–7."""

import unittest
from copy import deepcopy

from app.engine1830 import new_game, apply_action, RuleError, validate_state
from app.engine1830 import board as B, engine as E
from app.engine1830.data import PHASES, UPGRADES, BOARD_DATA
from app.unittests import test_Engine1830 as fixtures


class SpecialRules1830Tests(unittest.TestCase):
    setUp = fixtures.Rules1830Tests.setUp
    act = fixtures.Rules1830Tests.act
    reject = fixtures.Rules1830Tests.reject
    stock = fixtures.Rules1830Tests.stock
    cash = fixtures.Rules1830Tests.cash
    shares = fixtures.Rules1830Tests.shares
    operating = fixtures.Rules1830Tests.operating
    train = fixtures.Rules1830Tests.train
    washington = fixtures.Rules1830Tests.washington
    to_train = fixtures.Rules1830Tests.to_train

    def test_bidding_keeps_stock_round_open_instead_of_discounting_sv(self):
        for price in (45, 50, 55, 60, 65, 70):
            self.act("bid", company="CS", price=price)
        self.assertEqual(self.s["auction"]["discount"], 0)
        self.act("buy_private", company="SV", price=20)

    def test_normal_action_cannot_forge_other_party_consent(self):
        self.operating()
        self.s["phase"] = "3"
        self.reject(
            "buy_private", company="SV", buyer="B&O", price=20, seller_consent="p1"
        )
        self.reject(
            "offer",
            kind="private",
            item="SV",
            seller="p1",
            buyer="C&O",
            price=20,
            player="p2",
        )
        self.act(
            "offer",
            kind="private",
            item="SV",
            seller="p1",
            buyer="B&O",
            price=20,
            player="p1",
        )
        self.act("buy_private", company="SV", buyer="B&O", price=20)
        self.assertEqual(self.s["privates"]["SV"]["owner"], "B&O")

    def test_player_private_sale_on_seller_turn_requires_buyer_offer(self):
        self.stock()
        self.s["stock_round"] = 2
        self.reject("buy_private", company="SV", buyer="p2", price=25)
        self.act(
            "offer",
            kind="private",
            item="SV",
            seller="p1",
            buyer="p2",
            price=25,
            player="p2",
        )
        self.act("buy_private", company="SV", buyer="p2", price=25)
        self.assertEqual(self.s["privates"]["SV"]["owner"], "p2")
        self.assertEqual(
            self.s["players"]["p1"]["cash"], 695
        )  # SV20 + MH110, then sale25.

    def test_private_sales_prohibited_first_round_and_corporate_resale(self):
        self.stock()
        self.act(
            "offer",
            kind="private",
            item="SV",
            seller="p1",
            buyer="p2",
            price=20,
            player="p2",
        )
        self.reject("buy_private", company="SV", buyer="p2", price=20)
        self.s["privates"]["SV"]["owner"] = "B&O"
        self.reject(
            "offer", kind="private", item="SV", seller="B&O", buyer="p1", price=20
        )

    def test_bo_cannot_be_sold_to_corporation(self):
        self.operating()
        self.s["phase"] = "3"
        self.reject("buy_private", company="BO", buyer="B&O", price=220)

    def test_cs_extra_disconnected_tile_lay_is_once_only(self):
        self.operating()
        self.s["phase"] = "3"
        self.s["privates"]["CS"]["owner"] = "B&O"
        self.act("lay_tile", hex="J14", tile="57", rotation=0)
        self.act("lay_tile", hex="B20", tile="3", rotation=0, special="CS")
        self.assertTrue(self.s["operating_turn"]["laid"])
        self.assertTrue(self.s["privates"]["CS"]["used"])
        self.assertEqual(self.s["tiles"]["3"], 1)
        self.reject("lay_tile", hex="B20", tile="4", rotation=0, special="CS")
        self.reject("lay_tile", hex="I17", tile="9", rotation=1)

    def test_dh_disconnected_mountain_tile_and_free_token(self):
        self.operating()
        self.s["phase"] = "3"
        self.s["privates"]["DH"]["owner"] = "B&O"
        self.act(
            "lay_tile", hex="F16", tile="57", rotation=0, special="DH", place_token=True
        )
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 880)
        self.assertIn("B&O", self.s["board"]["F16"]["tokens"][0])
        self.assertTrue(self.s["operating_turn"]["tokened"])
        self.reject("place_token", hex="J14")

    def test_dh_deferred_disconnected_token_is_paid(self):
        self.operating()
        self.s["phase"] = "3"
        self.s["privates"]["DH"]["owner"] = "B&O"
        self.act("lay_tile", hex="F16", tile="57", rotation=0, special="DH")
        self.s["operating_turn"].update(step="track", laid=False, dh_free=False)
        self.act("place_token", hex="F16")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 840)

    def test_mh_can_exchange_between_turns_but_not_interrupt_another_turn(self):
        self.stock()
        self.shares("NYC", "p2", 20)
        self.act("pass")
        # It is now player 2's untouched turn, a legal between-turn window.
        self.act("exchange_private", player="p1")
        self.assertEqual(self.s["current_player"], "p2")
        self.assertTrue(self.s["privates"]["MH"]["closed"])
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 10)

    def test_mh_exchange_does_not_count_as_stock_purchase(self):
        self.stock()
        self.shares("NYC", "p2", 20)
        self.act("exchange_private")
        self.act("buy_shares", corporation="NYC")
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 20)

    def test_mh_exchange_can_float_corporation(self):
        self.stock()
        self.shares("NYC", "p2", 50)
        self.assertFalse(self.s["corporations"]["NYC"]["floated"])
        self.act("exchange_private")
        self.assertTrue(self.s["corporations"]["NYC"]["floated"])

    def test_erie_can_choose_either_home_city_and_lay_disconnected(self):
        self.operating("ERIE")
        self.s["phase"] = "3"
        self.assertFalse(self.s["corporations"]["ERIE"]["home_placed"])
        self.act("lay_tile", hex="E11", tile="59", rotation=0)
        self.act("home_token", city=1)
        self.assertEqual(self.s["board"]["E11"]["tokens"][1], ["ERIE"])
        self.reject("home_token", city=0)
        self.assertEqual(self.s["corporations"]["ERIE"]["cash"], 1000)

    def test_cannot_take_another_corporations_reserved_home(self):
        self.operating()
        self.s["board"]["A19"]["tokens"][0] = []
        with self.assertRaisesRegex(RuleError, "reserved"):
            B.place_token(self.s, "B&O", "A19", teleport=True)
        with self.assertRaisesRegex(RuleError, "Erie"):
            B.place_token(self.s, "B&O", "E11", teleport=True)

    def test_blocked_city_is_terminus_and_stops_network_expansion(self):
        self.operating()
        self.washington()
        self.train("B&O", "3-0")
        self.s["board"]["J14"]["tokens"][0] = ["PRR"]
        route = {"train": "3-0", "paths": [["I15", 1], ["J14", 1]]}
        self.assertEqual(B.route_revenue(self.s, "B&O", [route])[0], 50)
        self.assertTrue(B.blocked(self.s["board"], "J14:n0", "B&O"))
        self.assertIn("J14:n0", B.reachable(self.s["board"], "B&O"))
        self.assertNotIn("J14:e0", B.reachable(self.s["board"], "B&O"))

    def test_two_trains_can_share_city_but_not_track(self):
        self.operating()
        self.washington()
        self.train("B&O", "2-0")
        self.train("B&O", "2-1")
        self.act("lay_tile", hex="I17", tile="9", rotation=1)
        routes = [
            {"train": "2-0", "paths": [["I15", 1], ["J14", 1]]},
            {"train": "2-1", "paths": [["I15", 0], ["I17", 0], ["I19", 0]]},
        ]
        self.assertEqual(B.route_revenue(self.s, "B&O", routes)[0], 90)

    def test_offboard_revenue_changes_at_first_five(self):
        self.assertEqual(self.s["board"]["F2"]["nodes"][0]["revenue"], [40, 70])
        self.assertEqual(self.s["board"]["J2"]["nodes"][0]["revenue"], [30, 60])
        self.assertEqual(self.s["board"]["B24"]["nodes"][0]["revenue"], [20, 30])
        E._phase_change(self.s, "5")
        self.assertEqual(self.s["phase"], "5")
        self.assertTrue(all(p["closed"] for p in self.s["privates"].values()))

    def test_train_limit_reduction_requires_other_president_to_discard(self):
        self.operating()
        self.shares("NYC", "p1", 20)
        for tid in ("2-0", "3-0", "3-1", "3-2"):
            self.train("NYC", tid)
        E._phase_change(self.s, "4")
        self.assertEqual(self.s["pending_discards"], [])  # 2 rusts, leaving three.
        self.train("NYC", "4-0")
        E._phase_change(self.s, "5")
        self.assertEqual(self.s["pending_discards"], ["NYC"])
        self.reject("pass")
        self.reject("discard_train", corporation="NYC", train="3-0")
        self.act("discard_train", player="p1", corporation="NYC", train="3-0")
        self.act("discard_train", player="p1", corporation="NYC", train="3-1")
        self.assertEqual(self.s["pending_discards"], [])
        self.assertIn("3-0", E.available_depot(self.s))
        self.assertTrue(self.s["trains"]["3-0"]["used"])

    def test_diesel_trade_in_and_four_rust(self):
        self.operating()
        self.to_train()
        self.s["phase"] = "6"
        self.train("B&O", "4-0")
        self.train("NYC", "4-1")
        self.act("buy_train", train="D-0", trade_in="4-0")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 200)
        self.assertEqual(self.s["phase"], "D")
        self.assertTrue(self.s["trains"]["4-0"]["rusted"])
        self.assertTrue(self.s["trains"]["4-1"]["rusted"])
        self.assertEqual(self.s["corporations"]["B&O"]["trains"], ["D-0"])

    def test_train_transfer_requires_real_consent_and_pays_seller(self):
        self.operating()
        self.to_train()
        self.shares("NYC", "p1", 20)
        self.train("NYC", "2-0")
        self.reject("buy_train", train="2-0", price=50, seller_consent="p1")
        self.act(
            "offer",
            player="p1",
            kind="train",
            item="2-0",
            seller="NYC",
            buyer="B&O",
            price=50,
        )
        self.act("buy_train", train="2-0", price=50)
        self.assertEqual(self.s["corporations"]["NYC"]["cash"], 50)
        self.assertEqual(self.s["corporations"]["NYC"]["trains"], [])
        self.assertEqual(self.s["corporations"]["B&O"]["trains"], ["2-0"])

    def test_forced_share_sales_cannot_dump_affected_presidency(self):
        self.operating()
        self.washington()
        self.to_train()
        self.shares("B&O", "p1", 20)
        self.cash(self.s["corporations"]["B&O"], 0)
        self.cash(self.s["players"]["p3"], 0)
        self.reject("emergency_sell", corporation="B&O", percent=50)
        self.act("emergency_sell", corporation="B&O", percent=10)
        self.assertEqual(self.s["corporations"]["B&O"]["president"], "p3")
        self.act("buy_train", train="2-0")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 0)
        self.assertEqual(self.s["players"]["p3"]["cash"], 10)

    def test_emergency_sale_reorders_remaining_corporations(self):
        self.operating()
        self.washington()
        self.to_train()
        c = self.shares("NYC", "p3", 60)
        d = self.shares("C&O", "p1", 60)
        self.s["or_order"] = ["B&O", "NYC", "C&O"]
        self.s["or_index"] = 0
        E._position(self.s, c, [0, 6])
        E._position(self.s, d, [0, 5])
        self.cash(self.s["corporations"]["B&O"], 0)
        self.cash(self.s["players"]["p3"], 0)
        self.act("emergency_sell", corporation="NYC", percent=40)
        self.assertEqual(self.s["or_order"], ["B&O", "C&O", "NYC"])

    def test_all_table6_upgrades_have_preserving_orientation(self):
        for old, replacements in UPGRADES.items():
            for new in replacements:
                with self.subTest(old=old, new=new):
                    self.assertTrue(
                        any(
                            B.preserved_mapping(B.tile_for(old, 0), B.tile_for(new, r))
                            is not None
                            for r in range(6)
                        )
                    )

    def test_every_initial_tile_exit_is_checked_against_map_and_lakes(self):
        self.operating()
        self.reject(
            "lay_tile", hex="J14", tile="57", rotation=1
        )  # exits run outside printed board.
        self.reject("lay_tile", hex="F6", tile="57", rotation=0)  # fixed gray.
        self.s["privates"]["CS"]["owner"] = "B&O"
        self.reject(
            "lay_tile", hex="B20", tile="3", rotation=2, special="CS"
        )  # exits into map edge.

    def test_malformed_json_actions_fail_as_rule_errors(self):
        for field in (
            "company",
            "corporation",
            "train",
            "tile",
            "player",
            "buyer",
            "seller",
        ):
            with self.subTest(field=field):
                original = deepcopy(self.s)
                with self.assertRaises(RuleError):
                    apply_action(
                        self.s,
                        (
                            dict(type="bid", player="p1", **{field: []})
                            if field != "player"
                            else {"type": "bid", "player": []}
                        ),
                    )
                self.assertEqual(self.s, original)

    def test_mh_cannot_interrupt_own_corporations_operating_turn(self):
        self.operating()
        self.shares("NYC", "p2", 20)
        self.s["privates"]["MH"]["owner"] = "p3"
        self.act("skip")
        self.reject("exchange_private")

    def test_dh_special_does_not_allow_a_second_paid_token(self):
        self.operating()
        self.s["phase"] = "3"
        self.s["privates"]["DH"]["owner"] = "B&O"
        self.act(
            "lay_tile", hex="F16", tile="57", rotation=0, special="DH", place_token=True
        )
        self.reject("place_token", hex="F16")

    def test_sold_out_movement_preserves_top_to_bottom_stack_order(self):
        self.stock()
        c = self.shares("NYC", "p1", 60)
        self.shares("NYC", "p2", 40)
        d = self.shares("PRR", "p2", 50)
        self.shares("PRR", "p3", 30)  # CA gift supplies remaining 10.
        E._position(self.s, c, [1, 14])
        E._position(self.s, d, [1, 14])
        for _ in range(3):
            self.act("pass")
        self.assertEqual(self.s["or_order"][:2], ["NYC", "PRR"])

    def test_tied_market_prices_same_column_use_upper_row_first(self):
        c = self.shares("PRR", "p1", 60)
        d = self.shares("B&M", "p2", 60)
        E._position(self.s, c, [6, 6])
        E._position(self.s, d, [5, 6])
        self.assertEqual(E._operating_order(self.s), ["B&M", "PRR"])

    def test_diesel_trade_in_is_allowed_at_train_limit(self):
        self.operating()
        self.to_train()
        self.s["phase"] = "6"
        self.train("B&O", "4-0")
        self.train("B&O", "5-0")
        self.act("buy_train", train="D-0", trade_in="4-0")
        self.assertEqual(self.s["corporations"]["B&O"]["trains"], ["5-0", "D-0"])
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 200)

    def test_table6_erratum_does_not_override_track_preservation(self):
        self.assertNotIn("45", UPGRADES["28"])
        self.assertIn("46", UPGRADES["28"])
        self.assertTrue(
            any(
                B.preserved_mapping(B.tile_for("28", 0), B.tile_for("46", r))
                is not None
                for r in range(6)
            )
        )
        self.assertFalse(
            any(
                B.preserved_mapping(B.tile_for("28", 0), B.tile_for("45", r))
                is not None
                for r in range(6)
            )
        )
