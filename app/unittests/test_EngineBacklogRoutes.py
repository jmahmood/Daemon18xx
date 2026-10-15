"""Independent cyclic and recorded-board optima (BACKLOG-19 and 26)."""

import json
import subprocess
import sys
import time
import tracemalloc
import unittest
from copy import deepcopy
from itertools import combinations_with_replacement
from pathlib import Path

from app import engine1889
from app.engine1889 import engine as E
from app.unittests.route_oracle import best_revenue


def dense_report():
    record = json.loads((Path(__file__).parent / "fixtures/1889/962.json").read_text())
    base = engine1889.replay(
        record["names"], record["actions"][:471], record["player_ids"]
    )
    report = []
    for phase, kinds in (
        ("5", ("3", "4", "5")),
        ("6", ("4", "5", "6")),
        ("D", ("5", "6", "D")),
    ):
        for mix in combinations_with_replacement(kinds, 2):
            state = deepcopy(base)
            cid = "TR"
            if phase != "5":
                E._phase_change(state, "6")
                if phase == "D":
                    E._phase_change(state, "D")
            # Controlled train/phase projections of the recorded board, not
            # independent complete phase-6/D game histories.
            for tid in list(state["corporations"][cid]["trains"]):
                state["trains"][tid].update(owner="depot", used=True)
            state["corporations"][cid]["trains"] = []
            if mix == ("D", "D"):
                state["trains"]["D-1"] = dict(state["trains"]["D-0"], id="D-1")
            for kind in mix:
                tid = next(
                    t
                    for t, train in state["trains"].items()
                    if train["type"] == kind
                    and train["owner"] != cid
                    and not train["rusted"]
                )
                owner = state["trains"][tid]["owner"]
                if owner in state["corporations"]:
                    state["corporations"][owner]["trains"].remove(tid)
                state["trains"][tid]["owner"] = cid
                state["corporations"][cid]["trains"].append(tid)
            if phase == "D" and not any(
                t["type"] == "D" and t["owner"] == "depot"
                for t in state["trains"].values()
            ):
                # Unlimited supply retains a fresh Diesel after each purchase.
                tid = "D-" + str(
                    sum(t["type"] == "D" for t in state["trains"].values())
                )
                state["trains"][tid] = dict(
                    state["trains"]["D-0"], id=tid, owner="depot"
                )
            engine1889.validate_state(state)
            tracemalloc.start()
            start = time.monotonic()
            expected = best_revenue(state, cid)
            actual = engine1889.best_routes(state, cid)
            elapsed = time.monotonic() - start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert actual["revenue"] == expected, (phase, expected, actual)
            reordered = deepcopy(state)
            reordered["board"] = dict(reversed(list(reordered["board"].items())))
            assert engine1889.best_routes(reordered, cid) == actual
            report.append(
                dict(
                    phase=phase,
                    trains=list(mix),
                    revenue=expected,
                    seconds=elapsed,
                    peak_bytes=peak,
                    laid_tiles=sum(
                        t["tile"] is not None for t in state["board"].values()
                    ),
                )
            )
    return report


class BacklogRouteTests(unittest.TestCase):
    def network(self, kind):
        s = engine1889.new_game(list("ABC"))
        b = E.topology
        s["board"] = {c: b.decode("", "white") for c in s["board"]}
        specs = {
            "E2": (10, (0,)),
            "E4": (20, (0, 2, 3)),
            "E6": (50, (2, 3)),
            "D5": (80, (3, 5)),
            "D3": (40, (0, 5)),
            "F5": (60, (2,)),
            "I8": (500, (0,)),
            "I10": (500, (0, 3)),
            "I12": (500, (3,)),
        }
        for coord, (value, exits) in specs.items():
            tile = b.decode(
                "city=revenue:%d;" % value
                + ";".join("path=a:%d,b:_0" % e for e in exits),
                "yellow",
            )
            s["board"][coord] = tile
        s["board"]["E2"]["tokens"][0] = ["IR"]
        if kind == "ring":
            s["board"]["D5"]["tokens"][0] = ["IR"]
        elif kind == "junction":
            s["board"]["E4"] = b.decode("path=a:3,b:0;path=a:3,b:2", "green")
        else:
            s["board"]["E4"] = b.decode("path=a:3,b:0;path=a:2,b:5", "green")
        trains = (
            ("3-0", "3-1")
            if kind == "ring"
            else (("3-0",) if kind == "junction" else ("5-0",))
        )
        s["corporations"]["IR"]["trains"] = list(trains)
        for t in trains:
            s["trains"][t]["owner"] = "IR"
        return s

    def test_cyclic_junction_and_crossing_optima_against_independent_oracle(self):
        for kind, gold in (("ring", 290), ("junction", 140), ("crossing", 240)):
            with self.subTest(network=kind):
                state = self.network(kind)
                before = deepcopy(state)
                self.assertEqual(best_revenue(state, "IR"), gold)
                result = engine1889.best_routes(state, "IR")
                self.assertEqual(result["revenue"], gold)
                self.assertEqual(
                    E.topology.validate_routes(state, "IR", result["routes"]), gold
                )
                self.assertEqual(state, before)
        state = self.network("crossing")
        state["board"]["D5"]["tokens"][0] = ["AR"]
        self.assertEqual(best_revenue(state, "IR"), 140)
        self.assertEqual(engine1889.best_routes(state, "IR")["revenue"], 140)

    def test_recorded_late_board_exact_optima_with_bounded_resources(self):
        # 60s for the batch, 30s and 128 MiB peak traced Python allocations
        # per position; no approximate fallback on timeout or exhaustion.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json; from app.unittests.test_EngineBacklogRoutes import dense_report; print(json.dumps(dense_report()))",
            ],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            [r["phase"] for r in report], ["5"] * 6 + ["6"] * 6 + ["D"] * 6
        )
        self.assertEqual(
            [r["revenue"] for r in report],
            [
                340,
                390,
                430,
                430,
                470,
                510,
                430,
                470,
                510,
                510,
                550,
                580,
                510,
                550,
                630,
                580,
                650,
                650,
            ],
        )
        for entry in report:
            self.assertGreaterEqual(entry["laid_tiles"], 27)
            self.assertLess(entry["peak_bytes"], 128 * 1024 * 1024)
            self.assertLess(entry["seconds"], 30)
            self.assertGreater(entry["revenue"], 0)
