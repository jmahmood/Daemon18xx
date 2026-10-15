"""Small, explicit rail networks exercise the same boundary rules in both games.

These are board-unit tests: synthetic hexes isolate a rule from the full map.
Real-board integration remains covered by the variant suites and recordings.
"""

import unittest
from copy import deepcopy

from app import engine1830, engine1889
from app.engine1830 import board as board1830
from app.engine1889 import board as board1889
from app.unittests import test_Engine1830Followup as loop_fixtures


class TopologyEdgeTests(unittest.TestCase):
    def networks(self):
        for module, board, cid, east in (
            (engine1830, board1830, "C&O", 4),
            (engine1889, board1889, "IR", 0),
        ):
            self.module, self.b, self.cid = module, board, cid
            self.east, self.west = east, (east + 3) % 6
            self.s = module.new_game(["A", "B", "C"])
            self.s["board"] = {
                coord: board.decode(
                    "city=revenue:%s;path=a:%s,b:_0;path=a:%s,b:_0"
                    % (revenue, self.east, self.west),
                    "yellow",
                )
                for coord, revenue in (("E2", 10), ("E4", 20), ("E6", 30))
            }
            self.s["board"]["E2"]["tokens"][0] = [cid]
            self.c = self.s["corporations"][cid]
            self.c.update(cash=500, home_placed=True, token_supply=3)
            self.c["trains"] = ["2-0", "3-0", "3-1", "D-0"]
            for tid in self.c["trains"]:
                self.s["trains"][tid]["owner"] = cid
            self.vertices = [
                "E2:n0",
                "E2:e" + str(self.east),
                "E4:e" + str(self.west),
                "E4:n0",
                "E4:e" + str(self.east),
                "E6:e" + str(self.west),
                "E6:n0",
            ]
            self.route = {"train": "3-0", "vertices": self.vertices}
            yield

    def reject(self, routes, message):
        original = deepcopy(self.s)
        with self.assertRaisesRegex(self.module.RuleError, message):
            self.b.validate_routes(self.s, self.cid, routes)
        self.assertEqual(self.s, original)

    def test_every_intermediate_city_or_town_counts_toward_capacity_and_revenue(self):
        for _ in self.networks():
            self.assertEqual(self.b.validate_routes(self.s, self.cid, [self.route]), 60)
            self.s["board"]["E4"]["nodes"][0]["kind"] = "town"
            self.assertEqual(self.b.validate_routes(self.s, self.cid, [self.route]), 60)
            self.reject([dict(self.route, train="2-0")], "capacity")
            self.assertEqual(
                self.b.validate_routes(
                    self.s, self.cid, [dict(self.route, train="D-0")]
                ),
                60,
            )

    def test_train_must_be_owned_distinct_and_used_once(self):
        for _ in self.networks():
            self.reject([dict(self.route, train="2-5")], "distinct owned train")
            self.reject([self.route, self.route], "distinct owned train")

    def test_different_trains_cannot_share_track_in_either_direction(self):
        for _ in self.networks():
            for vertices in (self.vertices, list(reversed(self.vertices))):
                self.reject(
                    [self.route, dict(self.route, train="3-1", vertices=vertices)],
                    "share track",
                )

    def test_different_trains_can_share_a_city_without_sharing_track(self):
        for _ in self.networks():
            self.s["board"]["E4"]["tokens"][0] = [self.cid]
            routes = [
                dict(self.route, vertices=self.vertices[:4]),
                dict(self.route, train="3-1", vertices=self.vertices[3:]),
            ]
            self.assertEqual(self.b.validate_routes(self.s, self.cid, routes), 80)

    def test_each_route_needs_its_own_company_station(self):
        for _ in self.networks():
            self.reject([dict(self.route, vertices=self.vertices[3:])], "own railhead")
            self.s["board"]["E2"]["tokens"][0] = []
            self.reject([self.route], "own railhead")

    def test_repeated_vertices_reversal_disconnected_and_non_city_endpoints(self):
        for _ in self.networks():
            self.reject(
                [dict(self.route, vertices=self.vertices + self.vertices[-2::-1])],
                "revisit",
            )
            self.reject([dict(self.route, vertices=["E2:n0", "E6:n0"])], "disconnected")
            self.reject(
                [dict(self.route, vertices=self.vertices[1:])], "revenue centers"
            )

    def test_full_rival_city_is_a_legal_terminus_but_blocks_through_running(self):
        for _ in self.networks():
            self.s["board"]["E4"]["tokens"][0] = ["RIVAL"]
            self.reject([self.route], "blocked city")
            short = dict(self.route, vertices=self.vertices[:4])
            self.assertEqual(self.b.validate_routes(self.s, self.cid, [short]), 30)
            self.assertNotIn("E6:n0", self.b.reachable(self.s["board"], self.cid))
            self.assertIn("E4:n0", self.b.reachable(self.s["board"], self.cid))

    def test_own_token_in_full_city_allows_running_through_it(self):
        for _ in self.networks():
            self.s["board"]["E4"]["tokens"][0] = [self.cid]
            self.assertEqual(self.b.validate_routes(self.s, self.cid, [self.route]), 60)

    def test_offboards_are_termini_and_region_cannot_be_visited_twice(self):
        for _ in self.networks():
            self.s["board"]["E4"]["nodes"][0]["kind"] = "offboard"
            self.reject([self.route], "termini")
            self.assertEqual(
                self.b.validate_routes(
                    self.s, self.cid, [dict(self.route, vertices=self.vertices[:4])]
                ),
                30,
            )
            self.s["board"]["E4"]["nodes"][0]["kind"] = "city"
            for coord in ("E2", "E6"):
                self.s["board"][coord]["nodes"][0]["group"] = "same-region"
            self.reject([self.route], "same offboard region")

    def test_cannot_reverse_at_a_junction_or_switch_crossing_paths(self):
        for _ in self.networks():
            self.s["board"]["E4"]["paths"] = [
                ["e" + str(self.west), "e" + str(self.east)],
                ["e" + str(self.east), "n0"],
            ]
            vertices = self.vertices[:3] + ["E4:e" + str(self.east), "E4:n0"]
            self.reject([dict(self.route, vertices=vertices)], "junction|crossing")
            self.assertNotIn("E4:n0", self.b.reachable(self.s["board"], self.cid))

    def test_route_candidates_respect_capacity_tokens_blocking_and_limit(self):
        for _ in self.networks():
            routes = self.b.route_candidates(self.s, self.cid, "2-0", limit=1)
            self.assertEqual(len(routes), 1)
            self.assertEqual(self.b.validate_routes(self.s, self.cid, routes), 30)
            self.s["board"]["E4"]["tokens"][0] = ["RIVAL"]
            routes = self.b.route_candidates(self.s, self.cid, "3-0")
            self.assertTrue(routes)
            for route in routes:
                self.assertNotIn("E6:n0", route["vertices"])
                self.b.validate_routes(self.s, self.cid, [route])
            self.s["board"]["E2"]["tokens"][0] = []
            self.assertEqual(self.b.route_candidates(self.s, self.cid), [])

    def test_route_path_segments_expand_in_both_directions_and_bad_segments_fail(self):
        for _ in self.networks():
            segments = [["E2", 0], ["E4", 1], ["E4", 0], ["E6", 1]]
            for paths in (segments, list(reversed(segments))):
                route = self.b.route_from_paths(self.s, dict(train="3-0", paths=paths))
                self.assertEqual(self.b.validate_routes(self.s, self.cid, [route]), 60)
            for paths in (
                None,
                [],
                [["E2", True]],
                [["missing", 0]],
                [["E2", 99]],
                [["E2"]],
                [["E2", 0], ["E6", 1]],
            ):
                with self.assertRaises(self.module.RuleError):
                    self.b.route_from_paths(self.s, dict(train="3-0", paths=paths))

    def test_malformed_route_collections_and_vertices_are_rule_errors(self):
        for _ in self.networks():
            for routes in (
                None,
                {},
                [None],
                [dict(self.route, vertices=None)],
                [dict(self.route, vertices=[[], "E2:n0"])],
                [dict(self.route, vertices=["missing:n0", "E2:n0"])],
                [dict(self.route, vertices=["E2:n0"])],
            ):
                self.reject(routes, ".")

    def test_tokens_need_cash_supply_vacancy_and_reachability(self):
        for _ in self.networks():
            for change, message in (
                ("cash", "treasury"),
                ("supply", "remaining"),
                ("full", "vacant"),
                ("unreachable", "reachable"),
            ):
                trial = deepcopy(self.s)
                if change == "cash":
                    trial["corporations"][self.cid]["cash"] = 0
                elif change == "supply":
                    trial["corporations"][self.cid]["token_supply"] = 1
                elif change == "full":
                    trial["board"]["E4"]["tokens"][0] = ["RIVAL"]
                else:
                    trial["board"]["E2"]["paths"] = []
                with self.assertRaisesRegex(self.module.RuleError, message):
                    self.b.place_token(trial, self.cid, "E4")

    def test_tokens_require_a_valid_large_city_and_cannot_duplicate_a_hex(self):
        for _ in self.networks():
            for coord, index in (("missing", 0), ("E4", True), ("E4", -1), ("E4", 2)):
                with self.assertRaises(self.module.RuleError):
                    self.b.place_token(self.s, self.cid, coord, index)
            self.s["board"]["E4"]["nodes"][0]["kind"] = "town"
            with self.assertRaisesRegex(self.module.RuleError, "large city"):
                self.b.place_token(self.s, self.cid, "E4")
            with self.assertRaisesRegex(self.module.RuleError, "Already tokened"):
                self.b.place_token(self.s, self.cid, "E2")

    def test_extra_station_cost_is_variant_specific(self):
        for _ in self.networks():
            self.assertEqual(self.b.place_token(self.s, self.cid, "E4"), 40)
            cost = 40 if self.module is engine1889 else 100
            self.assertEqual(self.b.place_token(self.s, self.cid, "E6"), cost)
            self.assertEqual(self.c["cash"], 500 - 40 - cost)

    def test_offboard_values_follow_phase_and_train_type(self):
        for _ in self.networks():
            node = self.s["board"]["E6"]["nodes"][0]
            node["kind"] = "offboard"
            node["revenue"] = [30, 70, 100] if self.module is engine1889 else [30, 70]
            self.assertEqual(self.b.validate_routes(self.s, self.cid, [self.route]), 60)
            self.s["phase"] = "5"
            self.assertEqual(
                self.b.validate_routes(self.s, self.cid, [self.route]), 100
            )
            self.s["phase"] = "D"
            self.assertEqual(
                self.b.validate_routes(self.s, self.cid, [self.route]), 100
            )
            expected = 130 if self.module is engine1889 else 100
            self.assertEqual(
                self.b.validate_routes(
                    self.s, self.cid, [dict(self.route, train="D-0")]
                ),
                expected,
            )

    def test_station_preservation_rejects_overflow_duplicate_or_removed_track(self):
        for _ in self.networks():
            old = self.b.decode("city=revenue:10;path=a:0,b:_0", "yellow")
            old["tokens"][0] = [self.cid]
            new = self.b.decode(
                "city=revenue:20,slots:2;path=a:0,b:_0;path=a:1,b:_0", "green"
            )
            self.assertEqual(self.b.preserved_mapping(old, new), [0])
            new["paths"] = [["e1", "n0"]]
            self.assertIsNone(self.b.preserved_mapping(old, new))
            new["paths"] = [["e0", "n0"]]
            new["nodes"][0]["slots"] = 0
            self.assertIsNone(self.b.preserved_mapping(old, new))
            old["tokens"][0].append(self.cid)
            new["nodes"][0]["slots"] = 2
            self.assertIsNone(self.b.preserved_mapping(old, new))

    def test_closed_loop_does_not_create_a_connection_but_real_branch_does(self):
        # Reflect the known loop network and rotate its edges for flat 1889.
        # This tests real graph construction/traversal, without mocking either.
        for module, b, cid in (
            (engine1830, board1830, "C&O"),
            (engine1889, board1889, "IR"),
        ):
            with self.subTest(variant=module.__name__):
                f = loop_fixtures.loop_fixture()
                for coord, tile, rotation in (("G15", "8", 5), ("H16", "57", 2)):
                    f.s["board"][coord] = board1830.tile_for(tile, rotation)
                for connected in (False, True):
                    original = deepcopy(f.s["board"])
                    if connected:
                        original["F14"] = board1830.tile_for("27", 1)
                        original["F16"] = board1830.tile_for("57", 1)

                    def coord(c):
                        return (
                            c
                            if module is engine1830
                            else chr(ord("Z") - (ord(c[0]) - ord("A"))) + c[1:]
                        )

                    network = {}
                    for old_coord, tile in original.items():
                        tile["tokens"] = [
                            [cid if c == "C&O" else c for c in tokens]
                            for tokens in tile["tokens"]
                        ]
                        if module is engine1889:
                            tile["paths"] = [
                                [
                                    (
                                        "e" + str((int(v[1:]) + 2) % 6)
                                        if v.startswith("e")
                                        else v
                                    )
                                    for v in path
                                ]
                                for path in tile["paths"]
                            ]
                            for node in tile["nodes"]:
                                node["revenue"] = node["revenue"] + [
                                    node["revenue"][-1]
                                ]
                        network[coord(old_coord)] = tile
                    state = module.new_game(["A", "B", "C"])
                    state["board"] = network
                    state["corporations"][cid].update(cash=500, token_supply=4)
                    target = coord("F16" if connected else "H16")
                    reachable = b.reachable(network, cid)
                    self.assertEqual(target + ":n0" in reachable, connected)
                    candidates = b.route_candidates(state, cid, limit=1000)
                    self.assertEqual(
                        any(target + ":n0" in r["vertices"] for r in candidates),
                        connected,
                    )
                    if connected:
                        b.place_token(state, cid, target)
                        self.assertIn(cid, state["board"][target]["tokens"][0])
                    else:
                        with self.assertRaisesRegex(module.RuleError, "reachable"):
                            b.place_token(state, cid, target)
