"""Regression matrix for BACKLOG-03–11; accounting-balanced corruptions matter."""

import unittest
from copy import deepcopy

from app import engine1830, engine1889
from app.engine1830 import board as b1830
from app.engine1889 import board as b1889
from app.unittests import test_Engine1830 as f1830, test_Engine1889 as f1889


class BacklogSnapshotTests(unittest.TestCase):
    def reject(self, change):
        for module in (engine1830, engine1889):
            with self.subTest(variant=module.__name__):
                state = module.new_game(["A", "B", "C"])
                change(state)
                original = deepcopy(state)
                for operation in (
                    module.validate_state,
                    module.migrate_state,
                    lambda s: module.apply_action(s, dict(type="pass", player="p1")),
                ):
                    with self.assertRaises(module.RuleError):
                        operation(state)
                    self.assertEqual(state, original)

    def test_revision_types_ranges_and_history_consistency(self):
        for value in (False, 0.0, -1, 100, "0", None):
            with self.subTest(revision=value):
                self.reject(lambda s: s.update(revision=value))
        self.reject(lambda s: s.update(history=[None], revision=1))

    def test_action_revision_types_and_ranges(self):
        for module in (engine1830, engine1889):
            s = module.new_game(["A", "B", "C"])
            for value in (False, 0.0, -1, "0"):
                for field in ("expected_revision", "expected_action_id"):
                    with self.subTest(module=module.__name__, field=field, value=value):
                        action = dict(type="pass", player="p1")
                        kwargs = {}
                        (kwargs if field == "expected_revision" else action)[
                            field
                        ] = value
                        with self.assertRaises(module.RuleError):
                            module.apply_action(s, action, **kwargs)
                        self.assertEqual(s["revision"], 0)
            self.assertEqual(
                module.apply_action(
                    s, dict(type="pass", player="p1"), expected_revision=0
                )["revision"],
                1,
            )

    def test_unknown_phase_round_and_inconsistent_finished_state(self):
        for field, value in (
            ("phase", "bogus"),
            ("round", "bogus"),
            ("finished", True),
            ("finished", 0),
            ("end_reason", "bank"),
            ("result", {}),
        ):
            self.reject(lambda s: s.update({field: value}))

    def test_nonobject_and_missing_required_structure_are_rule_errors(self):
        for module in (engine1830, engine1889):
            for state in (
                None,
                [],
                1,
                "state",
                {},
                {"variant": module.__name__[-4:], "schema_version": 1},
            ):
                for operation in (module.validate_state, module.migrate_state):
                    with self.subTest(
                        module=module.__name__, state=state
                    ), self.assertRaises(module.RuleError):
                        operation(state)

    def test_operating_lifecycle_and_actor_consistency(self):
        for module, fixture in (
            (engine1830, f1830.Rules1830Tests),
            (engine1889, f1889.Rules1889Tests),
        ):
            f = fixture("runTest")
            f.setUp()
            f.operating()
            module.validate_state(f.s)
            for case in (
                "step",
                "corp",
                "missing_turn",
                "actor",
                "dividend",
                "order",
                "index",
                "interrupt",
            ):
                state = deepcopy(f.s)
                if case == "step":
                    state["operating_turn"]["step"] = "bogus"
                elif case == "corp":
                    state["current_corporation"] = "unknown"
                elif case == "missing_turn":
                    state["operating_turn"] = None
                elif case == "actor":
                    state["current_player"] = (
                        "p2" if state["current_player"] != "p2" else "p1"
                    )
                elif case == "order":
                    state["or_order"] = []
                elif case == "index":
                    state["or_index"] = -1
                elif case == "interrupt":
                    state["pending_special"] = {}
                else:
                    state["operating_turn"]["dividend"] = True
                with self.subTest(module=module.__name__, case=case), self.assertRaises(
                    module.RuleError
                ):
                    module.migrate_state(state)

    def test_bank_requires_integer_but_zero_and_negative_are_valid(self):
        for value in (False, 0.0, 0.5):

            def change(s):
                s["players"]["p1"]["cash"] += s["bank"] - value
                s["bank"] = value

            self.reject(change)
        for module in (engine1830, engine1889):
            for value in (0, -1):
                s = module.new_game(["A", "B", "C"])
                s["players"]["p1"]["cash"] += s["bank"] - value
                s.update(bank=value, bank_broken=True, end_after_set=True)
                module.validate_state(s)

    def test_balanced_invalid_escrow(self):
        for value in (-5, False, 5.0, 5.5):

            def change(s):
                pid = next(iter(s["auction"]["bids"]))
                s["auction"]["bids"][pid]["p1"] = value
                s["bank"] -= value

            self.reject(change)

    def test_share_supply_units_and_holder_catalog(self):
        for value in (1, 1.0, False):

            def change(s):
                c = next(iter(s["corporations"].values()))
                c.update(pool=value, ipo=100 - value)

            self.reject(change)
        self.reject(
            lambda s: next(iter(s["corporations"].values()))["holdings"].update(
                unknown=0
            )
        )
        self.reject(
            lambda s: next(iter(s["corporations"].values()))["holdings"].pop("p1")
        )

        def stale_president(s):
            c = next(iter(s["corporations"].values()))
            c.update(ipo=50, president="p1")
            c["holdings"].update(p1=20, p2=30)

        self.reject(stale_president)

    def test_duplicate_unknown_and_rusted_owned_trains(self):
        for case in ("duplicate", "unknown_id", "unknown_owner", "rusted"):

            def change(s):
                cid = next(iter(s["corporations"]))
                if case == "unknown_owner":
                    s["trains"]["2-0"]["owner"] = "unknown"
                elif case == "unknown_id":
                    s["corporations"][cid]["trains"] = ["unknown"]
                else:
                    s["corporations"][cid]["trains"] = ["2-0"] * (
                        2 if case == "duplicate" else 1
                    )
                    s["trains"]["2-0"].update(owner=cid, rusted=case == "rusted")

            self.reject(change)

    def test_unknown_overfull_duplicate_and_noncity_tokens(self):
        for case in ("unknown", "overfull", "duplicate", "array", "home"):

            def change(s):
                cid = next(iter(s["corporations"]))
                c = s["corporations"][cid]
                tile = s["board"][c["home"]]
                if case == "unknown":
                    tile["tokens"][0] = ["unknown"]
                elif case == "overfull":
                    tile["tokens"][0] = list(s["corporations"])
                elif case == "duplicate":
                    tile["nodes"][0]["slots"] = 2
                    tile["tokens"][0] = [cid, cid]
                elif case == "array":
                    tile["tokens"] = []
                else:
                    c["home_placed"] = True

            self.reject(change)

    def test_station_supply_and_town_tokens(self):
        def over_supply(s):
            cid = next(iter(s["corporations"]))
            s["corporations"][cid]["token_supply"] = 0
            s["board"][s["corporations"][cid]["home"]]["tokens"][0] = [cid]

        self.reject(over_supply)

        def town(s):
            cid = next(iter(s["corporations"]))
            tile = next(
                t
                for t in s["board"].values()
                if any(n["kind"] == "town" for n in t["nodes"])
            )
            index = next(i for i, n in enumerate(tile["nodes"]) if n["kind"] == "town")
            tile["tokens"][index] = [cid]

        self.reject(town)

    def test_tile_catalog_and_count_integrity(self):
        for case in ("missing", "extra", "unknown_laid", "bool", "float"):

            def change(s):
                tid = next(iter(s["tiles"]))
                if case == "missing":
                    del s["tiles"][tid]
                elif case == "extra":
                    s["tiles"]["unknown"] = 0
                elif case == "unknown_laid":
                    next(iter(s["board"].values()))["tile"] = "unknown"
                elif case == "bool":
                    s["tiles"][tid] = True
                else:
                    s["tiles"][tid] = float(s["tiles"][tid])

            self.reject(change)


