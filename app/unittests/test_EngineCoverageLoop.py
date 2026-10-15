"""Boundary and ownership combinations from the iterative coverage audit."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app import engine1830, engine1889
from app.engine1830 import engine as e1830
from app.engine1889 import engine as e1889
from app.unittests import test_Engine1889 as fixtures1889
from app.unittests import test_Engine1830 as fixtures1830
from app.unittests import test_Engine1830API as api_fixtures


class CertificateBoundaryTests(unittest.TestCase):
    VARIANTS = (
        (engine1830, e1830, {2: 28, 3: 20, 4: 16, 5: 13, 6: 11}),
        (engine1889, e1889, {2: 25, 3: 19, 4: 14, 5: 12, 6: 11}),
    )

    def boundary(self, module, engine, count, limit):
        state = module.new_game(["Player " + str(i) for i in range(count)])
        # Isolate certificate limits from private powers and auction affordability.
        for private in state["privates"].values():
            private["closed"] = True
        engine._start_stock(state)
        target = list(state["corporations"])[-1]
        remaining = limit - 1
        for cid, corp in state["corporations"].items():
            if cid == target or not remaining:
                continue
            certificates = min(5, remaining)
            engine._set_par(state, corp, 100)
            percent = (certificates + 1) * 10
            corp["ipo"] -= percent
            corp["holdings"]["p1"] = percent
            corp["president"] = "p1"
            engine._float(corp)
            remaining -= certificates
        self.assertEqual(remaining, 0)
        module.validate_state(state)
        self.assertEqual(engine.certificate_count(state, "p1"), limit - 1)
        return state, target

    def reject(self, module, state, action, message):
        old = deepcopy(state)
        with self.assertRaisesRegex(module.RuleError, message):
            module.apply_action(state, action)
        self.assertEqual(state, old)

    def test_buy_and_pass_enforce_exact_certificate_limit_for_every_player_count(self):
        for module, engine, limits in self.VARIANTS:
            for count, limit in limits.items():
                with self.subTest(variant=module.__name__, players=count):
                    state, target = self.boundary(module, engine, count, limit)
                    state = module.apply_action(
                        state,
                        dict(
                            type="buy_shares",
                            player="p1",
                            corporation=target,
                            price=100,
                        ),
                    )
                    self.assertEqual(engine.certificate_count(state, "p1"), limit)
                    engine._start_stock(state)
                    self.reject(
                        module,
                        state,
                        dict(type="buy_shares", player="p1", corporation=target),
                        "Certificate limit",
                    )
                    passed = module.apply_action(
                        state, dict(type="end_turn", player="p1")
                    )
                    self.assertEqual(passed["current_player"], "p2")
                    # A former colored-zone holding can put a player over limit.
                    corp = state["corporations"][target]
                    corp["ipo"] -= 10
                    corp["holdings"]["p1"] += 10
                    self.assertEqual(engine.certificate_count(state, "p1"), limit + 1)
                    self.reject(
                        module,
                        state,
                        dict(type="end_turn", player="p1"),
                        "excess certificates",
                    )
                    state = module.apply_action(
                        state,
                        dict(
                            type="sell_shares",
                            player="p1",
                            corporation=target,
                            percent=10,
                        ),
                    )
                    self.assertEqual(engine.certificate_count(state, "p1"), limit)
                    state = module.apply_action(
                        state, dict(type="end_turn", player="p1")
                    )
                    self.assertEqual(state["current_player"], "p2")


class Ownership1889Tests(unittest.TestCase):
    def fixture(self):
        f = fixtures1889.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.s["phase"] = "3"
        return f

    def test_ehime_seller_can_control_buyer_and_resolve_lay_or_pass_after_restore(self):
        for lay in (False, True):
            with self.subTest(lay=lay):
                f = self.fixture()
                corp = f.s["corporations"]["IR"]
                corp["holdings"].update(p1=0, p3=50)
                corp["president"] = "p3"
                f.s["current_player"] = "p3"
                before = deepcopy(f.s["operating_turn"])
                f.act("buy_private", company="ER", buyer="IR", price=40)
                self.assertEqual(f.s["pending_special"]["player"], "p3")
                f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
                self.assertEqual(
                    engine1889.legal_actions(f.s, "p3")["types"], ["lay_tile", "pass"]
                )
                f.reject("pass", player="p1")
                if lay:
                    f.act(
                        "lay_tile",
                        player="p3",
                        special="ER",
                        hex="C4",
                        tile="14",
                        rotation=1,
                    )
                    self.assertEqual(f.s["board"]["C4"]["tile"], "14")
                else:
                    f.act("pass", player="p3")
                self.assertIsNone(f.s["pending_special"])
                self.assertEqual(f.s["current_player"], "p3")
                self.assertEqual(f.s["operating_turn"], before)
                f.route()

    def test_mitsubishi_sale_disables_port_for_former_owner_and_buying_president(self):
        f = self.fixture()
        f.act(
            "offer",
            player="p2",
            kind="private",
            item="MF",
            seller="p2",
            buyer="IR",
            price=30,
        )
        f.act("buy_private", company="MF", buyer="IR", price=30)
        self.assertEqual(f.s["privates"]["MF"]["owner"], "IR")
        self.assertFalse(f.s["privates"]["MF"]["used"])
        f.s = engine1889.migrate_state(json.loads(json.dumps(f.s)))
        for actor in ("p1", "p2"):
            self.assertNotIn(
                "port_hexes", engine1889.legal_actions(f.s, actor)["choices"]
            )
            f.reject(
                "lay_tile",
                player=actor,
                special="MF",
                hex="G10",
                tile="437",
                rotation=0,
            )
        self.assertIsNone(f.s["board"]["G10"]["tile"])


class SavedMetadataTests(unittest.TestCase):
    def test_partial_1830_legacy_home_metadata_validates_and_migrates_idempotently(
        self,
    ):
        expected = engine1830.new_game(["A", "B", "C"])
        state = deepcopy(expected)
        state["schema_version"] = 1
        for cid, corp in state["corporations"].items():
            if cid != "NYC":
                del corp["home_city"]
        original = deepcopy(state)
        self.assertTrue(engine1830.validate_state(state))
        self.assertEqual(state, original)
        migrated = engine1830.migrate_state(state)
        self.assertEqual(migrated, expected)
        self.assertEqual(engine1830.migrate_state(migrated), migrated)
        self.assertEqual(state, original)

    def test_wrong_variant_or_noninteger_schema_rejected_by_load_validate_and_action(
        self,
    ):
        for module in (engine1830, engine1889):
            for field, value in (
                ("variant", "1889" if module is engine1830 else "1830"),
                ("variant", None),
                ("schema_version", True),
                ("schema_version", 1.0),
                ("schema_version", "1"),
                ("schema_version", -1),
                ("schema_version", 999),
            ):
                with self.subTest(variant=module.__name__, field=field, value=value):
                    state = module.new_game(["A", "B", "C"])
                    state[field] = value
                    original = deepcopy(state)
                    for operation in (
                        module.validate_state,
                        module.migrate_state,
                        lambda s: module.apply_action(
                            s, dict(type="pass", player="p1")
                        ),
                    ):
                        with self.assertRaises(module.RuleError):
                            operation(state)
                        self.assertEqual(state, original)

    def test_money_shares_trains_tiles_and_actor_corruption_are_rejected(self):
        for module in (engine1830, engine1889):
            for case in (
                "bank",
                "player_negative",
                "player_float",
                "corp_negative",
                "corp_float",
                "share_total",
                "pool_overflow",
                "holding_negative",
                "holding_float",
                "president",
                "train_owner",
                "tile_supply",
                "actor",
            ):
                with self.subTest(variant=module.__name__, case=case):
                    state = module.new_game(["A", "B", "C"])
                    corp = next(iter(state["corporations"].values()))
                    if case == "bank":
                        state["bank"] += 1
                    elif case.startswith("player_"):
                        amount = -1 if case.endswith("negative") else 10.0
                        state["bank"] += state["players"]["p1"]["cash"] - amount
                        state["players"]["p1"]["cash"] = amount
                    elif case.startswith("corp_"):
                        amount = -1 if case.endswith("negative") else 10.0
                        state["bank"] -= amount
                        corp["cash"] = amount
                    elif case == "share_total":
                        corp["ipo"] = 90
                    elif case == "pool_overflow":
                        corp.update(ipo=40, pool=60)
                    elif case.startswith("holding_"):
                        corp["ipo"] = 90
                        if case.endswith("negative"):
                            corp["holdings"].update(p1=-10, p2=20)
                        else:
                            corp["holdings"]["p1"] = 10.0
                    elif case == "president":
                        corp.update(ipo=90, president="p1")
                        corp["holdings"]["p1"] = 10
                    elif case == "train_owner":
                        corp["trains"].append("2-0")
                    elif case == "tile_supply":
                        state["tiles"][next(iter(state["tiles"]))] += 1
                    else:
                        state["current_player"] = "unknown"
                    original = deepcopy(state)
                    with self.assertRaises(module.RuleError):
                        module.validate_state(state)
                    self.assertEqual(state, original)


class NegotiationLifecycleTests(unittest.TestCase):
    def test_new_president_must_consent_and_failed_purchase_keeps_matching_offer(self):
        for module, engine, fixture, buyer, seller in (
            (engine1830, e1830, fixtures1830.Rules1830Tests, "NYC", "CPR"),
            (engine1889, e1889, fixtures1889.Rules1889Tests, "IR", "AR"),
        ):
            with self.subTest(variant=module.__name__):
                f = fixture("runTest")
                f.setUp()
                f.stock()
                f.s["stock_round"] = 2
                f.shares(buyer, "p1", 60 if module is engine1830 else 50)
                f.shares(seller, "p2", 30)
                f.shares(seller, "p3", 20)
                (f.train if module is engine1830 else f.give_train)(seller, "2-0")
                f.s["current_player"] = "p2"
                terms = dict(
                    kind="train", item="2-0", seller=seller, buyer=buyer, price=50
                )
                f.act("offer", player="p2", **terms)
                f.act("sell_shares", corporation=seller, percent=10)
                f.act("end_turn")
                f.act("buy_shares", corporation=seller)
                self.assertEqual(f.s["corporations"][seller]["president"], "p3")
                f.act("end_turn")
                for _ in range(3):
                    f.act("pass")
                self.assertEqual(f.s["current_corporation"], buyer)
                (f.to_train if module is engine1830 else f.train_step)()
                f.reject("buy_train", train="2-0", price=50)
                f.reject("offer", player="p2", **terms)
                f.act("offer", player="p3", **terms)
                f.cash(f.s["corporations"][buyer], 0)
                offers = deepcopy(f.s["offers"])
                f.reject("buy_train", train="2-0", price=50)
                self.assertEqual(f.s["offers"], offers)
                f.cash(f.s["corporations"][buyer], 100)
                f.act("buy_train", train="2-0", price=50)
                self.assertEqual(f.s["corporations"][seller]["trains"], [])
                self.assertEqual(f.s["corporations"][buyer]["trains"], ["2-0"])
                self.assertFalse(any(o["offered_by"] == "p3" for o in f.s["offers"]))


class TransportBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = api_fixtures.Rules1830APITests("runTest")
        await self.h.asyncSetUp()

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def room(self, variant, count=3):
        status, info = await self.h.request(
            "POST", "/api/" + variant + "/games", dict(max_players=count)
        )
        self.assertEqual(status, 200)
        path = "/api/" + variant + "/games/" + info["room_code"]
        status, view = await self.h.request(
            "POST",
            path + "/start",
            dict(player_names=["Player " + str(i) for i in range(count)]),
            info["creator_token"],
        )
        self.assertEqual(status, 200, view)
        return info, path, view

    async def test_all_player_counts_complete_private_auction_through_authenticated_http(
        self,
    ):
        for variant in ("1830", "1889"):
            for count in range(2, 7):
                with self.subTest(variant=variant, count=count):
                    info, path, view = await self.room(variant, count)
                    for company in view["state"]["privates"]:
                        actor = view["state"]["current_player"]
                        status, view = await self.h.request(
                            "POST",
                            path + "/actions",
                            dict(
                                expected_action_id=view["state"]["revision"],
                                action=dict(type="buy_private", company=company),
                            ),
                            info["player_tokens"][int(actor[1:]) - 1],
                        )
                        self.assertEqual(status, 200, view)
                        if view["state"]["pending_par"]:
                            actor = view["state"]["pending_par"]
                            status, view = await self.h.request(
                                "POST",
                                path + "/actions",
                                dict(
                                    expected_action_id=view["state"]["revision"],
                                    action=dict(type="par", price=100),
                                ),
                                info["player_tokens"][int(actor[1:]) - 1],
                            )
                            self.assertEqual(status, 200, view)
                    self.assertEqual(view["state"]["round"], "stock")
                    self.assertEqual(len(view["state"]["players"]), count)
                    module = engine1830 if variant == "1830" else engine1889
                    module.validate_state(view["state"])

    async def test_wrong_variant_and_boolean_saved_schema_return_conflict(self):
        for variant in ("1830", "1889"):
            for field, value in (
                ("variant", "1889" if variant == "1830" else "1830"),
                ("schema_version", True),
            ):
                info, path, view = await self.room(variant)
                state = view["state"]
                state.update(revision=1)
                state[field] = value
                game = await self.h.db.get_game_by_room_code(info["room_code"])
                await self.h.db.save_rules_state(game["id"], state, 0)
                status, _ = await self.h.request(
                    "GET", path, token=info["spectator_token"]
                )
                self.assertEqual(status, 409)
                record = await self.h.db.get_latest_game_state(game["id"])
                self.assertEqual(json.loads(record["state_json"]), state)

    async def test_commit_failure_rolls_back_snapshot_and_same_revision_can_retry(self):
        import sqlite3
        import aiosqlite

        for variant in ("1830", "1889"):
            info, path, initial = await self.room(variant)
            payload = dict(expected_action_id=0, action=dict(type="pass"))
            with patch.object(
                aiosqlite.Connection,
                "commit",
                new=AsyncMock(
                    side_effect=sqlite3.OperationalError("injected commit failure")
                ),
            ):
                with self.assertRaises(sqlite3.OperationalError):
                    await self.h.request(
                        "POST", path + "/actions", payload, info["player_tokens"][0]
                    )
            status, restored = await self.h.request(
                "GET", path, token=info["creator_token"]
            )
            self.assertEqual(status, 200)
            self.assertEqual(restored, initial)
            status, accepted = await self.h.request(
                "POST", path + "/actions", payload, info["player_tokens"][0]
            )
            self.assertEqual(status, 200, accepted)
            self.assertEqual(accepted["state"]["revision"], 1)


class GameplayCoverageTests(unittest.TestCase):
    def test_competitive_bo_award_interrupts_for_par_and_resumes_stock_after_restore(
        self,
    ):
        f = fixtures1830.Rules1830Tests("runTest")
        f.setUp()
        f.act("bid", company="BO", price=225)
        f.act("bid", company="BO", price=230)
        for company in ("SV", "CS", "DH", "MH", "CA"):
            f.act("buy_private", company=company)
        self.assertEqual(f.s["auction"]["active"], "BO")
        self.assertEqual(f.s["current_player"], "p1")
        cash = f.s["players"]["p1"]["cash"]
        f.act("pass")
        self.assertEqual(f.s["players"]["p1"]["cash"], cash + 225)
        self.assertEqual(f.s["privates"]["BO"]["owner"], "p2")
        self.assertEqual(f.s["corporations"]["B&O"]["holdings"]["p2"], 20)
        self.assertEqual(f.s["pending_par"], "p2")
        f.s = engine1830.migrate_state(json.loads(json.dumps(f.s)))
        self.assertEqual(engine1830.legal_actions(f.s)["types"], ["par"])
        f.reject("par", player="p1", price=100)
        f.reject("pass", player="p2")
        f.act("par", player="p2", price=100)
        self.assertIsNone(f.s["pending_par"])
        self.assertEqual(f.s["round"], "stock")
        self.assertEqual(f.s["priority"], "p2")
        self.assertEqual(f.s["current_player"], "p2")
        self.assertEqual(f.s["corporations"]["B&O"]["par"], 100)
        engine1830.validate_state(f.s)

    def test_presidential_funding_of_corporate_train_obeys_variant_and_face_value(self):
        for module, fixture, seller in (
            (engine1830, fixtures1830.Rules1830Tests, "NYC"),
            (engine1889, fixtures1889.Rules1889Tests, "AR"),
        ):
            for price in (80, 81):
                with self.subTest(variant=module.__name__, price=price):
                    f = fixture("runTest")
                    f.setUp()
                    f.operating()
                    if module is engine1830:
                        f.washington()
                        f.train(seller, "2-0")
                    else:
                        f.route()
                        f.give_train(seller, "2-0")
                    f.shares(seller, "p2", 60)
                    f.act("dividend", payout=False)
                    buyer = f.s["current_corporation"]
                    president = f.s["corporations"][buyer]["president"]
                    self.assertNotEqual(president, "p2")
                    f.cash(f.s["corporations"][buyer], 40)
                    f.cash(f.s["players"][president], 100)
                    f.act(
                        "offer",
                        player="p2",
                        kind="train",
                        item="2-0",
                        seller=seller,
                        buyer=buyer,
                        price=price,
                    )
                    original = deepcopy(f.s)
                    if module is engine1889 or price == 81:
                        message = (
                            "cannot subsidize"
                            if module is engine1889
                            else "cannot exceed face value"
                        )
                        with self.assertRaisesRegex(module.RuleError, message):
                            f.act("buy_train", train="2-0", price=price)
                        self.assertEqual(f.s, original)
                        # Consent remains usable if the treasury can pay unaided.
                        f.cash(f.s["corporations"][buyer], price)
                    f.act("buy_train", train="2-0", price=price)
                    self.assertEqual(
                        f.s["players"][president]["cash"],
                        60 if module is engine1830 and price == 80 else 100,
                    )
                    self.assertEqual(f.s["corporations"][buyer]["cash"], 0)
                    self.assertEqual(
                        f.s["corporations"][seller]["cash"],
                        original["corporations"][seller]["cash"] + price,
                    )
                    self.assertEqual(f.s["trains"]["2-0"]["owner"], buyer)
                    self.assertNotIn("2-0", f.s["corporations"][seller]["trains"])
                    module.validate_state(f.s)

    def test_round_specific_action_dispatch_rejects_other_rounds_atomically(self):
        for module, fixture in (
            (engine1830, fixtures1830.Rules1830Tests),
            (engine1889, fixtures1889.Rules1889Tests),
        ):
            for round_name, forbidden in (
                ("auction", ("buy_train", "lay_tile", "sell_shares", "unknown")),
                ("stock", ("bid", "buy_train", "lay_tile", "discard_train", "unknown")),
                ("operating", ("bid", "buy_shares", "sell_shares", "unknown")),
            ):
                f = fixture("runTest")
                f.setUp()
                if round_name == "stock":
                    f.stock()
                elif round_name == "operating":
                    f.operating()
                for kind in forbidden:
                    with self.subTest(
                        variant=module.__name__, round=round_name, kind=kind
                    ):
                        original = deepcopy(f.s)
                        with self.assertRaises(module.RuleError):
                            module.apply_action(
                                f.s, dict(type=kind, player=f.s["current_player"])
                            )
                        self.assertEqual(f.s, original)

    def test_1889_action_aliases_match_canonical_result_and_history(self):
        f = fixtures1889.Rules1889Tests("runTest")
        f.setUp()
        f.stock()
        f.shares("IR", "p1", 20)
        cases = [(deepcopy(f.s), "exchange_private", "exchange_dr", "p2")]
        f.operating()
        f.route()
        f.train_step()
        corp = f.s["corporations"]["IR"]
        corp["holdings"].update(p1=30, p2=30, p3=0)
        corp.update(ipo=40, pool=0)
        f.cash(corp, 0)
        f.cash(f.s["players"]["p1"], 0)
        cases.append((f.s, "bankrupt", "bankruptcy", "p1"))
        for state, canonical, alias, player in cases:
            with self.subTest(alias=alias):
                original = deepcopy(state)
                action = dict(type=alias, player=player)
                result = engine1889.apply_action(state, action)
                self.assertEqual(
                    result,
                    engine1889.apply_action(state, dict(type=canonical, player=player)),
                )
                self.assertEqual(result["history"][-1]["type"], canonical)
                self.assertEqual(action["type"], alias)
                self.assertEqual(state, original)

    def test_complete_authored_1889_games_for_remaining_player_counts(self):
        expected = {
            2: ("bank", "5", {"p1": 145, "p2": 145}),
            3: ("bank", "5", {"p1": 110, "p2": 90, "p3": 105}),
            5: (
                "bankruptcy",
                "6",
                {"p1": 20, "p2": 615, "p3": 80, "p4": 100, "p5": 90},
            ),
            6: (
                "bankruptcy",
                "4",
                {"p1": 445, "p2": 230, "p3": 375, "p4": 390, "p5": 395, "p6": 400},
            ),
        }
        for count, (ending, phase, result) in expected.items():
            with self.subTest(players=count):
                path = (
                    Path(__file__).parent
                    / "fixtures"
                    / "1889"
                    / ("authored_%d_players.json" % count)
                )
                record = json.loads(path.read_text())
                state = engine1889.new_game(record["names"])
                for index, action in enumerate(record["actions"]):
                    state = engine1889.apply_action(state, action)
                    # Restore a running game as well as both terminal conditions.
                    if index == len(record["actions"]) // 2:
                        state = engine1889.migrate_state(json.loads(json.dumps(state)))
                self.assertTrue(state["finished"])
                self.assertEqual(state["end_reason"], ending)
                self.assertEqual(state["phase"], phase)
                self.assertEqual(state["result"], result)
                self.assertEqual(state["revision"], len(record["actions"]))
                if ending == "bank":
                    self.assertLessEqual(state["bank"], 0)
                    self.assertEqual(state["or_number"], state["or_total"])
                else:
                    self.assertEqual(
                        sum(p["bankrupt"] for p in state["players"].values()), 1
                    )
                restored = engine1889.migrate_state(json.loads(json.dumps(state)))
                self.assertEqual(restored, state)
                self.assertEqual(
                    engine1889.legal_actions(restored),
                    {"player": None, "types": [], "choices": {}},
                )
                before = deepcopy(restored)
                with self.assertRaises(engine1889.RuleError):
                    engine1889.apply_action(restored, dict(type="pass", player="p1"))
                self.assertEqual(restored, before)
                engine1889.validate_state(restored)

    def test_route_quote_accepts_paths_or_vertices_and_preserves_state(self):
        f = fixtures1889.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.route()
        f.give_train("IR", "2-0")
        b = e1889.topology
        vertices = b.route_candidates(f.s, "IR", "2-0")[0]
        paths = []
        for a, z in zip(vertices["vertices"], vertices["vertices"][1:]):
            coord, first = a.split(":")
            other, last = z.split(":")
            if coord == other:
                index = next(
                    i
                    for i, edge in enumerate(f.s["board"][coord]["paths"])
                    if set(edge) == {first, last}
                )
                paths.append([coord, index])
        before = deepcopy(f.s)
        for route in (
            vertices,
            dict(train="2-0", paths=paths),
            dict(train="2-0", paths=list(reversed(paths))),
        ):
            revenue, details = b.route_revenue(f.s, "IR", [route])
            self.assertEqual(revenue, 50)
            self.assertEqual(set(details[0]["stops"]), {"E2:n0", "F1:n0"})
            self.assertEqual(f.s, before)
        self.assertEqual(b.route_revenue(f.s, "IR", []), (0, []))
        for invalid in (paths + paths, paths[:1]):
            with self.assertRaises(engine1889.RuleError):
                b.route_revenue(f.s, "IR", [dict(train="2-0", paths=invalid)])
        self.assertEqual(f.s, before)

    def test_skip_routes_requires_no_runnable_train_and_dividend_cannot_be_skipped(
        self,
    ):
        for runnable in (False, True):
            with self.subTest(runnable=runnable):
                f = fixtures1889.Rules1889Tests("runTest")
                f.setUp()
                f.operating()
                f.route()
                if runnable:
                    f.give_train("IR", "2-0")
                f.act("skip")  # Token step.
                self.assertEqual(f.s["operating_turn"]["step"], "routes")
                if runnable:
                    f.reject("skip")
                    f.act(
                        "run_routes",
                        routes=e1889.topology.route_candidates(f.s, "IR", "2-0")[:1],
                    )
                else:
                    f.act("skip")
                    self.assertEqual(f.s["operating_turn"]["routes"], [])
                    self.assertEqual(f.s["operating_turn"]["revenue"], 0)
                self.assertEqual(f.s["operating_turn"]["step"], "dividend")
                f.reject("skip")
                f.act("dividend", payout=True)
                f.reject("skip")

    def test_action_discovery_covers_initial_competitive_auction_and_terminal_states(
        self,
    ):
        for module, company, cheapest in (
            (engine1830, "CS", "SV"),
            (engine1889, "ER", "TR"),
        ):
            state = module.new_game(["A", "B", "C"])
            before = deepcopy(state)
            choices = module.legal_actions(state)
            self.assertEqual(choices["player"], "p1")
            self.assertIn("bid", choices["types"])
            self.assertEqual(
                set(choices["choices"]["companies"]), set(state["privates"])
            )
            self.assertEqual(module.legal_actions(state, "p2")["types"], [])
            self.assertEqual(state, before)
            for action in (
                dict(type="bid", company=company, price=45),
                dict(type="bid", company=company, price=50),
                dict(type="buy_private", company=cheapest),
            ):
                state = module.apply_action(
                    state, dict(action, player=state["current_player"])
                )
            if module is engine1889:
                # MF precedes ER in 1889's ordered auction.
                state = module.apply_action(
                    state,
                    dict(
                        type="buy_private", company="MF", player=state["current_player"]
                    ),
                )
            self.assertEqual(state["auction"]["active"], company)
            before = deepcopy(state)
            self.assertTrue(
                {"bid", "pass"}.issubset(module.legal_actions(state)["types"])
            )
            self.assertEqual(state, before)
            state["finished"] = True
            self.assertEqual(
                module.legal_actions(state),
                {"player": None, "types": [], "choices": {}},
            )


if __name__ == "__main__":
    unittest.main()
