"""Cross-step regressions for the standard 1889 uploaded-rulebook audit."""

import json
import unittest
from copy import deepcopy
from itertools import combinations, product

from app import engine1889
from app.engine1889 import engine as E
from app.unittests import test_Engine1889 as fixtures


class OperatingInteractionTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.s["phase"] = "3"
        f.give_train("IR", "2-0")
        return f

    def buy_ehime(self, f):
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
        f.reject("lay_tile", hex="C4", tile="57", rotation=1)
        f.act("lay_tile", hex="C4", tile="14", rotation=1)

    def test_ehime_revalues_unpaid_routes_but_never_changes_paid_dividends(self):
        for payout, already_paid in product((False, True), repeat=2):
            with self.subTest(payout=payout, already_paid=already_paid):
                f = self.fixture()
                E.topology.place_token(f.s, "IR", "C4", teleport=True)
                f.act("run_best_routes")
                self.assertEqual(f.s["operating_turn"]["revenue"], 40)
                if already_paid:
                    f.act("dividend", payout=payout)
                self.buy_ehime(f)
                cash = f.s["corporations"]["IR"]["cash"]
                player_cash = f.s["players"]["p1"]["cash"]
                if already_paid:
                    self.assertEqual(f.s["operating_turn"]["revenue"], 40)
                    f.reject("dividend", payout=payout)
                    f.reject("run_best_routes")
                else:
                    f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
                    f.act("dividend", payout=payout)
                    self.assertEqual(f.s["operating_turn"]["revenue"], 50)
                    self.assertEqual(
                        f.s["corporations"]["IR"]["cash"], cash + (0 if payout else 50)
                    )
                    self.assertEqual(
                        f.s["players"]["p1"]["cash"],
                        player_cash + (25 if payout else 0),
                    )

    def test_port_after_empty_route_claim_requires_newly_available_train_to_run(self):
        for empty_claim in ("run_routes", "skip"):
            with self.subTest(empty_claim=empty_claim):
                f = self.fixture()
                corp = f.s["corporations"]["IR"]
                corp["holdings"].update(p1=0, p2=50)
                corp["president"] = f.s["current_player"] = "p2"
                E.topology.place_token(f.s, "IR", "F9", teleport=True)
                self.assertEqual(engine1889.best_routes(f.s)["routes"], [])
                if empty_claim == "skip":
                    f.act("skip")
                    f.act("skip")
                    f.act("skip")
                else:
                    f.act("run_routes", routes=[])
                f.act("lay_tile", special="MF", hex="G10", tile="437", rotation=0)
                f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
                f.reject("dividend", payout=False)
                f.reject("dividend", payout=True)
                f.act("run_best_routes")
                self.assertEqual(f.s["operating_turn"]["revenue"], 60)
                cash = f.s["corporations"]["IR"]["cash"]
                f.act("dividend", payout=False)
                self.assertEqual(f.s["corporations"]["IR"]["cash"], cash + 60)

    def test_invalid_route_corrections_keep_the_previous_claim_and_revision(self):
        f = self.fixture()
        f.route()
        f.act("run_best_routes")
        routes = deepcopy(f.s["operating_turn"]["routes"])
        for invalid in (
            [],
            routes + routes,
            [dict(routes[0], train="2-1")],
            [
                dict(
                    routes[0],
                    vertices=list(reversed(routes[0]["vertices"])) + ["E2:n0"],
                )
            ],
            [None],
            [dict(train="2-0", paths=[["E2", 999]])],
        ):
            with self.subTest(routes=invalid):
                f.reject("run_routes", routes=invalid)
                self.assertEqual(f.s["operating_turn"]["revenue"], 50)
                self.assertEqual(f.s["operating_turn"]["routes"], routes)
        f.act(
            "run_routes",
            routes=[dict(routes[0], vertices=list(reversed(routes[0]["vertices"])))],
        )
        f.act("dividend", payout=False)

    def test_port_after_paid_zero_revenue_preserves_lock_and_new_train_obligation(self):
        for owns_train in (False, True):
            with self.subTest(owns_train=owns_train):
                f = self.fixture()
                corp = f.s["corporations"]["IR"]
                corp["holdings"].update(p1=0, p2=50)
                corp["president"] = f.s["current_player"] = "p2"
                if not owns_train:
                    corp["trains"].remove("2-0")
                    f.s["trains"]["2-0"]["owner"] = "depot"
                E.topology.place_token(f.s, "IR", "F9", teleport=True)
                f.act("dividend", payout=False)
                f.act("lay_tile", special="MF", hex="G10", tile="437", rotation=0)
                f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
                self.assertEqual(f.s["operating_turn"]["revenue"], 0)
                f.reject("run_best_routes")
                f.reject("dividend", payout=True)
                if not owns_train:
                    f.reject("end_turn")
                    f.act("buy_train", train="2-0")
                    self.assertEqual(f.s["operating_turn"]["new_trains"], ["2-0"])
                f.act("end_turn")
                self.assertEqual(f.s["round"], "stock")

    def test_dougo_flotation_during_operation_funds_once_and_waits_for_next_round(self):
        for break_bank in (False, True):
            with self.subTest(break_bank=break_bank):
                f = fixtures.Rules1889Tests("runTest")
                f.setUp()
                f.stock()
                f.shares("TR", "p1", 50)
                f.shares("IR", "p1", 30)
                f.shares("IR", "p3", 10)
                f.s["or_number"] = 1
                E._start_operating(f.s)
                if break_bank:
                    f.cash(
                        f.s["players"]["p3"],
                        f.s["players"]["p3"]["cash"] + f.s["bank"] - 900,
                    )
                turn = deepcopy(f.s["operating_turn"])
                f.act("exchange_private", player="p2")
                self.assertEqual(f.s["current_corporation"], "TR")
                self.assertEqual(f.s["current_player"], "p1")
                self.assertEqual(f.s["operating_turn"], turn)
                self.assertEqual(f.s["or_order"], ["TR"])
                self.assertTrue(f.s["corporations"]["IR"]["funded"])
                self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)
                self.assertFalse(f.s["corporations"]["IR"]["home_placed"])
                f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
                f.act("dividend", payout=False)
                f.act("end_turn")
                if break_bank:
                    self.assertTrue(f.s["finished"])
                    self.assertEqual(f.s["end_reason"], "bank")
                else:
                    self.assertEqual(f.s["round"], "stock")
                    for _ in range(3):
                        f.act("pass")
                    self.assertIn("IR", f.s["or_order"])
                    self.assertTrue(f.s["corporations"]["IR"]["home_placed"])
                    self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)