class BacklogHelperTests(unittest.TestCase):
    def test_limits_identifiers_and_malformed_quotations(self):
        for module, board in ((engine1830, b1830), (engine1889, b1889)):
            state = module.new_game(["A", "B", "C"])
            cid = next(iter(state["corporations"]))
            self.assertEqual(board.route_candidates(state, cid, limit=0), [])
            self.assertEqual(board.route_candidates(state, cid, limit=None), [])
            self.assertEqual(board.route_revenue(state, cid, []), (0, []))
            original = deepcopy(state)
            for limit in (-1, False, 1.5, "1"):
                with self.assertRaises(module.RuleError):
                    board.route_candidates(state, cid, limit=limit)
            for routes in (None, [None], [1], {}):
                with self.assertRaises(module.RuleError):
                    board.route_revenue(state, cid, routes)
            for bad in ("unknown", [], False):
                with self.assertRaises(module.RuleError):
                    board.route_candidates(state, bad)
                with self.assertRaises(module.RuleError):
                    board.route_candidates(state, cid, bad)
                with self.assertRaises(module.RuleError):
                    board.route_revenue(state, bad, [])
            self.assertEqual(state, original)
        # Exercise the return-limit comparison on real runnable paths, rather
        # than returning early because an unstarted company has no stations.
        from app.unittests import test_EngineTopologyEdges as topology

        fixture = topology.TopologyEdgeTests("runTest")
        for _ in fixture.networks():
            board, state, cid = fixture.b, fixture.s, fixture.cid
            original = deepcopy(state)
            all_routes = board.route_candidates(state, cid, "3-0", limit=None)
            self.assertGreater(len(all_routes), 1)
            self.assertEqual(len(board.route_candidates(state, cid, "3-0", limit=1)), 1)
            self.assertEqual(board.route_candidates(state, cid, "3-0", limit=0), [])
            self.assertEqual(board.route_revenue(state, cid, [fixture.route])[0], 60)
            self.assertEqual(state, original)
