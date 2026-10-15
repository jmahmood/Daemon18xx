"""Regression scenarios found by reviewing the edge-case inventory itself."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from app import engine1830, engine1889
from app.engine1830 import engine as e1830
from app.engine1889 import engine as e1889
from app.unittests import test_Engine1830 as f1830
from app.unittests import test_Engine1889 as f1889
from app.unittests import test_EngineAuctionAndEmergency as emergency
from app.unittests import test_Engine1830API as api_fixtures


def public_emergency_state():
    """A legal public-action prefix, modified to require emergency funding.

    Give AR a route before its first 5 purchase and buy UTF at twice face.
    AR's president then sells TR shares to help fund the mandatory train.
    No balances, holdings, round flags or history entries are seeded directly.
    """
    record = json.loads(
        (Path(__file__).parent / "fixtures/1889/authored_all_phases.json").read_text()
    )
    state = engine1889.new_game(record["names"])
    for action in record["actions"]:
        if action["type"] == "buy_train" and action.get("train") == "5-0":
            break
        if (
            state["phase"] == "4"
            and state["current_corporation"] == "AR"
            and state["operating_turn"]["step"] == "track"
            and action["type"] == "skip"
        ):
            action = dict(
                type="lay_tile",
                player=state["current_player"],
                hex="K8",
                tile="5",
                rotation=3,
            )
        state = engine1889.apply_action(state, action)
    actor = state["current_player"]
    seller = state["privates"]["UTF"]["owner"]
    for action in (
        dict(
            type="offer",
            player=seller,
            kind="private",
            item="UTF",
            seller=seller,
            buyer="AR",
            price=300,
        ),
        dict(type="buy_private", player=actor, company="UTF", buyer="AR", price=300),
        dict(type="emergency_sell", player=actor, corporation="TR", percent=10),
    ):
        state = engine1889.apply_action(state, action)
    return state


class Old1889EmergencySaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = public_emergency_state()

    def legacy(self):
        state = deepcopy(self.canonical)
        del state["operating_turn"]["emergency_sales"]
        return json.loads(json.dumps(state))

    def test_complete_legacy_history_restores_exact_sale_blocks_without_mutation(self):
        old = self.legacy()
        original = deepcopy(old)
        loaded = engine1889.migrate_state(old)
        self.assertEqual(loaded, self.canonical)
        self.assertEqual(loaded["operating_turn"]["emergency_sales"], ["TR"])
        self.assertEqual(loaded["revision"], old["revision"])
        self.assertEqual(old, original)
        self.assertEqual(engine1889.migrate_state(loaded), loaded)

    def test_incomplete_inconsistent_or_unreplayable_history_is_rejected(self):
        for change in ("truncated", "wrong_action", "changed_cash", "missing"):
            with self.subTest(change=change):
                old = self.legacy()
                if change == "truncated":
                    old["history"].pop()
                elif change == "wrong_action":
                    old["history"][-1]["type"] = "unknown"
                elif change == "changed_cash":
                    old["bank"] -= 1
                    old["players"]["p1"]["cash"] += 1
                else:
                    del old["history"]
                original = deepcopy(old)
                with self.assertRaisesRegex(engine1889.RuleError, "history"):
                    engine1889.migrate_state(old)
                self.assertEqual(old, original)

    def test_ambiguous_seeded_save_cannot_reset_a_used_emergency_block(self):
        fixture = emergency.EmergencyBlock1889Tests("runTest")
        fixture.setUp()
        f = fixture.f
        f.act("emergency_sell", corporation="AR", percent=10)
        del f.s["operating_turn"]["emergency_sales"]
        original = deepcopy(f.s)
        with self.assertRaises(engine1889.RuleError):
            engine1889.apply_action(
                f.s,
                dict(type="emergency_sell", player="p1", corporation="AR", percent=10),
            )
        self.assertEqual(f.s, original)

    def test_bookkeeping_must_be_a_unique_list_of_known_corporations(self):
        for value in (None, "TR", ["missing"], ["TR", "TR"], [[]]):
            with self.subTest(value=value):
                state = deepcopy(self.canonical)
                state["operating_turn"]["emergency_sales"] = value
                with self.assertRaises(engine1889.RuleError):
                    engine1889.migrate_state(state)

    def test_legacy_turn_without_sales_recovers_an_empty_list(self):
        state = engine1889.replay(
            [p["name"] for p in self.canonical["players"].values()],
            self.canonical["history"][:-1],
        )
        legacy = deepcopy(state)
        del legacy["operating_turn"]["emergency_sales"]
        self.assertEqual(engine1889.migrate_state(legacy), state)
        self.assertEqual(state["operating_turn"]["emergency_sales"], [])

    def test_previous_turn_sales_are_not_carried_into_new_operator(self):
        state = deepcopy(self.canonical)
        actor = state["current_player"]
        state = engine1889.apply_action(
            state, dict(type="buy_train", player=actor, train="4-2", price=1)
        )
        state = engine1889.apply_action(state, dict(type="end_turn", player=actor))
        self.assertEqual(state["round"], "operating")
        self.assertNotEqual(state["current_corporation"], "AR")
        legacy = deepcopy(state)
        del legacy["operating_turn"]["emergency_sales"]
        self.assertEqual(engine1889.migrate_state(legacy), state)
        self.assertEqual(state["operating_turn"]["emergency_sales"], [])

    def test_ehime_seller_pass_alias_does_not_reset_current_operator_sale_block(self):
        state = deepcopy(self.canonical)
        seller = state["privates"]["ER"]["owner"]
        actor = state["current_player"]
        for action in (
            dict(
                type="offer",
                player=seller,
                kind="private",
                item="ER",
                seller=seller,
                buyer="AR",
                price=40,
            ),
            dict(type="buy_private", player=actor, company="ER", buyer="AR", price=40),
            dict(type="end_turn", player=seller),
        ):
            state = engine1889.apply_action(state, action)
        self.assertEqual(state["current_corporation"], "AR")
        legacy = deepcopy(state)
        del legacy["operating_turn"]["emergency_sales"]
        self.assertEqual(engine1889.migrate_state(legacy), state)
        self.assertEqual(state["operating_turn"]["emergency_sales"], ["TR"])


class SharedReviewEdgeTests(unittest.TestCase):
    def variants(self):
        for module, engine, fixtures in (
            (engine1830, e1830, f1830),
            (engine1889, e1889, f1889),
        ):
            f = (
                fixtures.Rules1830Tests
                if module is engine1830
                else fixtures.Rules1889Tests
            )("runTest")
            f.setUp()
            yield module, engine, f

    def excess(self, module, engine, f):
        f.operating()
        corporations = ("NYC", "CPR") if module is engine1830 else ("AR", "SR")
        for cid, owner, trains in (
            (corporations[0], "p1", ("3-0", "3-1", "4-0")),
            (corporations[1], "p2", ("3-2", "3-3", "4-1")),
        ):
            f.shares(cid, owner, 20)
            for tid in trains:
                (f.train if module is engine1830 else f.give_train)(cid, tid)
        engine._phase_change(f.s, "5")
        return corporations

    def test_action_discovery_returns_independent_train_choices_and_preserves_state(
        self,
    ):
        for module, engine, f in self.variants():
            cids = self.excess(module, engine, f)
            original = deepcopy(f.s)
            first = module.legal_actions(f.s, "p1")
            second = module.legal_actions(f.s, "p2")
            self.assertEqual(f.s, original)
            first["choices"]["corporations"][cids[0]].clear()
            self.assertEqual(f.s, original)
            self.assertEqual(
                second["choices"]["corporations"][cids[0]],
                original["corporations"][cids[0]]["trains"],
            )
            second["choices"]["corporations"][cids[1]].append("forged")
            self.assertEqual(f.s, original)

    def test_diesel_runs_seven_stops_while_six_train_rejects_the_same_route(self):
        for module, engine, f in self.variants():
            b = engine.topology
            cid = "C&O" if module is engine1830 else "IR"
            east = 4 if module is engine1830 else 0
            west = (east + 3) % 6
            coords = ["E" + str(i) for i in range(2, 16, 2)]
            state = f.s
            state["board"] = {
                coord: b.decode(
                    "city=revenue:10;path=a:%d,b:_0;path=a:%d,b:_0" % (east, west),
                    "yellow",
                )
                for coord in coords
            }
            state["board"][coords[0]]["tokens"][0] = [cid]
            state["corporations"][cid]["trains"] = ["6-0", "D-0"]
            for tid in ("6-0", "D-0"):
                state["trains"][tid]["owner"] = cid
            vertices = [coords[0] + ":n0"]
            for a, z in zip(coords, coords[1:]):
                vertices.extend([a + ":e" + str(east), z + ":e" + str(west), z + ":n0"])
            for path in (vertices, list(reversed(vertices))):
                with self.assertRaisesRegex(module.RuleError, "capacity"):
                    b.validate_routes(state, cid, [dict(train="6-0", vertices=path)])
                self.assertEqual(
                    b.validate_routes(state, cid, [dict(train="D-0", vertices=path)]),
                    70,
                )

    def test_sales_payout_withhold_and_zero_revenue_preserve_original_par(self):
        for module, engine, f in self.variants():
            f.stock()
            f.s["stock_round"] = 2
            cid = "NYC" if module is engine1830 else "IR"
            f.shares(cid, "p1", 60)
            before = deepcopy(f.s["corporations"][cid]["position"])
            f.act("sell_shares", corporation=cid, percent=10)
            self.assertEqual(f.s["corporations"][cid]["par"], 100)
            self.assertNotEqual(f.s["corporations"][cid]["position"], before)
            engine._start_operating(f.s)
            for payout, revenue in ((True, 100), (False, 100), (True, 0)):
                engine._start_corporation(f.s)
                f.s["operating_turn"].update(routes=[], revenue=revenue)
                before = deepcopy(f.s["corporations"][cid]["position"])
                f.act("dividend", payout=payout)
                self.assertNotEqual(f.s["corporations"][cid]["position"], before)
                self.assertEqual(f.s["corporations"][cid]["par"], 100)

    def test_emergency_purchase_rejects_costlier_train_when_returned_train_is_cheapest(
        self,
    ):
        for module, engine, f in self.variants():
            f.operating()
            (f.washington if module is engine1830 else f.route)()
            (f.to_train if module is engine1830 else f.train_step)()
            sellers = ("NYC", "CPR") if module is engine1830 else ("AR", "SR")
            for cid, owner, tids in (
                (sellers[0], "p1", ("3-1", "3-2", "3-3")),
                (sellers[1], "p2", ("3-4",)),
            ):
                f.shares(cid, owner, 20)
                for tid in tids:
                    (f.train if module is engine1830 else f.give_train)(cid, tid)
            engine._phase_change(f.s, "4")
            f.s["trains"]["3-0"]["used"] = True
            cid, actor = f.s["current_corporation"], f.s["current_player"]
            f.cash(f.s["corporations"][cid], 0)
            f.cash(f.s["players"][actor], 500)
            self.assertIn("3-0", engine.available_depot(f.s))
            self.assertIn("4-0", engine.available_depot(f.s))
            f.reject("buy_train", train="4-0", price=300)
            f.act("buy_train", train="3-0", price=180)
            self.assertEqual(f.s["players"][actor]["cash"], 320)
            self.assertEqual(f.s["corporations"][cid]["cash"], 0)
            self.assertEqual(f.s["phase"], "4")

    def test_two_presidents_resolve_all_discards_in_either_order_with_midway_restore(
        self,
    ):
        for module, engine, f in self.variants():
            for reverse in (False, True):
                f.setUp()
                cids = self.excess(module, engine, f)
                order = cids[::-1] if reverse else cids
                current = f.s["current_corporation"], f.s["current_player"]
                self.assertEqual(set(f.s["pending_discards"]), set(cids))
                for cid in cids:
                    owner = f.s["corporations"][cid]["president"]
                    self.assertEqual(
                        module.legal_actions(f.s, owner)["types"], ["discard_train"]
                    )
                f.reject("skip")
                first, last = order
                owner = f.s["corporations"][first]["president"]
                other = f.s["corporations"][last]["president"]
                train = f.s["corporations"][first]["trains"][0]
                f.reject("discard_train", corporation=first, train=train, player=other)
                f.act("discard_train", corporation=first, train=train, player=owner)
                self.assertEqual(f.s["pending_discards"], [last])
                f.s = module.migrate_state(json.loads(json.dumps(f.s)))
                f.reject("skip")
                train = f.s["corporations"][last]["trains"][0]
                f.act("discard_train", corporation=last, train=train, player=other)
                self.assertEqual(f.s["pending_discards"], [])
                self.assertEqual(
                    (f.s["current_corporation"], f.s["current_player"]), current
                )
                f.act("skip")
                self.assertEqual(f.s["operating_turn"]["step"], "token")

    def test_owned_five_and_six_trade_for_diesel_at_limit_with_exact_discount(self):
        for module, engine, f in self.variants():
            for old, retained in (("5-0", "6-1"), ("6-0", "5-1")):
                f.setUp()
                f.operating()
                engine._phase_change(f.s, "6")
                cid = f.s["current_corporation"]
                for tid in (old, retained):
                    (f.train if module is engine1830 else f.give_train)(cid, tid)
                f.cash(f.s["corporations"][cid], 2000)
                (f.to_train if module is engine1830 else f.train_step)()
                for price in (799, 801):
                    f.reject("buy_train", train="D-0", trade_in=old, price=price)
                f.act("buy_train", train="D-0", trade_in=old, price=800)
                self.assertEqual(f.s["corporations"][cid]["cash"], 1200)
                self.assertEqual(
                    set(f.s["corporations"][cid]["trains"]), {retained, "D-0"}
                )
                self.assertEqual(f.s["trains"][old]["owner"], "depot")
                self.assertTrue(f.s["trains"][old]["used"])
                self.assertIn(old, engine.available_depot(f.s))
                self.assertEqual(f.s["phase"], "D")


class Old1889SaveHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = api_fixtures.Rules1830APITests("runTest")
        await self.h.asyncSetUp()
        self.canonical = public_emergency_state()
        status, self.info = await self.h.request(
            "POST", "/api/1889/games", dict(max_players=4)
        )
        self.assertEqual(status, 200)
        self.path = "/api/1889/games/" + self.info["room_code"]
        status, _ = await self.h.request(
            "POST",
            self.path + "/start",
            dict(player_names=[p["name"] for p in self.canonical["players"].values()]),
            self.info["creator_token"],
        )
        self.assertEqual(status, 200)
        self.game = await self.h.db.get_game_by_room_code(self.info["room_code"])

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def save_legacy(self, corrupt=False):
        legacy = deepcopy(self.canonical)
        del legacy["operating_turn"]["emergency_sales"]
        if corrupt:
            legacy["history"].pop()
        await self.h.db.save_rules_state(self.game["id"], legacy, 0)
        return legacy

    async def test_old_snapshot_migrates_on_read_and_persists_only_on_accepted_action(
        self,
    ):
        legacy = await self.save_legacy()
        status, view = await self.h.request(
            "GET", self.path, token=self.info["spectator_token"]
        )
        self.assertEqual(status, 200, view)
        self.assertEqual(view["state"], self.canonical)
        record = await self.h.db.get_latest_game_state(self.game["id"])
        self.assertEqual(json.loads(record["state_json"]), legacy)
        actor = self.canonical["current_player"]
        status, view = await self.h.request(
            "POST",
            self.path + "/actions",
            dict(expected_action_id=legacy["revision"], action=dict(type="bankrupt")),
            self.info["player_tokens"][int(actor[1:]) - 1],
        )
        self.assertEqual(status, 200, view)
        expected = engine1889.apply_action(
            self.canonical,
            dict(type="bankrupt", player=actor, expected_action_id=legacy["revision"]),
        )
        self.assertEqual(view["state"], expected)
        self.assertEqual(view["state"]["end_reason"], "bankruptcy")
        record = await self.h.db.get_latest_game_state(self.game["id"])
        self.assertEqual(json.loads(record["state_json"]), expected)

    async def test_ambiguous_old_snapshot_returns_conflict_without_appending(self):
        legacy = await self.save_legacy(corrupt=True)
        status, _ = await self.h.request(
            "GET", self.path, token=self.info["creator_token"]
        )
        self.assertEqual(status, 409)
        status, _ = await self.h.request(
            "POST",
            self.path + "/actions",
            dict(expected_action_id=legacy["revision"], action=dict(type="bankrupt")),
            self.info["player_tokens"][3],
        )
        self.assertEqual(status, 409)
        record = await self.h.db.get_latest_game_state(self.game["id"])
        self.assertEqual(json.loads(record["state_json"]), legacy)


if __name__ == "__main__":
    unittest.main()
