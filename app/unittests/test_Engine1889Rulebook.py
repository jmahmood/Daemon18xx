"""Regressions derived from the uploaded Japanese 1889 rules, cited by section."""

import json
import unittest
from copy import deepcopy

from app import engine1889
from app.engine1889 import engine as E
from app.unittests import test_Engine1889 as fixtures


class UploadedRulebookTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Rules1889Tests("runTest")
        self.f.setUp()

    def stock_at_forty_percent(self):
        f = self.f
        f.stock()
        f.act("buy_shares", corporation="IR", price=100)
        f.act("end_turn")
        f.act("buy_shares", corporation="IR")
        f.act("end_turn")
        f.act("buy_shares", corporation="IR")
        f.act("end_turn")
        self.assertEqual(f.s["corporations"]["IR"]["ipo"], 60)
        self.assertFalse(f.s["corporations"]["IR"]["funded"])
        return f

    def test_5_6_4_capital_paid_at_fifth_share_and_never_repeated(self):
        f = self.stock_at_forty_percent()
        bank = f.s["bank"]
        f.act("buy_shares", corporation="IR")
        self.assertEqual(f.s["round"], "stock")
        self.assertEqual(f.s["bank"], bank + 100 - 1000)
        self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)
        self.assertTrue(f.s["corporations"]["IR"]["funded"])
        self.assertFalse(f.s["corporations"]["IR"]["home_placed"])
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        E._start_operating(f.s)
        self.assertEqual(f.s["corporations"]["IR"]["cash"], 1000)
        self.assertTrue(f.s["corporations"]["IR"]["home_placed"])
        engine1889.validate_state(f.s)

    def test_12_2_flotation_can_break_bank_before_stock_round_ends(self):
        f = self.stock_at_forty_percent()
        f.cash(f.s["players"]["p3"], f.s["players"]["p3"]["cash"] + f.s["bank"] - 850)
        f.act("buy_shares", corporation="IR")
        self.assertEqual(f.s["bank"], -50)
        self.assertTrue(f.s["bank_broken"])
        self.assertTrue(f.s["end_after_set"])
        self.assertFalse(f.s["finished"])
        self.assertEqual(f.s["round"], "stock")

    def test_5_7_competitive_auction_uses_clockwise_order_after_high_bidder(self):
        f = self.f
        f.s = engine1889.new_game(list("ABCD"))
        for kind, fields in (
            ("bid", dict(company="ER", price=45)),
            ("pass", {}),
            ("bid", dict(company="ER", price=50)),
            ("pass", {}),
            ("pass", {}),
            ("bid", dict(company="ER", price=55)),
            ("buy_private", dict(company="TR")),
            ("buy_private", dict(company="MF")),
        ):
            f.act(kind, **fields)
        # p2 has the highest bid; p3 is clockwise-next, although p1 bid less.
        self.assertEqual(f.s["current_player"], "p3")
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        f.act("pass")
        self.assertEqual(f.s["current_player"], "p1")
        f.reject("pass", player="p2")
        f.act("bid", company="ER", price=60)
        self.assertEqual(f.s["current_player"], "p2")
        f.act("pass")
        self.assertEqual(f.s["privates"]["ER"]["owner"], "p1")
        self.assertEqual(f.s["players"]["p1"]["cash"], 360)
        self.assertEqual(f.s["players"]["p2"]["cash"], 420)
        self.assertEqual(f.s["players"]["p3"]["cash"], 400)
        self.assertEqual(f.s["current_player"], "p1")

    def emergency(self, orange=False):
        f = self.f
        f.operating()
        f.route()
        f.train_step()
        f.cash(f.s["corporations"]["IR"], 0)
        f.cash(f.s["players"]["p1"], 0)
        f.shares("AR", "p1", 80)
        if orange:
            E._position(f.s, f.s["corporations"]["AR"], [10, 1])
        return f

    def test_5_7_last_private_winner_determines_first_public_stock_actor(self):
        f = self.f
        f.act("bid", company="SIR", price=85)
        for company in ("TR", "MF", "ER", "SMR", "DR"):
            f.act("buy_private", company=company)
        self.assertEqual(f.s["privates"]["SIR"]["owner"], "p1")
        self.assertEqual(f.s["round"], "stock")
        self.assertEqual(f.s["current_player"], "p2")
        self.assertEqual(f.s["priority"], "p2")
        f.reject("buy_shares", player="p1", corporation="IR", price=100)
        f.act("buy_shares", corporation="IR", price=100)

    def test_5_7_auction_order_and_last_winner_survive_reordered_json(self):
        f = self.f
        f.act("bid", company="SIR", price=85)
        for company in ("TR", "MF", "ER", "SMR", "DR"):
            f.s = engine1889.migrate_state(json.loads(json.dumps(f.s, sort_keys=True)))
            f.act("buy_private", company=company)
        self.assertEqual(f.s["current_player"], "p2")
        self.assertEqual(f.s["priority"], "p2")
        self.assertEqual(
            engine1889.replay(["Alice", "Bob", "Carol"], f.s["history"]), f.s
        )

    def test_5_7_private_only_pass_cycle_updates_priority_before_free_purchase(self):
        f = self.f
        f.act("bid", company="ER", price=45)
        for _ in range(3):
            f.act("pass")
        self.assertEqual(f.s["current_player"], "p2")
        self.assertEqual(f.s["priority"], "p2")
        for _ in range(9):
            f.act("pass")
        self.assertEqual(f.s["privates"]["TR"]["owner"], "p2")
        self.assertEqual(f.s["players"]["p2"]["cash"], 420)

    def test_15_2_mitsubishi_port_can_be_used_during_initial_stock_auction(self):
        f = self.f
        f.act("buy_private", company="TR")
        f.act("buy_private", company="MF")
        self.assertEqual(f.s["current_player"], "p3")
        self.assertIn("lay_tile", engine1889.legal_actions(f.s, "p2")["types"])
        f.act("lay_tile", player="p2", special="MF", hex="G10", tile="437", rotation=0)
        self.assertEqual(f.s["current_player"], "p3")
        self.assertEqual(f.s["round"], "auction")
        self.assertEqual(f.s["board"]["G10"]["tile"], "437")
        self.assertFalse(f.s["privates"]["MF"]["closed"])
        f.reject(
            "lay_tile", player="p2", special="MF", hex="B11", tile="437", rotation=0
        )
        f.act("buy_private", company="ER")

    def test_15_2_mitsubishi_port_is_available_throughout_owners_operating_turn(self):
        for step in ("token", "routes", "dividend", "train"):
            with self.subTest(step=step):
                f = fixtures.Rules1889Tests("runTest")
                f.setUp()
                f.operating()
                f.s["corporations"]["IR"]["holdings"].update(p1=0, p2=50)
                f.s["corporations"]["IR"]["president"] = "p2"
                f.s["current_player"] = "p2"
                f.route()
                if step in ("routes", "dividend", "train"):
                    f.act("skip")
                if step in ("dividend", "train"):
                    f.act("run_routes", routes=[])
                if step == "train":
                    f.act("dividend", payout=False)
                turn = deepcopy(f.s["operating_turn"])
                f.reject("lay_tile", player="p1", special="MF", hex="G10", tile="437")
                self.assertIn(
                    "port_hexes", engine1889.legal_actions(f.s, "p2")["choices"]
                )
                f.act("lay_tile", player="p2", special="MF", hex="G10", tile="437")
                self.assertEqual(f.s["operating_turn"], turn)
                self.assertEqual(f.s["current_player"], "p2")

    def test_15_2_dougo_exchange_during_another_players_started_stock_turn(self):
        f = self.f
        f.stock()
        f.act("buy_shares", corporation="IR", price=100)
        turn = deepcopy(f.s["stock_turn"])
        f.act("exchange_private", player="p2")
        self.assertEqual(f.s["corporations"]["IR"]["holdings"]["p2"], 10)
        self.assertEqual(f.s["current_player"], "p1")
        self.assertEqual(f.s["stock_turn"], turn)
        f.act("end_turn")
        f.act("buy_shares", corporation="AR", price=65)

    def test_15_2_dougo_mid_operation_can_change_president_and_resumes_same_step(self):
        f = self.f
        f.operating()
        corp = f.s["corporations"]["IR"]
        corp["holdings"].update(p1=20, p2=20, p3=10)
        f.route()
        f.act("dividend", payout=False)
        turn = deepcopy(f.s["operating_turn"])
        f.act("exchange_private", player="p2")
        self.assertEqual(f.s["current_player"], "p2")
        self.assertEqual(f.s["corporations"]["IR"]["president"], "p2")
        self.assertEqual(f.s["operating_turn"], turn)
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        f.reject("buy_train", player="p1", train="2-0")
        f.act("buy_train", player="p2", train="2-0")

    def test_15_2_dougo_exchange_uses_normal_orange_holding_exemption(self):
        f = self.f
        f.stock()
        corp = f.shares("IR", "p2", 70)
        E._float(corp, f.s)
        E._position(f.s, corp, [10, 1])
        cash = f.s["players"]["p2"]["cash"]
        f.act("exchange_private", player="p2")
        self.assertEqual(f.s["corporations"]["IR"]["holdings"]["p2"], 80)
        self.assertTrue(f.s["privates"]["DR"]["closed"])
        self.assertEqual(f.s["players"]["p2"]["cash"], cash)

    def test_10_6_2_excess_holding_sale_must_correct_to_sixty_even_if_more_than_needed(
        self,
    ):
        f = self.emergency()
        original = deepcopy(f.s)
        f.reject("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(f.s, original)
        f.reject("emergency_sell", corporation="AR", percent=30)
        f.act("emergency_sell", corporation="AR", percent=20)
        self.assertEqual(f.s["corporations"]["AR"]["holdings"]["p1"], 60)
        self.assertEqual(f.s["players"]["p1"]["cash"], 200)
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        f.act("buy_train", train="2-0")
        self.assertEqual(f.s["players"]["p1"]["cash"], 120)

    def test_10_6_2_orange_holdings_need_not_be_corrected_to_sixty(self):
        f = self.emergency(orange=True)
        f.act("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(f.s["corporations"]["AR"]["holdings"]["p1"], 70)
        self.assertEqual(f.s["players"]["p1"]["cash"], 20)

    def test_12_1_bankrupt_player_keeps_value_of_open_privates_and_can_win(self):
        f = self.f
        f.operating()
        f.route()
        f.train_step()
        corp = f.s["corporations"]["IR"]
        corp["holdings"].update(p1=30, p2=30, p3=0)
        corp.update(ipo=40, pool=0)
        f.cash(corp, 0)
        for player in f.s["players"].values():
            f.cash(player, 0)
        for private in f.s["privates"].values():
            if private["owner"] != "p1":
                private["closed"] = True
        f.act("bankrupt")
        self.assertTrue(f.s["players"]["p1"]["bankrupt"])
        self.assertEqual(f.s["result"]["p1"], 340)  # IR 270 + TR 20 + SMR 50.
        self.assertGreater(
            f.s["result"]["p1"], max(f.s["result"][p] for p in ("p2", "p3"))
        )
        self.assertEqual(
            engine1889.scores(engine1889.migrate_state(f.s)), f.s["result"]
        )


class UpgradeRulebookTests(unittest.TestCase):
    def network(self):
        b = E.topology
        state = engine1889.new_game(["A", "B", "C"])
        state["phase"] = "3"
        state["board"] = {coord: b.decode("", "white") for coord in state["board"]}
        source = b.decode("city=revenue:20;path=a:0,b:_0", "yellow")
        source["tokens"][0] = ["IR"]
        state["board"]["E4"] = source
        state["board"]["E6"] = b.tile_for("9", 0)
        state["tiles"]["9"] -= 1
        state["bank"] -= 500
        state["corporations"]["IR"]["cash"] = 500
        return state

    def test_6_2_disjoint_added_track_and_junction_reversal_cannot_justify_upgrade(
        self,
    ):
        for tile, rotation in (("19", 0), ("20", 0), ("23", 0)):
            with self.subTest(tile=tile, rotation=rotation):
                state = self.network()
                before = deepcopy(state)
                with self.assertRaisesRegex(
                    engine1889.RuleError, "new track|city value"
                ):
                    E.topology.lay_tile(state, "IR", "E6", tile, rotation)
                self.assertEqual(state, before)

    def test_6_2_reachable_new_branch_is_a_legal_upgrade(self):
        state = self.network()
        E.topology.lay_tile(state, "IR", "E6", "23", 3)
        self.assertEqual(state["board"]["E6"]["tile"], "23")
        self.assertIn("E6:e1", E.topology.reachable(state["board"], "IR"))
        self.assertEqual(state["tiles"]["9"], E.BOARD_DATA["tiles"]["9"]["count"])

    def test_6_2_reachable_city_value_change_needs_no_new_track(self):
        state = self.network()
        state["phase"] = "5"
        old = E.topology.decode(E.BOARD_DATA["hexes"]["F9"]["code"], "green")
        old["tile"] = None
        state["board"]["E6"] = old
        new = E.topology.tile_for("465", 2)
        self.assertEqual(
            {frozenset(p) for p in old["paths"]}, {frozenset(p) for p in new["paths"]}
        )
        E.topology.lay_tile(state, "IR", "E6", "465", 2)
        self.assertEqual(state["board"]["E6"]["nodes"][0]["revenue"], [60, 60, 60])
        self.assertEqual(state["corporations"]["IR"]["cash"], 420)


class RouteRulebookTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.s["phase"] = "3"
        f.give_train("IR", "3-0")
        f.give_train("IR", "2-0")
        for coord, revenue in (("E2", 10), ("E4", 100), ("E6", 100)):
            tile = E.topology.decode(
                "city=revenue:%d;path=a:0,b:_0;path=a:3,b:_0" % revenue, "yellow"
            )
            tile["tile"] = None
            if coord in ("E2", "E4"):
                tile["tokens"][0] = ["IR"]
            f.s["board"][coord] = tile
        engine1889.validate_state(f.s)
        return f

    def test_8_3_optimal_allocation_can_shorten_best_train_to_improve_total(self):
        f = self.fixture()
        before = deepcopy(f.s)
        result = engine1889.best_routes(f.s)
        self.assertEqual(result["revenue"], 310)
        self.assertEqual(len(result["routes"]), 2)
        self.assertEqual(E.topology.validate_routes(f.s, "IR", result["routes"]), 310)
        self.assertEqual(f.s, before)
        reordered = deepcopy(f.s)
        reordered["board"] = dict(reversed(list(reordered["board"].items())))
        self.assertEqual(reordered, f.s)
        self.assertEqual(engine1889.best_routes(reordered), result)
        result["routes"][0]["vertices"].clear()
        self.assertEqual(engine1889.best_routes(f.s)["revenue"], 310)
        self.assertEqual(f.s, before)

    def test_8_3_identical_trains_and_unused_extra_trains_keep_track_disjoint(self):
        for count in (2, 3, 4):
            with self.subTest(trains=count):
                f = self.fixture()
                f.s["corporations"]["IR"]["trains"].remove("3-0")
                f.s["trains"]["3-0"]["owner"] = "depot"
                for i in range(1, count):
                    f.give_train("IR", "2-" + str(i))
                result = engine1889.best_routes(f.s)
                self.assertEqual(result["revenue"], 310)
                self.assertEqual(len(result["routes"]), 2)
                self.assertEqual(len({r["train"] for r in result["routes"]}), 2)
                self.assertEqual(
                    E.topology.validate_routes(f.s, "IR", result["routes"]), 310
                )

    def test_8_3_route_claims_can_be_corrected_until_dividend_then_are_locked(self):
        f = self.fixture()
        route = dict(
            train="3-0",
            vertices=["E2:n0", "E2:e0", "E4:e3", "E4:n0", "E4:e0", "E6:e3", "E6:n0"],
        )
        f.act("run_routes", routes=[route])
        self.assertEqual(f.s["operating_turn"]["revenue"], 210)
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        money = f.s["bank"], f.s["corporations"]["IR"]["cash"]
        f.act("run_best_routes")
        self.assertEqual(f.s["operating_turn"]["revenue"], 310)
        self.assertEqual((f.s["bank"], f.s["corporations"]["IR"]["cash"]), money)
        f.reject("run_routes", player="p2", routes=[route])
        f.act("dividend", payout=False)
        self.assertEqual(f.s["corporations"]["IR"]["cash"], money[1] + 310)
        f.reject("run_routes", routes=[route])
        f.reject("run_best_routes")

    def test_8_3_optimizer_assigns_shared_offboard_to_diesel(self):
        f = fixtures.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.route()
        f.s["phase"] = "D"
        f.give_train("IR", "6-0")
        f.give_train("IR", "D-0")
        result = engine1889.best_routes(f.s)
        self.assertEqual(result["revenue"], 120)
        self.assertEqual([r["train"] for r in result["routes"]], ["D-0"])

    def test_8_3_no_routes_or_only_newly_bought_trains_produces_zero(self):
        f = fixtures.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        self.assertEqual(engine1889.best_routes(f.s), {"routes": [], "revenue": 0})
        f.route()
        f.give_train("IR", "2-0")
        f.s["operating_turn"]["new_trains"] = ["2-0"]
        self.assertEqual(engine1889.best_routes(f.s), {"routes": [], "revenue": 0})
        for invalid in ("unknown", [], False, ""):
            with self.assertRaises(engine1889.RuleError):
                engine1889.best_routes(f.s, invalid)

    def test_8_3_zero_revenue_still_returns_a_runnable_route(self):
        f = self.fixture()
        for coord in ("E2", "E4", "E6"):
            f.s["board"][coord]["nodes"][0]["revenue"] = [0, 0, 0]
        result = engine1889.best_routes(f.s)
        self.assertEqual(result["revenue"], 0)
        self.assertTrue(result["routes"])
        f.act("run_best_routes")
        f.act("dividend", payout=False)


class UploadedRulebookHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.unittests import test_Engine1830API as api

        self.h = api.Rules1830APITests("runTest")
        await self.h.asyncSetUp()

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def test_5_6_4_flotation_capital_is_persisted_before_operating_and_not_paid_again(
        self,
    ):
        h = self.h
        status, info = await h.request("POST", "/api/1889/games", {"max_players": 3})
        self.assertEqual(status, 200)
        path = "/api/1889/games/" + info["room_code"]
        status, view = await h.request(
            "POST",
            path + "/start",
            {"player_names": ["A", "B", "C"]},
            info["creator_token"],
        )
        self.assertEqual(status, 200)

        async def act(kind, **fields):
            nonlocal view
            state = view["state"]
            token = info["player_tokens"][int(state["current_player"][1:]) - 1]
            status, view = await h.request(
                "POST",
                path + "/actions",
                {
                    "expected_action_id": state["revision"],
                    "action": dict(type=kind, **fields),
                },
                token,
            )
            self.assertEqual(status, 200, view)

        for private in view["state"]["privates"]:
            await act("buy_private", company=private)
        for _ in range(3):
            await act("buy_shares", corporation="IR", price=100)
            await act("end_turn")
        await act("buy_shares", corporation="IR")
        self.assertEqual(view["state"]["round"], "stock")
        self.assertEqual(view["state"]["corporations"]["IR"]["cash"], 1000)
        status, restored = await h.request("GET", path, token=info["spectator_token"])
        self.assertEqual(status, 200)
        self.assertEqual(restored["state"], view["state"])
        await act("end_turn")
        for _ in range(3):
            await act("pass")
        self.assertEqual(view["state"]["round"], "operating")
        self.assertEqual(view["state"]["corporations"]["IR"]["cash"], 1000)
        self.assertEqual(view["state"]["board"]["E2"]["tokens"], [["IR"]])
        await act("lay_tile", hex="E2", tile="5", rotation=4)
        await act("dividend", payout=False)
        await act("buy_train", train="2-0")
        await act("end_turn")
        for _ in range(3):
            await act("pass")
        self.assertIn("run_best_routes", view["legal_actions"]["types"])
        await act("run_best_routes")
        self.assertEqual(view["state"]["operating_turn"]["revenue"], 50)
        routes = view["state"]["operating_turn"]["routes"]
        await act("run_routes", routes=routes)
        await act("dividend", payout=False)
        self.assertEqual(view["state"]["corporations"]["IR"]["cash"], 970)
        state = view["state"]
        status, _ = await h.request(
            "POST",
            path + "/actions",
            {
                "expected_action_id": state["revision"],
                "action": {"type": "run_best_routes"},
            },
            info["player_tokens"][0],
        )
        self.assertEqual(status, 422)
        status, restored = await h.request("GET", path, token=info["spectator_token"])
        self.assertEqual(status, 200)
        self.assertEqual(restored["state"], state)
        self.assertEqual(engine1889.replay(["A", "B", "C"], state["history"]), state)
