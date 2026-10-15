"""Rulebook acceptance tests for the JSON 1830 backend."""

import json
import unittest
from copy import deepcopy

from app.engine1830 import new_game, apply_action, RuleError, scores, validate_state
from app.engine1830 import engine as e, board as b
from app.engine1830.data import (
    CORPORATIONS,
    BOARD_DATA,
    TRAIN_TYPES,
    CERT_LIMITS,
    MARKET,
)


class Rules1830Tests(unittest.TestCase):
    def setUp(self):
        self.s = new_game(["Alice", "Bob", "Carol"])

    def do(self, kind, **kwargs):
        self.s = apply_action(
            self.s, dict(type=kind, player=self.s["current_player"], **kwargs)
        )
        return self.s

    def auction_done(self):
        for private in list(self.s["privates"]):
            self.do("bid", company=private, price=self.s["privates"][private]["value"])
            if self.s["pending_par"]:
                self.s = apply_action(
                    self.s,
                    {"type": "par", "player": self.s["pending_par"], "price": 67},
                )
        self.assertEqual(self.s["round"], "stock")

    def operating(self, cid="C&O", par=100):
        # A legitimate stock sequence; player 1 starts C&O and player 2 buys the remaining float shares.
        self.auction_done()
        self.do("buy_shares", corporation=cid, price=par)
        self.do("end_turn")
        for _ in range(4):
            self.do("buy_shares", corporation=cid)
            self.do("end_turn")
        for _ in range(3):
            self.do("pass")
        self.assertEqual(self.s["round"], "operating")
        self.assertEqual(self.s["current_corporation"], cid)

    def give_stock(self, cid, player, percent, par=67):
        c = self.s["corporations"][cid]
        if c["par"] is None:
            e._set_par(self.s, c, par)
        c["ipo"] -= percent
        c["holdings"][player] += percent
        if c["president"] is None and percent >= 20:
            c["president"] = player
        e._check_president(self.s, c)
        e._float(c)
        return c

    def fund(self, cid, cash):
        e._pay(self.s, "bank", cid, cash)

    def add_train(self, cid, tid):
        self.s["trains"][tid]["owner"] = cid
        self.s["corporations"][cid]["trains"].append(tid)

    def test_setup_component_inventory_and_isolation(self):
        self.assertEqual(len(self.s["corporations"]), 8)
        self.assertEqual(sum(self.s["tiles"].values()), 85)
        self.assertEqual(len(self.s["board"]), 93)
        self.assertEqual(
            CounterTypes(self.s), {t: data[0] for t, data in TRAIN_TYPES.items()}
        )
        self.assertEqual(self.s["bank"], 9600)
        for n, cash in [(2, 1200), (3, 800), (4, 600), (5, 480), (6, 400)]:
            state = new_game([str(i) for i in range(n)])
            self.assertEqual(state["players"]["p1"]["cash"], cash)
        second = new_game(["A", "B", "C"])
        self.s["board"]["F6"]["tokens"][0].append("C&O")
        self.assertEqual(second["board"]["F6"]["tokens"][0], [])
        self.assertEqual(new_game(["A", "B", "C"]), json.loads(json.dumps(second)))

    def test_action_is_atomic_and_revision_checked(self):
        old = deepcopy(self.s)
        with self.assertRaises(RuleError):
            self.do("bid", company="BO", price=9999)
        self.assertEqual(self.s, old)
        with self.assertRaises(RuleError):
            apply_action(self.s, {"type": "pass", "player": "p2"})
        with self.assertRaises(RuleError):
            apply_action(self.s, {"type": "pass", "player": "p1"}, expected_revision=99)
        result = apply_action(
            self.s, {"type": "bid", "player": "p1", "company": "SV", "price": 20}
        )
        self.assertEqual(self.s, old)
        self.assertEqual(result["revision"], 1)

    def test_auction_all_sold_gifts_par_and_round(self):
        self.auction_done()
        self.assertEqual(self.s["corporations"]["PRR"]["holdings"]["p2"], 10)
        self.assertEqual(self.s["corporations"]["B&O"]["holdings"]["p3"], 20)
        self.assertEqual(self.s["corporations"]["B&O"]["par"], 67)
        self.assertEqual(self.s["stock_round"], 1)
        self.assertEqual(sum(p["cash"] for p in self.s["players"].values()), 1780)
        validate_state(self.s)

    def test_auction_escrow_raise_and_release(self):
        self.do("bid", company="CS", price=45)
        self.do("bid", company="CS", price=50)
        self.do("bid", company="SV", price=20)
        self.assertEqual(self.s["auction"]["active"], "CS")
        self.assertEqual(self.s["current_player"], "p1")
        self.do("bid", company="CS", price=55)
        self.assertEqual(self.s["players"]["p1"]["cash"], 745)
        self.do("pass")
        self.assertEqual(self.s["privates"]["CS"]["owner"], "p1")
        self.assertEqual(self.s["players"]["p2"]["cash"], 800)
        self.assertEqual(self.s["players"]["p1"]["cash"], 745)
        validate_state(self.s)

    def test_sv_discount_and_forced_free_purchase(self):
        for _ in range(12):
            self.do("pass")
        self.assertEqual(self.s["auction"]["discount"], 20)
        self.assertEqual(self.s["privates"]["SV"]["owner"], "p1")

    def test_other_unsold_private_pays_revenue_without_discount(self):
        self.do("bid", company="SV", price=20)
        cash = self.s["players"]["p1"]["cash"]
        for _ in range(3):
            self.do("pass")
        self.assertEqual(self.s["players"]["p1"]["cash"], cash + 5)
        self.assertEqual(self.s["auction"]["discount"], 0)
        self.do("bid", company="CS", price=40)

    def test_stock_first_sale_restriction_and_five_certificate_holding(self):
        self.auction_done()
        self.do("buy_shares", corporation="C&O", price=100)
        with self.assertRaises(RuleError):
            self.do("sell_shares", corporation="C&O", percent=10)
        with self.assertRaises(RuleError):
            self.do("buy_shares", corporation="PRR", price=67)
        self.assertEqual(CERT_LIMITS, {2: 28, 3: 20, 4: 16, 5: 13, 6: 11})

    def test_float_capital_home_token_and_no_premature_train_use(self):
        self.operating()
        corp = self.s["corporations"]["C&O"]
        self.assertEqual(corp["cash"], 1000)
        self.assertEqual(self.s["board"]["F6"]["tokens"][0], ["C&O"])
        self.do("dividend", payout=False)
        self.do("buy_train", train="2-0")
        self.assertEqual(
            corp["cash"], 1000
        )  # The prior snapshot must remain unchanged.
        self.assertEqual(self.s["corporations"]["C&O"]["cash"], 920)
        with self.assertRaises(RuleError):
            self.do("run_routes", routes=[])
        self.do("end_turn")
        self.assertEqual(self.s["round"], "stock")
        self.assertEqual(self.s["stock_round"], 2)

    def test_sale_pays_before_market_drop_and_sell_buy_allowed(self):
        self.auction_done()
        corp = self.give_stock("C&O", "p1", 30, 100)
        self.s["stock_round"] = 2
        before = self.s["players"]["p1"]["cash"]
        self.do("sell_shares", corporation="C&O", percent=10)
        self.assertEqual(self.s["players"]["p1"]["cash"], before + 100)
        self.assertEqual(e._price(self.s["corporations"]["C&O"]), 90)
        with self.assertRaises(RuleError):
            self.do("buy_shares", corporation="C&O")
        self.do("buy_shares", corporation="PRR", price=67)

    def test_consecutive_passes_end_round_without_seat_cycle_requirement(self):
        self.operating()
        self.do("dividend", payout=False)
        self.do("end_turn")
        # A deal resets the consecutive-pass count.
        self.do("pass")
        self.do("buy_shares", corporation="PRR", price=67)
        last = self.s["current_player"]
        self.do("end_turn")
        for _ in range(3):
            self.do("pass")
        self.assertEqual(self.s["round"], "operating")
        self.assertEqual(self.s["priority"], e._next_player(self.s, last))

    def test_presidency_wraparound_and_equal_holdings(self):
        c = self.give_stock("PRR", "p3", 30)
        self.give_stock("PRR", "p1", 30)
        self.give_stock("PRR", "p2", 30)
        self.assertEqual(c["president"], "p3")
        c["holdings"]["p3"] -= 10
        c["pool"] += 10
        e._check_president(self.s, c)
        self.assertEqual(c["president"], "p1")
        validate_state(self.s)

    def test_dividends_pool_not_ipo_and_fixed_par(self):
        self.operating()
        c = self.s["corporations"]["C&O"]
        c["pool"] = 20
        c["ipo"] -= 20
        self.s["operating_turn"]["routes"] = []
        self.s["operating_turn"]["revenue"] = 100
        before = {p: x["cash"] for p, x in self.s["players"].items()}
        self.do("dividend", payout=True)
        c = self.s["corporations"]["C&O"]
        self.assertEqual(c["cash"], 1020)
        for p, n in c["holdings"].items():
            self.assertEqual(self.s["players"][p]["cash"], before[p] + n)
        self.assertEqual(c["par"], 100)
        self.assertEqual(e._price(c), 112)

    def test_train_depot_order_phase_rust_and_discard(self):
        self.operating()
        self.do("dividend", payout=False)
        with self.assertRaises(RuleError):
            self.do("buy_train", train="3-0")
        for train in self.s["trains"].values():
            if train["type"] == "2":
                train["owner"] = None
                train["rusted"] = True
        self.do("buy_train", train="3-0")
        self.assertEqual(self.s["phase"], "3")
        self.assertEqual(self.s["or_total"], 1)
        self.assertEqual(self.s["or_number"], 1)

    def test_route_real_hex_edges_city_revenues_and_token_each(self):
        # F6 edge 5 connects G7 edge 2; tile 58 rotation 2 connects edges 2 and 4.
        c = self.s["corporations"]["C&O"]
        self.fund("C&O", 500)
        b.place_token(self.s, "C&O", "F6", home=True)
        b.lay_tile(self.s, "C&O", "G7", "1", 2)
        self.add_train("C&O", "2-0")
        path = ["F6:n0", "F6:e5", "G7:e2", "G7:n1"]
        # Tile 1 at rotation 2 has e2 -> node1 and e3 -> node0.
        route = {"train": "2-0", "vertices": path}
        self.assertEqual(b.validate_routes(self.s, "C&O", [route]), 40)
        with self.assertRaises(RuleError):
            b.validate_routes(self.s, "C&O", [route, route])
        self.assertTrue(b.route_candidates(self.s, "C&O", "2-0", limit=1))

    def test_bank_break_deferred_and_scores_exclude_treasury(self):
        self.operating()
        e._pay(self.s, "bank", "p1", self.s["bank"] + 10)
        self.assertTrue(self.s["end_after_set"])
        self.assertFalse(self.s["finished"])
        self.do("dividend", payout=False)
        self.do("end_turn")
        self.assertTrue(self.s["finished"])
        self.assertEqual(self.s["end_reason"], "bank")
        self.assertEqual(self.s["result"], scores(self.s))
        with self.assertRaises(RuleError):
            self.do("pass")


def CounterTypes(state):
    return {
        t: sum(x["type"] == t for x in state["trains"].values()) for t in TRAIN_TYPES
    }
