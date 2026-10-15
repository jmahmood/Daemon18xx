"""Standard 1889 variant rules, negative actions and complete-game validation."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from app.engine1889 import (
    new_game,
    apply_action,
    RuleError,
    replay,
    validate_state,
    legal_actions,
)
from app.engine1889 import engine as E, board as B
from app.engine1889.data import CERT_LIMITS, CORPORATIONS, BOARD_DATA


class Rules1889Tests(unittest.TestCase):
    def setUp(self):
        self.s = new_game(["Alice", "Bob", "Carol"])

    def act(self, action_type, **kw):
        player = kw.pop("player", self.s["current_player"])
        self.s = apply_action(self.s, dict(type=action_type, player=player, **kw))

    def reject(self, action_type, **kw):
        original = deepcopy(self.s)
        with self.assertRaises(RuleError):
            self.act(action_type, **kw)
        self.assertEqual(self.s, original)

    def stock(self, players=3):
        self.s = new_game(["Player " + str(i) for i in range(players)])
        for private in self.s["privates"]:
            self.act("buy_private", company=private)
        self.assertEqual(self.s["round"], "stock")

    def shares(self, cid, pid, amount):
        c = self.s["corporations"][cid]
        if c["par"] is None:
            E._set_par(self.s, c, 100)
        c["ipo"] -= amount
        c["holdings"][pid] += amount
        if c["president"] is None and amount >= 20:
            c["president"] = pid
        E._check_president(self.s, c)
        E._float(c)
        return c

    def cash(self, account, amount):
        self.s["bank"] += account["cash"] - amount
        account["cash"] = amount

    def operating(self):
        self.stock()
        self.shares("IR", "p1", 50)
        self.s["or_number"] = 1
        E._start_operating(self.s)

    def route(self):
        self.act("lay_tile", hex="E2", tile="5", rotation=4)

    def train_step(self):
        self.act("dividend", kind="withhold")

    def give_train(self, cid, tid):
        self.s["corporations"][cid]["trains"].append(tid)
        self.s["trains"][tid]["owner"] = cid

    def test_setup_all_player_counts_and_complete_components(self):
        for count in range(2, 7):
            s = new_game([str(i) for i in range(count)])
            cash = 420 if count <= 4 else 390
            self.assertEqual(s["bank"], 7000 - count * cash)
            self.assertTrue(all(p["cash"] == cash for p in s["players"].values()))
            self.assertEqual(len(s["board"]), 52)
            self.assertEqual(sum(s["tiles"].values()), 63)
            self.assertEqual(len(s["corporations"]), 7)
            self.assertEqual("SIR" in s["privates"], count > 2)
            self.assertEqual("UTF" in s["privates"], count >= 4)
            self.assertEqual(
                CERT_LIMITS[count], {2: 25, 3: 19, 4: 14, 5: 12, 6: 11}[count]
            )
            validate_state(s)
        self.assertEqual(B.neighbor("E2", 4), "F1")
        self.assertEqual(B.neighbor("E2", 5), "F3")
        self.assertEqual(
            {c: x[2] for c, x in CORPORATIONS.items()},
            {"AR": 2, "IR": 2, "SR": 2, "KO": 2, "TR": 3, "KU": 1, "UR": 3},
        )

    def test_auction_bids_escrow_discount_and_first_round_sales(self):
        self.act("bid", company="ER", price=45)
        self.act("bid", company="ER", price=50)
        self.act("buy_private", company="TR")
        self.act("buy_private", company="MF")
        self.assertEqual(self.s["auction"]["active"], "ER")
        self.act("pass")
        self.assertEqual(self.s["privates"]["ER"]["owner"], "p2")
        self.s = new_game(["A", "B", "C"])
        for _ in range(12):
            self.act("pass")
        self.assertEqual(self.s["privates"]["TR"]["owner"], "p1")
        self.stock()
        self.act("buy_shares", corporation="IR", price=100)
        self.reject("sell_shares", corporation="IR", percent=10)

    def test_par_fifty_percent_float_capital_and_home_once(self):
        for price in (65, 70, 75, 80, 90, 100):
            self.stock()
            self.act("buy_shares", corporation="IR", price=price)
        self.stock()
        self.reject("buy_shares", corporation="IR", price=67)
        self.shares("IR", "p1", 40)
        self.assertFalse(self.s["corporations"]["IR"]["floated"])
        self.shares("IR", "p2", 10)
        E._start_operating(self.s)
        self.assertEqual(self.s["corporations"]["IR"]["cash"], 1000)
        self.assertEqual(self.s["board"]["E2"]["tokens"], [["IR"]])
        E._start_operating(self.s)
        self.assertEqual(self.s["corporations"]["IR"]["cash"], 1000)

    def test_all_floated_home_stations_are_placed_at_operating_round_start(self):
        self.stock()
        self.shares("IR", "p1", 50)
        self.shares("KO", "p2", 50)
        E._start_operating(self.s)
        self.assertEqual(self.s["current_corporation"], "IR")
        self.assertEqual(self.s["board"]["E2"]["tokens"], [["IR"]])
        self.assertEqual(self.s["board"]["K4"]["tokens"], [["KO"]])
        self.assertTrue(B.blocked(self.s["board"], "K4:n0", "IR"))
        self.assertEqual(self.s["corporations"]["KO"]["cash"], 1000)
        validate_state(self.s)

    def test_sales_one_block_and_sell_buy_or_buy_sell_order(self):
        for buy_first in (False, True):
            self.stock()
            self.s["stock_round"] = 2
            self.shares("IR", "p1", 40)
            self.shares("AR", "p1", 40)
            if buy_first:
                self.act("buy_shares", corporation="SR", price=65)
            self.act("sell_shares", corporation="IR", percent=10)
            self.reject("sell_shares", corporation="IR", percent=10)
            if not buy_first:
                self.act("buy_shares", corporation="SR", price=65)
                self.reject("sell_shares", corporation="AR", percent=10)
            else:
                self.act("sell_shares", corporation="AR", percent=10)
        self.act("end_turn")
        self.act("pass")
        self.act("pass")
        self.reject("buy_shares", corporation="IR")

    def test_dougo_ipo_exchange_and_limits(self):
        self.stock()
        self.shares("IR", "p1", 20)
        self.act("exchange_private", player="p2", source="ipo")
        self.assertTrue(self.s["privates"]["DR"]["closed"])
        self.assertEqual(self.s["corporations"]["IR"]["holdings"]["p2"], 10)
        self.reject("exchange_private", player="p2")
        self.stock()
        self.shares("IR", "p1", 20)
        self.reject("exchange_private", player="p2", source="pool")
        self.shares("IR", "p2", 60)
        self.reject("exchange_private", player="p2")

    def test_private_sales_bounds_no_interplayer_and_utf_survival(self):
        self.operating()
        self.reject("buy_private", company="SMR", buyer="IR", price=50)
        self.s["phase"] = "3"
        self.reject("buy_private", company="SMR", buyer="IR", price=24)
        self.reject("buy_private", company="SMR", buyer="IR", price=101)
        self.act("buy_private", company="SMR", buyer="IR", price=25)
        self.assertEqual(self.s["privates"]["SMR"]["owner"], "IR")
        self.reject(
            "offer",
            kind="private",
            item="MF",
            seller="p2",
            buyer="p1",
            price=30,
            player="p2",
        )
        self.stock(4)
        owner = self.s["privates"]["UTF"]["owner"]
        E._phase_change(self.s, "5")
        self.assertFalse(self.s["privates"]["UTF"]["closed"])
        self.assertEqual(self.s["privates"]["UTF"]["revenue"], 50)
        self.assertTrue(
            all(p["closed"] for c, p in self.s["privates"].items() if c != "UTF")
        )
        before = self.s["players"][owner]["cash"]
        E._private_revenue(self.s)
        self.assertEqual(self.s["players"][owner]["cash"], before + 50)
        self.stock(4)
        self.s["privates"]["UTF"]["owner"] = "IR"
        E._phase_change(self.s, "5")
        self.assertTrue(self.s["privates"]["UTF"]["closed"])

    def test_mitsubishi_port_timing_permanence_and_one_use(self):
        self.operating()
        before = deepcopy(self.s["operating_turn"])
        self.act(
            "lay_tile", player="p2", special="MF", hex="G10", tile="437", rotation=0
        )
        self.assertEqual(self.s["current_player"], "p1")
        self.assertEqual(self.s["operating_turn"], before)
        self.assertFalse(self.s["privates"]["MF"]["closed"])
        self.reject(
            "lay_tile", player="p2", special="MF", hex="J9", tile="437", rotation=0
        )
        self.operating()
        self.route()
        self.reject(
            "lay_tile", player="p2", special="MF", hex="G10", tile="437", rotation=0
        )
        self.stock()
        self.reject(
            "lay_tile", player="p2", special="MF", hex="J5", tile="437", rotation=0
        )
        self.act(
            "lay_tile", player="p2", special="MF", hex="G10", tile="437", rotation=0
        )
        self.s["phase"] = "3"
        with self.assertRaises(RuleError):
            B.lay_tile(self.s, "IR", "G10", "14", 0, special="test")

    def test_ehime_seller_interrupt_lay_or_pass_and_resume(self):
        for lay in (False, True):
            self.operating()
            self.s["phase"] = "3"
            self.act(
                "offer",
                player="p3",
                kind="private",
                item="ER",
                seller="p3",
                buyer="IR",
                price=40,
            )
            self.act("buy_private", company="ER", buyer="IR", price=40)
            self.assertEqual(self.s["current_player"], "p3")
            self.assertEqual(legal_actions(self.s, "p1")["types"], [])
            self.reject("lay_tile", player="p1", hex="E2", tile="5", rotation=4)
            self.reject("lay_tile", player="p3", hex="C4", tile="57", rotation=1)
            if lay:
                self.act(
                    "lay_tile",
                    player="p3",
                    special="ER",
                    hex="C4",
                    tile="14",
                    rotation=1,
                )
                self.assertEqual(self.s["board"]["C4"]["tile"], "14")
            else:
                self.act("pass", player="p3")
            self.assertEqual(self.s["current_player"], "p1")
            self.assertFalse(self.s["operating_turn"]["laid"])
            self.route()

    def test_smr_only_discounts_pure_mountains_and_h_costs_repeat(self):
        self.operating()
        self.s["phase"] = "3"
        self.s["privates"]["SMR"]["owner"] = "IR"
        for coord, expected in (("D5", 0), ("I6", 80)):
            for rotation in range(6):
                trial = deepcopy(self.s)
                try:
                    cost = B.lay_tile(trial, "IR", coord, "8", rotation, special="test")
                except RuleError:
                    continue
                self.assertEqual(cost, expected)
                validate_state(trial)
                break
            else:
                self.fail("No legal terrain-test rotation")
        for tile, rotation, phase in (
            ("438", 0, "3"),
            ("439", 0, "3"),
            ("492", 0, "5"),
        ):
            self.s["phase"] = phase
            for rot in range(6):
                trial = deepcopy(self.s)
                try:
                    cost = B.lay_tile(trial, "IR", "I4", tile, rot, special="test")
                except RuleError:
                    continue
                self.assertEqual(cost, 80)
                self.s = trial
                break
            else:
                self.fail("No legal H-city upgrade")

    def test_diesel_revenue_uses_train_type_and_supply_is_unlimited(self):
        self.operating()
        self.route()
        self.give_train("IR", "5-0")
        self.give_train("IR", "D-0")
        self.s["phase"] = "D"
        for tid, expected in (("5-0", 80), ("D-0", 120)):
            route = next(
                r
                for r in B.route_candidates(self.s, "IR", tid)
                if "F1:n0" in r["vertices"]
            )
            self.assertEqual(B.validate_routes(self.s, "IR", [route]), expected)
        self.operating()
        self.route()
        self.train_step()
        self.s["phase"] = "6"
        self.cash(self.s["corporations"]["IR"], 20000)
        for i in range(8):
            tid = "D-" + str(i)
            self.act("buy_train", train=tid)
            self.s["corporations"]["IR"]["trains"].remove(tid)
            self.s["trains"][tid].update(owner="depot", used=True)
        self.assertIn("D-8", E.available_depot(self.s))

    def test_emergency_funding_no_subsidized_transfer_or_presidency_swaps(self):
        self.operating()
        self.route()
        self.train_step()
        self.cash(self.s["corporations"]["IR"], 0)
        self.shares("AR", "p2", 50)
        self.give_train("AR", "2-0")
        self.act(
            "offer",
            player="p2",
            kind="train",
            item="2-0",
            seller="AR",
            buyer="IR",
            price=80,
        )
        self.reject("buy_train", train="2-0", price=80)
        for cid in ("IR", "AR"):
            c = self.s["corporations"][cid]
            c["holdings"].update(p1=40, p2=30, p3=0)
            c.update(ipo=30, pool=0, president="p1")
            self.cash(self.s["players"]["p1"], 0)
            self.reject("emergency_sell", corporation=cid, percent=20)
        self.act("emergency_sell", corporation="IR", percent=10)
        self.act("buy_train", train="2-1")
        self.assertIn("2-1", self.s["corporations"]["IR"]["trains"])

    def test_emergency_sale_cannot_liquidate_more_than_needed(self):
        self.operating()
        self.route()
        self.train_step()
        self.cash(self.s["corporations"]["IR"], 0)
        self.cash(self.s["players"]["p1"], 0)
        self.reject("emergency_sell", corporation="IR", percent=20)
        self.act("emergency_sell", corporation="IR", percent=10)
        self.reject("emergency_sell", corporation="IR", percent=10)
        self.act("buy_train", train="2-0")

    def test_holding_and_total_certificate_color_exceptions(self):
        self.stock()
        self.shares("IR", "p1", 60)
        self.reject("buy_shares", corporation="IR")
        E._position(self.s, self.s["corporations"]["IR"], [8, 0])
        self.assertEqual(
            E.certificate_count(self.s, "p1"), 2
        )  # two open privates, stock exempt
        self.act("buy_shares", corporation="IR")
        self.assertEqual(self.s["corporations"]["IR"]["holdings"]["p1"], 70)

    def test_bankruptcy_and_bank_end_scoring(self):
        self.operating()
        self.route()
        self.train_step()
        c = self.s["corporations"]["IR"]
        c["holdings"].update(p1=30, p2=30, p3=0)
        c.update(ipo=40, pool=0)
        self.cash(c, 0)
        self.cash(self.s["players"]["p1"], 0)
        self.act("bankrupt")
        self.assertTrue(self.s["finished"])
        self.assertEqual(self.s["end_reason"], "bankruptcy")
        self.assertEqual(self.s["result"]["p1"], 270)

    def test_parallel_variants_and_replay_isolation(self):
        from app.engine1830 import new_game as game1830, apply_action as action1830

        other = game1830(["A", "B", "C"])
        original = deepcopy(other)
        self.stock()
        self.assertEqual(other, original)
        snapshot = deepcopy(self.s)
        other = action1830(
            other, {"type": "buy_private", "company": "SV", "player": "p1"}
        )
        self.assertEqual(self.s, snapshot)
        self.assertEqual(
            self.s,
            replay([p["name"] for p in self.s["players"].values()], self.s["history"]),
        )
        self.assertEqual(other["variant"], "1830")
        self.assertEqual(self.s["variant"], "1889")

    def test_authored_complete_game_all_seven_corporations_and_every_phase(self):
        record = json.loads(
            (
                Path(__file__).parent / "fixtures" / "1889" / "authored_all_phases.json"
            ).read_text()
        )
        state = replay(record["names"], record["actions"])
        self.assertTrue(state["finished"])
        self.assertEqual(state["end_reason"], "bank")
        self.assertEqual(
            state["result"], {"p1": 2725, "p2": 2787, "p3": 4442, "p4": 2741}
        )
        self.assertTrue(
            all(
                c["floated"] and c["home_placed"]
                for c in state["corporations"].values()
            )
        )
        self.assertEqual(
            [x for x in state["log"] if x.startswith("Phase")],
            ["Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase D"],
        )
        self.assertEqual(state["or_number"], state["or_total"])
        validate_state(state)

    def test_historical_314_illegal_route_is_rejected_without_weakening_blocking(self):
        record = json.loads(
            (
                Path(__file__).parent / "fixtures" / "1889" / "314_rejected_route.json"
            ).read_text()
        )
        state = replay(record["names"], record["actions"], record["player_ids"])
        self.assertEqual(state["board"]["I2"]["tokens"], [["SR", "AR"]])
        original = deepcopy(state)
        with self.assertRaisesRegex(RuleError, "blocked city"):
            apply_action(
                state,
                {
                    "type": "run_routes",
                    "player": state["current_player"],
                    "routes": [record["invalid_route"]],
                },
            )
        self.assertEqual(state, original)

    def test_rust_discard_returned_trains_and_diesel_trade_in(self):
        self.operating()
        self.route()
        for tid in ("2-0", "2-1", "3-0", "3-1"):
            self.give_train("IR", tid)
        E._phase_change(self.s, "4")
        self.assertEqual(self.s["corporations"]["IR"]["trains"], ["3-0", "3-1"])
        self.give_train("IR", "4-0")
        self.give_train("IR", "4-1")
        E._phase_change(self.s, "5")
        self.assertEqual(self.s["pending_discards"], ["IR"])
        self.reject("skip")
        self.act("discard_train", corporation="IR", train="3-0")
        self.act("discard_train", corporation="IR", train="3-1")
        self.assertIn("3-0", E.available_depot(self.s))
        E._phase_change(self.s, "6")
        self.assertTrue(self.s["trains"]["3-0"]["rusted"])
        self.cash(self.s["corporations"]["IR"], 2000)
        self.s["operating_turn"].update(
            step="train", routes=[], revenue=0, dividend=True
        )
        self.act("buy_train", train="D-0", trade_in="4-0", price=800)
        self.assertTrue(self.s["trains"]["4-0"]["rusted"])
        self.assertTrue(self.s["trains"]["4-1"]["rusted"])
        self.assertEqual(self.s["corporations"]["IR"]["cash"], 1200)
        self.assertEqual(self.s["corporations"]["IR"]["trains"], ["D-0"])

    def test_independent_complete_game_exact_scores_and_all_phases(self):
        record = json.loads(
            (Path(__file__).parent / "fixtures" / "1889" / "962.json").read_text()
        )
        s = new_game(record["names"], record["player_ids"])
        phases = set()
        for action in record["actions"]:
            old = deepcopy(s)
            s = apply_action(s, action)
            self.assertEqual(old["revision"] + 1, s["revision"])
            phases.add(s["phase"])
        self.assertTrue(s["finished"])
        self.assertEqual(s["result"], record["result"])
        self.assertEqual(s["end_reason"], "bank")
        self.assertEqual(phases, {"2", "3", "4", "5"})
        self.assertEqual(s, json.loads(json.dumps(s)))