class RouteAllocationOracleTests(unittest.TestCase):
    def star(self, values, leaf_station=False, blocked=False, grouped=False):
        """Four independent branches; the oracle uses branch IDs, not graph search."""
        state = engine1889.new_game(["A", "B", "C"])
        state["phase"] = "D"
        center = E.topology.decode("city=revenue:20,slots:1", "yellow")
        center["tile"] = None
        center["tokens"][0] = ["AR"] if blocked else ([] if leaf_station else ["IR"])
        state["board"]["E4"] = center
        leaves = ("E6", "D3", "E2", "F5")
        for i, (coord, edge, value) in enumerate(zip(leaves, (0, 2, 3, 5), values)):
            code = (
                "offboard=revenue:yellow_%d|brown_%d|diesel_%d,groups:X"
                % (value, value, value * 2)
                if grouped and i < 2
                else "city=revenue:%d" % value
            )
            leaf = E.topology.decode(
                code + ";path=a:%d,b:_0" % ((edge + 3) % 6), "yellow"
            )
            leaf["tile"] = None
            leaf["tokens"][0] = ["IR"] if leaf_station and i == 2 else []
            state["board"][coord] = leaf
            center["paths"].append(["n0", "e%d" % edge])
        return state

    def oracle(self, values, trains, leaf_station, blocked, grouped):
        # Every legal route is either one spoke or two spokes through the hub.
        # Compute revenues and allocate disjoint *branch numbers* independently
        # of route_candidates, validate_routes and the engine's bitmask search.
        choices = []
        for kind in trains:
            routes = [(frozenset(), 0)]
            for size in (1, 2):
                if size + 1 > (999 if kind == "D" else int(kind)):
                    continue
                for arms in combinations(range(4), size):
                    if leaf_station and 2 not in arms:
                        continue
                    if size == 2 and (blocked or (grouped and 0 in arms and 1 in arms)):
                        continue
                    revenue = 20 + sum(
                        values[i] * (2 if kind == "D" and grouped and i < 2 else 1)
                        for i in arms
                    )
                    routes.append((frozenset(arms), revenue))
            choices.append(routes)
        return max(
            sum(value for _, value in allocation)
            for allocation in product(*choices)
            if sum(len(arms) for arms, _ in allocation)
            == len(set().union(*(arms for arms, _ in allocation)))
        )

    def test_allocator_matches_independent_oracle_across_weighted_network_family(self):
        # 320 combinations of train mix, offboard groups, blocking, railhead
        # and stop values, including zero-valued destinations and equal maxima.
        mixes = (("2", "2"), ("2", "3"), ("3", "3"), ("2", "3", "D"))
        for values, trains, scenario in product(
            product((0, 50), repeat=4),
            mixes,
            (
                (False, False, False),
                (False, False, True),
                (True, False, True),
                (True, True, False),
                (True, True, True),
            ),
        ):
            leaf_station, blocked, grouped = scenario
            with self.subTest(values=values, trains=trains, scenario=scenario):
                state = self.star(values, *scenario)
                for kind in trains:
                    tid = next(
                        tid
                        for tid, train in state["trains"].items()
                        if train["type"] == kind and train["owner"] == "depot"
                    )
                    state["trains"][tid]["owner"] = "IR"
                    state["corporations"]["IR"]["trains"].append(tid)
                original = deepcopy(state)
                expected = self.oracle(values, trains, leaf_station, blocked, grouped)
                result = engine1889.best_routes(state, "IR")
                self.assertEqual(result["revenue"], expected)
                self.assertEqual(state, original)
                self.assertEqual(
                    E.topology.validate_routes(state, "IR", result["routes"]), expected
                )

    def test_exact_allocator_is_not_limited_to_first_hundred_suggestions(self):
        # Eight fully connected revenue nodes have >100 simple candidate routes.
        # This small synthetic graph isolates enumeration from tile placement.
        state = engine1889.new_game(["A", "B", "C"])
        state["board"] = {
            "E2": E.topology.decode(
                ";".join(
                    ["city=revenue:%d" % value for value in (1, 2, 3, 4, 5, 6, 7, 1000)]
                    + ["path=a:_%d,b:_%d" % pair for pair in combinations(range(8), 2)]
                ),
                "yellow",
            )
        }
        state["board"]["E2"]["tokens"][0] = ["IR"]
        state["corporations"]["IR"]["trains"] = ["4-0"]
        state["trains"]["4-0"]["owner"] = "IR"
        bounded = E.topology.route_candidates(state, "IR", "4-0")
        self.assertEqual(len(bounded), 100)
        self.assertLess(
            max(E.topology.validate_routes(state, "IR", [r]) for r in bounded), 1014
        )
        self.assertGreater(
            len(E.topology.route_candidates(state, "IR", "4-0", limit=None)), 100
        )
        self.assertEqual(engine1889.best_routes(state, "IR")["revenue"], 1014)


class OperatingInteractionHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.unittests import test_Engine1830API as api

        self.h = api.Rules1830APITests("runTest")
        await self.h.asyncSetUp()

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def seed(self, state):
        status, self.info = await self.h.request(
            "POST", "/api/1889/games", {"max_players": 3}
        )
        self.assertEqual(status, 200)
        self.path = "/api/1889/games/" + self.info["room_code"]
        status, _ = await self.h.request(
            "POST",
            self.path + "/start",
            {"player_names": ["A", "B", "C"]},
            self.info["creator_token"],
        )
        self.assertEqual(status, 200)
        game = await self.h.db.get_game_by_room_code(self.info["room_code"])
        await self.h.db.save_rules_state(game["id"], state, 0)
        self.state = deepcopy(state)

    async def submit(self, player, action_type, status=200, **fields):
        action = dict(
            type=action_type,
            player=player,
            expected_action_id=self.state["revision"],
            **fields,
        )
        expected = (
            engine1889.apply_action(self.state, action) if status == 200 else self.state
        )
        actual_status, response = await self.h.request(
            "POST",
            self.path + "/actions",
            dict(expected_action_id=self.state["revision"], action=action),
            self.info["player_tokens"][int(player[1:]) - 1],
        )
        self.assertEqual(actual_status, status, response)
        actual_status, restored = await self.h.request(
            "GET", self.path, token=self.info["spectator_token"]
        )
        self.assertEqual(actual_status, 200)
        self.assertEqual(restored["state"], expected)
        self.state = expected

    async def test_ehime_interrupt_and_revalued_payment_persist_with_stale_retry_rejected(
        self,
    ):
        f = OperatingInteractionTests("runTest").fixture()
        E.topology.place_token(f.s, "IR", "C4", teleport=True)
        f.act("run_best_routes")
        await self.seed(f.s)
        await self.submit(
            "p3", "offer", kind="private", item="ER", seller="p3", buyer="IR", price=40
        )
        await self.submit("p1", "buy_private", company="ER", buyer="IR", price=40)
        await self.submit("p1", "dividend", status=422, payout=True)
        await self.submit("p3", "lay_tile", hex="C4", tile="14", rotation=1)
        previous_revision = self.state["revision"]
        cash = self.state["players"]["p1"]["cash"]
        await self.submit("p1", "dividend", payout=True)
        self.assertEqual(self.state["operating_turn"]["revenue"], 50)
        self.assertEqual(self.state["players"]["p1"]["cash"], cash + 25)
        status, _ = await self.h.request(
            "POST",
            self.path + "/actions",
            dict(
                expected_action_id=previous_revision,
                action=dict(type="dividend", payout=True),
            ),
            self.info["player_tokens"][0],
        )
        self.assertEqual(status, 409)
        await self.submit("p1", "run_best_routes", status=422)

    async def test_port_invalidates_empty_claim_without_persisting_rejected_payment(
        self,
    ):
        f = OperatingInteractionTests("runTest").fixture()
        corp = f.s["corporations"]["IR"]
        corp["holdings"].update(p1=0, p2=50)
        corp["president"] = f.s["current_player"] = "p2"
        E.topology.place_token(f.s, "IR", "F9", teleport=True)
        f.act("run_routes", routes=[])
        await self.seed(f.s)
        await self.submit(
            "p2", "lay_tile", special="MF", hex="G10", tile="437", rotation=0
        )
        await self.submit("p2", "dividend", status=422, payout=False)
        await self.submit("p2", "run_best_routes")
        self.assertEqual(self.state["operating_turn"]["revenue"], 60)
        cash = self.state["corporations"]["IR"]["cash"]
        await self.submit("p2", "dividend", payout=False)
        self.assertEqual(self.state["corporations"]["IR"]["cash"], cash + 60)


if __name__ == "__main__":
    unittest.main()
