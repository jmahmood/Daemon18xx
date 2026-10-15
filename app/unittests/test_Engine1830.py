"""Rulebook-based tests for the pure 1830 backend, including rejected actions."""

import json
import unittest
from copy import deepcopy

from app.engine1830 import new_game, apply_action, replay, RuleError, check_invariants
from app.engine1830 import engine as E
from app.engine1830 import board as B
from app.engine1830.data import CORPORATIONS, TRAIN_SPECS, CERT_LIMIT
from app.engine1830.board_data import DATA


class Rules1830Tests(unittest.TestCase):
    def setUp(self):
        self.s = new_game(["Alice", "Bob", "Carol"])

    def act(self, action_type, **args):
        actor = args.pop("player", self.s["current_player"])
        self.s = apply_action(self.s, dict(type=action_type, player=actor, **args))
        return self.s

    def reject(self, action_type, **args):
        original = deepcopy(self.s)
        with self.assertRaises(RuleError):
            self.act(action_type, **args)
        self.assertEqual(self.s, original)

    def stock(self):
        for pid in self.s["privates"]:
            self.act("buy_private", company=pid)
            if self.s["pending_par"] is not None:
                self.act("par", player=self.s["pending_par"], price=100)
        self.assertEqual(self.s["round"], "stock")

    def cash(self, account, amount):
        self.s["bank"] += account["cash"] - amount
        account["cash"] = amount

    def shares(self, cid, pid, amount, par=100):
        c = self.s["corporations"][cid]
        if c["par"] is None:
            E._set_par(self.s, c, par)
        c["ipo"] -= amount
        c["holdings"][pid] += amount
        if c["president"] is None and amount >= 20:
            c["president"] = pid
        E._presidency(self.s, c)
        E._float(c)
        return c

    def operating(self, cid="B&O"):
        self.stock()
        c = self.s["corporations"][cid]
        owner = c["president"] or "p1"
        self.shares(cid, owner, 60 - sum(c["holdings"].values()))
        self.s["or_number"] = 1
        E._start_or(self.s)
        check_invariants(self.s)
        return c

    def train(self, cid, tid):
        c = self.s["corporations"][cid]
        c["trains"].append(tid)
        self.s["trains"][tid].update(owner=cid, bought_at=-1)

    def washington(self):
        B.lay_tile(self.s, "B&O", "J14", "57", 0)
        self.s["privates"]["BO"]["closed"] = True

    def to_train(self):
        for step in ("track", "token", "routes"):
            if self.s["operating_turn"]["step"] == step:
                self.act("skip")
        if self.s["operating_turn"]["step"] == "dividend":
            self.act("dividend", kind="withhold")

    def test_setup_all_player_counts_and_money(self):
        for count in range(2, 7):
            s = new_game([str(i) for i in range(count)])
            self.assertEqual(
                [p["cash"] for p in s["players"].values()], [2400 // count] * count
            )
            self.assertEqual(s["bank"], 9600)
            self.assertEqual(len(s["corporations"]), 8)
            self.assertEqual(len(s["board"]), 93)
            check_invariants(s)

    def test_setup_rejects_invalid_players(self):
        for names in ([], ["A"], ["A"] * 3, ["A", ""], list("ABCDEFG")):
            with self.assertRaises(RuleError):
                new_game(names)

    def test_independent_games_and_json_roundtrip(self):
        original = deepcopy(self.s)
        self.act("buy_private", company="SV")
        self.assertEqual(new_game(["Alice", "Bob", "Carol"]), original)
        self.assertEqual(json.loads(json.dumps(self.s)), self.s)

    def test_action_atomicity_wrong_player_unknown_action_and_stale_version(self):
        self.reject("buy_private", company="SV", player="p2")
        self.reject("nonsense")
        self.reject("buy_private", company="SV", expected_action_id=4)
        self.reject("buy_private", company="missing")

    def test_initial_private_order_and_prices(self):
        self.reject("buy_private", company="CS")
        self.reject("buy_private", company="SV", price=0)
        self.act("buy_private", company="SV")
        self.assertEqual(self.s["players"]["p1"]["cash"], 780)
        self.assertEqual(self.s["privates"]["SV"]["owner"], "p1")
        self.assertEqual(self.s["current_player"], "p2")

    def test_auction_minimum_and_reserved_cash(self):
        self.reject("bid", company="BO", price=224)
        self.act("bid", company="BO", price=700)
        self.act("pass")
        self.act("pass")
        self.reject("bid", company="CA", price=165)
        self.act("bid", company="BO", price=705)
        self.assertEqual(self.s["players"]["p1"]["cash"], 95)
        self.assertEqual(self.s["players"]["p1"]["cash"], 95)

    def test_auction_bid_increment_and_single_bid_resolution(self):
        self.act("bid", company="CS", price=45)
        self.act("buy_private", company="SV")
        self.assertEqual(self.s["privates"]["CS"]["owner"], "p1")
        self.assertEqual(self.s["players"]["p1"]["cash"], 755)
        self.assertEqual(self.s["current_player"], "p3")

    def test_competitive_auction_and_resume(self):
        self.act("bid", company="CS", price=45)
        self.act("bid", company="CS", price=50)
        self.act("buy_private", company="SV")
        self.assertEqual(self.s["auction"]["active"], "CS")
        self.assertEqual(self.s["current_player"], "p1")
        self.reject("bid", company="CS", price=54)
        self.act("bid", company="CS", price=55)
        self.act("pass")
        self.assertEqual(self.s["privates"]["CS"]["owner"], "p1")
        self.assertEqual(self.s["players"]["p1"]["cash"], 745)
        self.assertEqual(self.s["players"]["p2"]["cash"], 800)
        self.assertEqual(self.s["current_player"], "p1")

    def test_sv_discount_and_forced_free_purchase(self):
        for _ in range(12):
            self.act("pass")
        self.assertEqual(self.s["privates"]["SV"]["owner"], "p1")
        self.assertEqual(self.s["players"]["p1"]["cash"], 800)
        self.assertEqual(20 - self.s["auction"]["discount"], 0)

    def test_other_privates_do_not_discount_and_pay_revenue(self):
        self.act("buy_private", company="SV")
        for _ in range(3):
            self.act("pass")
        self.assertEqual(self.s["privates"]["CS"]["value"], 40)
        self.assertEqual(self.s["players"]["p1"]["cash"], 785)

    def test_ca_free_prr_share_and_bo_presidency(self):
        self.stock()
        self.assertEqual(self.s["corporations"]["PRR"]["holdings"]["p2"], 10)
        self.assertEqual(self.s["corporations"]["B&O"]["holdings"]["p3"], 20)
        self.assertEqual(self.s["corporations"]["B&O"]["par"], 100)

    def test_bo_par_interrupts_auction(self):
        for pid in ["SV", "CS", "DH", "MH", "CA"]:
            self.act("buy_private", company=pid)
        self.act("buy_private", company="BO")
        self.assertEqual(self.s["pending_par"], "p3")
        self.reject("pass")
        self.reject("par", player="p3", price=80)
        self.act("par", player="p3", price=67)
        self.assertEqual(self.s["round"], "stock")

    def test_president_first_and_one_purchase_per_turn(self):
        self.stock()
        self.reject("buy_shares", corporation="NYC", percent=10, par=100)
        self.act("buy_shares", corporation="NYC", par=100)
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 20)
        self.reject("buy_shares", corporation="NYC")

    def test_par_prices_are_exact(self):
        self.stock()
        self.reject("buy_shares", corporation="NYC", par=80)
        self.act("buy_shares", corporation="NYC", par=67)
        self.assertEqual(E.price(self.s["corporations"]["NYC"]), 67)

    def test_no_sales_in_first_stock_round(self):
        self.stock()
        self.reject("sell_shares", corporation="PRR", percent=10, player="p1")

    def test_sale_pays_pre_sale_price_and_pool_limits(self):
        self.stock()
        c = self.shares("NYC", "p1", 60)
        self.s["stock_round"] = 2
        before = self.s["players"]["p1"]["cash"]
        self.act("sell_shares", corporation="NYC", percent=40)
        self.assertEqual(self.s["players"]["p1"]["cash"], before + 400)
        self.assertEqual(c["pool"], 0)  # accepted actions produce a new state
        c = self.s["corporations"]["NYC"]
        self.assertEqual(c["pool"], 40)
        self.assertEqual(c["position"], [4, 6])
        self.reject("sell_shares", corporation="NYC", percent=20)

    def test_sell_then_buy_uses_proceeds(self):
        self.stock()
        self.s["stock_round"] = 2
        self.shares("NYC", "p1", 60)
        self.cash(self.s["players"]["p1"], 0)
        self.act("sell_shares", corporation="NYC", percent=20)
        self.act("buy_shares", corporation="CPR", par=100)
        self.assertEqual(self.s["players"]["p1"]["cash"], 0)

    def test_buy_then_sell_same_corporation_is_allowed(self):
        self.stock()
        self.s["stock_round"] = 2
        self.shares("NYC", "p1", 20)
        self.act("buy_shares", corporation="NYC")
        self.act("sell_shares", corporation="NYC", percent=10)
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 20)

    def test_sold_company_restriction_is_per_player(self):
        self.stock()
        self.s["stock_round"] = 2
        self.shares("NYC", "p1", 30)
        self.act("sell_shares", corporation="NYC", percent=10)
        self.reject("buy_shares", corporation="NYC")
        self.act("end_turn")
        self.act("buy_shares", corporation="NYC", source="pool")
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p2"], 10)

    def test_presidency_transfer_and_wraparound_tie(self):
        self.stock()
        self.s["stock_round"] = 2
        self.shares("NYC", "p3", 40)
        self.shares("NYC", "p1", 20)
        self.shares("NYC", "p2", 20)
        self.s["current_player"] = "p3"
        self.act("sell_shares", corporation="NYC", percent=30)
        self.assertEqual(self.s["corporations"]["NYC"]["president"], "p1")

    def test_presidency_does_not_transfer_on_equal_holdings(self):
        self.stock()
        self.shares("NYC", "p2", 30)
        self.shares("NYC", "p1", 30)
        self.assertEqual(self.s["corporations"]["NYC"]["president"], "p2")

    def test_president_cannot_dump_without_successor(self):
        self.stock()
        self.s["stock_round"] = 2
        self.shares("NYC", "p1", 20)
        self.reject("sell_shares", corporation="NYC", percent=10)

    def test_certificate_table_and_president_counts_once(self):
        self.stock()
        self.assertEqual(CERT_LIMIT, {2: 28, 3: 20, 4: 16, 5: 13, 6: 11})
        before = E.certificates(self.s, "p1")
        self.act("buy_shares", corporation="NYC", par=100)
        self.assertEqual(E.certificates(self.s, "p1"), before + 1)

    def test_yellow_orange_brown_exempt_total_certificate_limit(self):
        self.stock()
        c = self.shares("NYC", "p1", 60)
        for cell in [(0, 0), (3, 0), (5, 0)]:
            E._position(self.s, c, cell)
            self.assertEqual(E.certificates(self.s, "p1"), 2)

    def test_orange_allows_more_than_five_certificates(self):
        self.stock()
        c = self.shares("NYC", "p1", 60)
        self.reject("buy_shares", corporation="NYC")
        E._position(self.s, self.s["corporations"]["NYC"], [3, 0])
        self.act("buy_shares", corporation="NYC")
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 70)

    def test_brown_multiple_buys_same_company(self):
        self.stock()
        c = self.shares("NYC", "p1", 20)
        E._position(self.s, c, [5, 0])
        self.act("buy_shares", corporation="NYC")
        self.act("buy_shares", corporation="NYC")
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 40)

    def test_consecutive_passes_and_priority(self):
        self.stock()
        self.act("pass")  # 0
        self.act("buy_shares", corporation="NYC", par=100)  # 1
        self.act("end_turn")
        self.act("pass")  # 2
        self.act("pass")  # 0
        self.assertEqual(self.s["round"], "stock")
        self.act("pass")  # 1 -- consecutive passes span seating boundary
        self.assertEqual(
            self.s["round"], "stock"
        )  # no floated corporations: empty OR, next SR
        self.assertEqual(self.s["stock_round"], 2)
        self.assertEqual(self.s["priority"], "p3")

    def test_flotation_capital_only_once_at_or_start(self):
        self.stock()
        c = self.shares("NYC", "p1", 60, par=90)
        self.assertTrue(c["floated"])
        self.assertEqual(c["cash"], 0)
        E._start_or(self.s)
        self.assertEqual(c["cash"], 900)
        E._start_or(self.s)
        self.assertEqual(c["cash"], 900)

    def test_stock_market_right_edge_up_and_left_edge_down(self):
        c = self.shares("NYC", "p1", 60)
        E._position(self.s, c, [2, 15])
        E._move_market(self.s, c, "right")
        self.assertEqual(c["position"], [1, 15])
        E._position(self.s, c, [0, 0])
        E._move_market(self.s, c, "left")
        self.assertEqual(c["position"], [1, 0])

    def test_market_movement_does_not_change_par(self):
        c = self.shares("NYC", "p1", 60)
        E._move_market(self.s, c, "down", 2)
        self.assertEqual(c["par"], 100)
        self.assertEqual(E.price(c), 82)

    def test_sold_out_rises_only_for_floated_corporations(self):
        self.stock()
        c = self.shares("NYC", "p1", 60)
        self.shares("NYC", "p2", 40)
        E._position(self.s, c, [2, 6])
        for _ in range(3):
            self.act("pass")
        self.assertEqual(self.s["corporations"]["NYC"]["position"], [1, 6])

    def test_operating_order_rightmost_then_stack(self):
        c = self.shares("NYC", "p1", 60)
        d = self.shares("CPR", "p2", 60)
        E._position(self.s, c, [2, 9])
        E._position(self.s, d, [0, 6])  # 100 vs 100
        self.assertEqual(E._operating_order(self.s), ["NYC", "CPR"])
        E._position(self.s, c, [0, 6])
        self.assertEqual(E._operating_order(self.s), ["CPR", "NYC"])

    def test_free_home_token_and_turn_authorization(self):
        self.operating()
        c = self.s["corporations"]["B&O"]
        self.assertTrue(c["home_placed"])
        self.assertEqual(c["cash"], 1000)
        self.assertEqual(self.s["board"]["I15"]["tokens"], [["B&O"]])
        self.reject("skip", player="p1")
        self.reject("buy_train", train="2-0")

    def test_dividends_bank_pool_not_ipo(self):
        self.operating()
        c = self.s["corporations"]["B&O"]
        c["holdings"]["p3"] = 50
        c["ipo"] = 30
        c["pool"] = 20
        self.s["operating_turn"].update(step="dividend", routes=[])
        self.s["operating_turn"]["revenue"] = 50
        before = self.s["players"]["p3"]["cash"]
        treasury = c["cash"]
        self.act("dividend", kind="payout")
        self.assertEqual(self.s["players"]["p3"]["cash"], before + 25)
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], treasury + 10)

    def test_withhold_and_zero_revenue_move_left(self):
        self.operating()
        self.s["operating_turn"].update(step="dividend", routes=[])
        self.s["operating_turn"]["revenue"] = 80
        self.act("dividend", kind="withhold")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 1080)
        self.assertEqual(self.s["corporations"]["B&O"]["position"], [0, 5])

    def test_private_revenue_to_treasury_not_dividends(self):
        self.operating()
        p = self.s["privates"]["SV"]
        p.update(owner="B&O", owner_type="corporation")
        before = self.s["corporations"]["B&O"]["cash"]
        E._private_revenue(self.s)
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], before + 5)
        self.assertEqual(self.s["operating_turn"]["revenue"], 0)

    def test_hex_neighbors_and_fixed_track(self):
        self.assertEqual(B.neighbor("I15", 0), "J14")
        self.assertEqual(B.neighbor("I15", 4), "I17")
        self.assertEqual(B.neighbor("I15", 3), "H16")
        for h in DATA["hexes"]:
            for e in range(6):
                other = B.neighbor(h, e)
                if other in DATA["hexes"]:
                    self.assertEqual(B.neighbor(other, (e + 3) % 6), h)

    def test_track_terrain_charge_and_finite_supply(self):
        self.operating()
        self.act("lay_tile", hex="J14", tile="57", rotation=0)
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 920)
        self.assertEqual(self.s["tiles"]["57"], 3)
        self.assertEqual(self.s["operating_turn"]["step"], "token")
        self.reject("lay_tile", hex="I17", tile="9", rotation=1)

    def test_track_rejects_disconnected_wrong_city_type_and_color(self):
        self.operating()
        self.reject("lay_tile", hex="E19", tile="57", rotation=0)
        self.reject("lay_tile", hex="J14", tile="9", rotation=1)
        self.reject("lay_tile", hex="J14", tile="14", rotation=0)
        self.reject("lay_tile", hex="F6", tile="57", rotation=0)

    def test_player_private_blocks_hex(self):
        self.operating()
        self.reject("lay_tile", hex="G15", tile="9", rotation=1)

    def test_track_upgrade_preserves_track_and_returns_tile(self):
        self.operating()
        self.act("lay_tile", hex="J14", tile="57", rotation=0)
        self.s["operating_turn"].update(step="track", laid=False)
        self.s["phase"] = "3"
        self.act("lay_tile", hex="J14", tile="14", rotation=2)
        self.assertEqual(self.s["tiles"]["57"], 4)
        self.assertEqual(self.s["tiles"]["14"], 2)
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 920)

    def test_track_upgrade_cannot_remove_track(self):
        self.operating()
        self.act("lay_tile", hex="J14", tile="57", rotation=0)
        self.s["operating_turn"].update(step="track", laid=False)
        self.s["phase"] = "3"
        self.reject("lay_tile", hex="J14", tile="15", rotation=1)

    def test_station_costs_reachability_and_one_per_turn(self):
        self.operating()
        self.washington()
        self.s["operating_turn"]["step"] = "token"
        before = self.s["corporations"]["B&O"]["cash"]
        self.act("place_token", hex="J14")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], before - 40)
        self.assertEqual(
            sum(
                "B&O" in ts
                for tile in self.s["board"].values()
                for ts in tile["tokens"]
            ),
            2,
        )
        self.reject("place_token", hex="J14")

    def test_station_rejects_duplicate_and_unreachable_city(self):
        self.operating()
        self.s["operating_turn"]["step"] = "token"
        self.reject("place_token", hex="I15")
        self.reject("place_token", hex="A19")

    def test_route_uses_actual_revenue_and_train_capacity(self):
        self.operating()
        self.washington()
        self.train("B&O", "2-0")
        revenue, details = B.route_revenue(
            self.s, "B&O", [{"train": "2-0", "paths": [["I15", 1], ["J14", 1]]}]
        )
        self.assertEqual(revenue, 50)
        self.assertEqual(details[0]["stops"], ["I15:n0", "J14:n0"])

    def test_route_requires_token_on_every_route_and_no_shared_track(self):
        self.operating()
        self.washington()
        self.train("B&O", "2-0")
        self.train("B&O", "2-1")
        route = {"train": "2-0", "paths": [["I15", 1], ["J14", 1]]}
        with self.assertRaises(RuleError):
            B.route_revenue(self.s, "B&O", [route, dict(route, train="2-1")])
        with self.assertRaises(RuleError):
            B.route_revenue(self.s, "NYC", [route])

    def test_route_cannot_reuse_train_or_disconnected_track(self):
        self.operating()
        self.washington()
        self.train("B&O", "2-0")
        with self.assertRaises(RuleError):
            B.route_revenue(
                self.s, "B&O", [{"train": "2-0", "paths": [["I15", 0], ["J14", 1]]}]
            )
        with self.assertRaises(RuleError):
            B.route_revenue(
                self.s, "B&O", [{"train": "2-0", "paths": [["I15", 1], ["I15", 1]]}]
            )

    def test_trains_are_finite_and_bought_in_order(self):
        self.operating()
        self.to_train()
        self.reject("buy_train", train="3-0")
        self.act("buy_train", train="2-0")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 920)
        self.assertEqual(self.s["trains"]["2-0"]["owner"], "B&O")
        self.assertTrue(self.s["privates"]["BO"]["closed"])
        self.reject("buy_train", train="2-0")

    def test_phase_changes_rust_close_and_limits(self):
        self.train("B&O", "2-0")
        self.train("NYC", "3-0")
        self.train("CPR", "4-0")
        E._phase_change(self.s, "4")
        self.assertTrue(self.s["trains"]["2-0"]["rusted"])
        self.assertEqual(self.s["corporations"]["B&O"]["trains"], [])
        self.assertEqual(E.train_limit(self.s), 3)
        E._phase_change(self.s, "5")
        self.assertTrue(all(p["closed"] for p in self.s["privates"].values()))
        self.assertEqual(E.train_limit(self.s), 2)
        E._phase_change(self.s, "6")
        self.assertTrue(self.s["trains"]["3-0"]["rusted"])
        E._phase_change(self.s, "D")
        self.assertTrue(self.s["trains"]["4-0"]["rusted"])
        check_invariants(self.s)

    def test_mandatory_train_and_presidential_contribution_not_loan(self):
        self.operating()
        self.washington()
        self.to_train()
        self.cash(self.s["corporations"]["B&O"], 20)
        before = self.s["players"]["p3"]["cash"]
        self.reject("end_turn")
        self.act("buy_train", train="2-0")
        self.assertEqual(self.s["corporations"]["B&O"]["cash"], 0)
        self.assertEqual(self.s["players"]["p3"]["cash"], before - 60)

    def test_no_presidential_funding_for_optional_train(self):
        self.operating()
        self.to_train()
        self.cash(self.s["corporations"]["B&O"], 0)
        self.reject("buy_train", train="2-0")

    def test_mh_exchange_closes_private_and_transfers_share(self):
        self.stock()
        self.shares("NYC", "p2", 20)
        self.act("exchange_mh", player="p1")
        self.assertTrue(self.s["privates"]["MH"]["closed"])
        self.assertEqual(self.s["corporations"]["NYC"]["holdings"]["p1"], 10)
        self.reject("exchange_mh", player="p1")

    def test_private_sale_requires_consent_and_corporate_phase_price(self):
        self.operating()
        self.act(
            "offer",
            player="p1",
            kind="private",
            item="SV",
            seller="p1",
            buyer="B&O",
            price=40,
        )
        self.reject(
            "buy_private", company="SV", buyer="B&O", buyer_type="corporation", price=40
        )
        self.s["phase"] = "3"
        self.reject(
            "buy_private", company="SV", buyer="B&O", buyer_type="corporation", price=41
        )
        self.act(
            "buy_private", company="SV", buyer="B&O", buyer_type="corporation", price=40
        )
        self.assertEqual(self.s["privates"]["SV"]["owner"], "B&O")

    def test_bankruptcy_ends_immediately_and_scoring(self):
        self.operating()
        self.washington()
        self.to_train()
        self.cash(self.s["corporations"]["B&O"], 0)
        self.cash(self.s["players"]["p3"], 0)
        c = self.s["corporations"]["B&O"]
        c["holdings"]["p3"], c["ipo"], c["pool"] = 20, 30, 50
        self.act("bankruptcy")
        self.assertTrue(self.s["finished"])
        self.assertEqual(self.s["end_reason"], "bankruptcy")
        self.assertEqual(self.s["result"]["p3"], 180)

    def test_bank_end_waits_for_complete_operating_set(self):
        self.operating()
        self.s["or_total"] = 2
        self.s["bank_broken"] = True
        self.s["end_after_set"] = True
        self.to_train()
        self.act("end_turn")
        self.assertFalse(self.s["finished"])
        self.assertEqual(self.s["or_number"], 2)
        self.to_train()
        self.act("end_turn")
        self.assertTrue(self.s["finished"])
        self.assertEqual(self.s["end_reason"], "bank")
        self.reject("pass")

    def test_replay_is_deterministic_and_json_safe(self):
        self.stock()
        restored = replay(["Alice", "Bob", "Carol"], self.s["history"])
        self.assertEqual(restored, self.s)


if __name__ == "__main__":
    unittest.main()
