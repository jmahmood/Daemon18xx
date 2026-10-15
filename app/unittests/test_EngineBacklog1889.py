"""Rule and interaction regressions closing BACKLOG-01/02 and 12–24."""

import json
import unittest
from copy import deepcopy

from app import engine1830, engine1889
from app.engine1830 import engine as e1830
from app.engine1889 import engine as E
from app.unittests import test_Engine1830 as f1830, test_Engine1889 as f1889
from app.unittests.test_EngineReviewEdges import public_emergency_state


class Backlog1889Tests(unittest.TestCase):
    def fixture(self, operating=True):
        f = f1889.Rules1889Tests("runTest")
        f.setUp()
        (f.operating if operating else f.stock)()
        return f

    def test_emergency_sale_commits_to_depot_even_if_corporate_price_is_affordable(
        self,
    ):
        for seller_player in ("p1", "p2"):
            f = self.fixture()
            f.route()
            f.train_step()
            f.cash(f.s["corporations"]["IR"], 50)
            f.cash(f.s["players"]["p1"], 0)
            f.shares("AR", "p1", 30)
            f.shares("SR", seller_player, 20)
            f.give_train("SR", "2-1")
            if seller_player != "p1":
                f.act(
                    "offer",
                    player=seller_player,
                    kind="train",
                    item="2-1",
                    seller="SR",
                    buyer="IR",
                    price=1,
                )
            before = deepcopy(f.s)
            # An ordinary affordable transfer is still legal before emergency sales.
            normal = engine1889.apply_action(
                before, dict(type="buy_train", player="p1", train="2-1", price=1)
            )
            self.assertIn("2-1", normal["corporations"]["IR"]["trains"])
            f.act("emergency_sell", corporation="AR", percent=10)
            f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
            offers = deepcopy(f.s["offers"])
            f.reject("buy_train", train="2-1", price=1)
            self.assertEqual(f.s["offers"], offers)
            f.act("buy_train", train="2-0")
            self.assertEqual(f.s["corporations"]["IR"]["cash"], 0)
            self.assertEqual(f.s["players"]["p1"]["cash"], 70)

    def test_bankruptcy_liquidation_is_independent_of_dictionary_order_in_both_games(
        self,
    ):
        for module, engine, fixture, cid, others in (
            (engine1889, E, f1889.Rules1889Tests, "IR", ("AR", "SR")),
            (engine1830, e1830, f1830.Rules1830Tests, "B&O", ("NYC", "CPR")),
        ):
            f = fixture("runTest")
            f.setUp()
            f.operating()
            if module is engine1889:
                f.route()
                f.train_step()
            else:
                f.washington()
                f.to_train()
            pid = f.s["current_player"]
            f.cash(f.s["corporations"][cid], 0)
            for player in f.s["players"].values():
                f.cash(player, 0)
            # Make all priced shares too cheap to meet the mandatory train cost.
            for corp in f.s["corporations"].values():
                if corp["par"]:
                    engine._position(
                        f.s,
                        corp,
                        min(
                            (cell["price"], [r, c])
                            for r, row in enumerate(engine.MARKET)
                            for c, cell in enumerate(row)
                            if cell
                        )[1],
                    )
            for other in others:
                f.shares(other, pid, 30)
                engine._position(
                    f.s,
                    f.s["corporations"][other],
                    [9, 0] if module is engine1889 else [6, 0],
                )
            a = deepcopy(f.s)
            b = deepcopy(f.s)
            b["corporations"] = dict(reversed(list(b["corporations"].items())))
            action = dict(type="bankrupt", player=pid)
            first = module.apply_action(a, action)
            second = module.apply_action(b, action)
            self.assertEqual(first, second)
            self.assertEqual(
                module.migrate_state(json.loads(json.dumps(first, sort_keys=True))),
                first,
            )
            self.assertTrue(first["finished"])

    def test_dougo_last_ipo_share_and_no_pool_fallback(self):
        for remaining in (0, 10):
            f = self.fixture(False)
            f.shares("IR", "p1", 30)
            f.shares("IR", "p2", 30)
            f.shares("IR", "p3", 30)
            if remaining == 0:
                c = f.s["corporations"]["IR"]
                c.update(ipo=0, pool=10)
            f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
            if remaining:
                self.assertIn(
                    "exchange_private", engine1889.legal_actions(f.s, "p2")["types"]
                )
                f.act("exchange_private", player="p2")
                self.assertEqual(f.s["corporations"]["IR"]["ipo"], 0)
                self.assertEqual(f.s["corporations"]["IR"]["holdings"]["p2"], 40)
                self.assertEqual(f.s["corporations"]["IR"]["president"], "p2")
                self.assertTrue(f.s["privates"]["DR"]["closed"])
            else:
                f.reject("exchange_private", player="p2")
            self.assertNotIn(
                "exchange_private", engine1889.legal_actions(f.s, "p2")["types"]
            )

    def test_dougo_before_par_retains_share_and_funds_once_at_flotation(self):
        f = self.fixture(False)
        f.act("exchange_private", player="p2")
        c = f.s["corporations"]["IR"]
        self.assertIsNone(c["par"])
        self.assertFalse(c["funded"])
        self.assertFalse(c["home_placed"])
        f.act("buy_shares", corporation="IR", price=100)
        f.act("end_turn")
        f.act("buy_shares", corporation="IR")
        f.act("end_turn")
        f.act("buy_shares", corporation="IR")
        self.assertEqual(f.s["corporations"]["IR"]["holdings"]["p2"], 20)
        self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)
        self.assertEqual(f.s["corporations"]["IR"]["ipo"], 50)
        self.assertEqual(
            engine1889.replay(["Player 0", "Player 1", "Player 2"], f.s["history"]), f.s
        )

    def test_dougo_unpaid_claim_transfers_actor_and_pays_current_holdings(self):
        for payout in (False, True):
            f = self.fixture()
            f.route()
            f.give_train("IR", "2-0")
            f.s["corporations"]["IR"]["holdings"].update(p1=20, p2=20, p3=10)
            f.act("run_best_routes")
            claim = deepcopy(f.s["operating_turn"])
            f.act("exchange_private", player="p2")
            f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
            self.assertEqual(f.s["operating_turn"], claim)
            f.reject("dividend", player="p1", payout=payout)
            cash = {p: v["cash"] for p, v in f.s["players"].items()}
            treasury = f.s["corporations"]["IR"]["cash"]
            f.act("dividend", payout=payout)
            self.assertEqual(
                {p: v["cash"] - cash[p] for p, v in f.s["players"].items()},
                dict(p1=10, p2=15, p3=5) if payout else dict(p1=0, p2=0, p3=0),
            )
            self.assertEqual(
                f.s["corporations"]["IR"]["cash"], treasury + (0 if payout else 50)
            )
            f.reject("dividend", payout=payout)

    def test_dougo_flotation_joins_next_operation_in_same_set_and_bank_end_waits(self):
        for break_bank in (False, True):
            f = self.fixture(False)
            f.s["phase"] = "3"
            f.shares("TR", "p1", 50)
            f.shares("IR", "p1", 30)
            f.shares("IR", "p3", 10)
            f.s.update(or_number=1, or_total=2)
            E._start_operating(f.s)
            if break_bank:
                f.cash(
                    f.s["players"]["p3"],
                    f.s["players"]["p3"]["cash"] + f.s["bank"] - 900,
                )
            f.act("exchange_private", player="p2")
            self.assertEqual(f.s["or_order"], ["TR"])
            f.act("dividend", payout=False)
            f.act("end_turn")
            self.assertEqual((f.s["round"], f.s["or_number"]), ("operating", 2))
            self.assertIn("IR", f.s["or_order"])
            self.assertTrue(f.s["corporations"]["IR"]["home_placed"])
            self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)
            while f.s["round"] == "operating":
                f.act("dividend", payout=False)
                f.act("end_turn")
            self.assertEqual(f.s["finished"], break_bank)
        f = self.fixture()
        E._phase_change(f.s, "5")
        f.reject("exchange_private", player="p2")

    def test_port_during_competitive_auction_keeps_bidding_and_escrow_intact(self):
        for outsider in (False, True):
            f = f1889.Rules1889Tests("runTest")
            f.setUp()
            f.s = engine1889.new_game(list("ABCD") if outsider else list("ABC"))
            f.act("bid", company="ER", price=45)
            f.act("bid", company="ER", price=50)
            f.act("buy_private", company="TR")
            f.act("buy_private", company="MF")
            owner = f.s["privates"]["MF"]["owner"]
            self.assertEqual(owner != f.s["current_player"], outsider)
            before = deepcopy(f.s)
            f.act("lay_tile", player=owner, special="MF", hex="G10", tile="437")
            for key in ("auction", "players", "current_player", "priority"):
                self.assertEqual(f.s[key], before[key])
            f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
            f.act("pass")
            self.assertEqual(f.s["privates"]["ER"]["owner"], "p2")

    def test_ehime_with_exhausted_green_supply_can_pass_and_resume(self):
        f = self.fixture()
        f.s["phase"] = "3"
        homes = {c["home"] for c in f.s["corporations"].values()}
        spare = iter(
            c for c, t in f.s["board"].items() if not t["nodes"] and c not in homes
        )
        # Component-exhaustion fixture; not a historical sequence of track lays.
        for tid in ("12", "13", "14", "15", "205", "206"):
            while f.s["tiles"][tid]:
                f.s["board"][next(spare)] = E.topology.tile_for(tid, 0)
                f.s["tiles"][tid] -= 1
        engine1889.validate_state(f.s)
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
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        f.reject("lay_tile", hex="C4", tile="14", rotation=1)
        f.act("pass")
        self.assertEqual(f.s["current_player"], "p1")
        self.assertTrue(f.s["privates"]["ER"]["used"])
        self.assertFalse(f.s["operating_turn"]["laid"])
        f.route()

    def test_emergency_maximum_ownership_correction_and_orange_control(self):
        for orange in (False, True):
            f = self.fixture()
            f.route()
            f.train_step()
            f.cash(f.s["corporations"]["IR"], 0)
            f.cash(f.s["players"]["p1"], 0)
            f.shares("AR", "p1", 100)
            if orange:
                E._position(f.s, f.s["corporations"]["AR"], [9, 1])
            f.reject("bankrupt")
            if not orange:
                for amount in (10, 20, 30, 50):
                    f.reject("emergency_sell", corporation="AR", percent=amount)
                self.assertGreaterEqual(E._maximum_emergency_sale(f.s, "p1", "AR"), 40)
            f.act("emergency_sell", corporation="AR", percent=30 if orange else 40)
            self.assertEqual(
                f.s["corporations"]["AR"]["holdings"]["p1"], 70 if orange else 60
            )
            f.act("buy_train", train="2-0")

    def test_foreign_route_query_does_not_inherit_active_new_train_exclusion(self):
        f = self.fixture()
        f.route()
        f.s["phase"] = "3"
        E.topology.lay_tile(f.s, "IR", "E2", "15", 4)
        f.shares("AR", "p2", 50)
        f.cash(f.s["corporations"]["AR"], 1000)
        E.topology.place_token(f.s, "AR", "K8", home=True)
        E.topology.place_token(f.s, "AR", "E2", teleport=True)
        f.give_train("IR", "2-0")
        f.give_train("AR", "2-1")
        f.s["operating_turn"]["new_trains"] = ["2-0"]
        before = deepcopy(f.s)
        self.assertEqual(engine1889.best_routes(f.s, "IR")["revenue"], 0)
        result = engine1889.best_routes(f.s, "AR")
        self.assertEqual(result["revenue"], 60)
        result["routes"].clear()
        self.assertEqual(engine1889.best_routes(f.s, "AR")["revenue"], 60)
        self.assertEqual(f.s, before)

    def test_bankruptcy_takes_precedence_over_previously_broken_bank(self):
        state = public_emergency_state()
        other = next(p for p in state["players"] if p != state["current_player"])
        E._pay(state, "bank", other, state["bank"])
        state = engine1889.migrate_state(json.loads(json.dumps(state)))
        self.assertTrue(state["end_after_set"])
        result = engine1889.apply_action(
            state, dict(type="bankrupt", player=state["current_player"])
        )
        self.assertTrue(result["finished"])
        self.assertEqual(result["end_reason"], "bankruptcy")
        self.assertEqual(result["or_number"], state["or_number"])
        self.assertEqual(result["result"], engine1889.scores(result))

    def test_stock_exchange_resets_passes_and_priority_but_port_does_not(self):
        for own_turn in (False, True):
            f = self.fixture(False)
            f.act("pass")
            if not own_turn:
                f.act("pass")
            active = f.s["current_player"]
            turn = deepcopy(f.s["stock_turn"])
            f.act("exchange_private", player="p2")
            self.assertEqual(f.s["stock_passes"], 0)
            self.assertEqual(f.s["last_deal"], "p2")
            if not own_turn:
                self.assertEqual(f.s["stock_turn"], turn)
            self.assertEqual(f.s["current_player"], active)
            if own_turn:
                f.act("end_turn")
            for _ in range(3):
                f.act("pass")
            self.assertEqual(f.s["priority"], "p3")
        f = self.fixture(False)
        f.act("pass")
        f.act("pass")
        before = deepcopy(f.s)
        f.act("lay_tile", player="p2", special="MF", hex="G10", tile="437")
        for key in (
            "stock_passes",
            "last_deal",
            "stock_turn",
            "current_player",
            "priority",
        ):
            self.assertEqual(f.s[key], before[key])
        f.act("pass")
        self.assertEqual(f.s["stock_round"], before["stock_round"] + 1)
