"""Whole games driven solely through the public transition API."""

import json
import unittest

from app.engine1830 import new_game, apply_action, replay, check_invariants
from app.engine1830.engine import price


def play_bank_game():
    state = new_game(["Alice", "Bob", "Carol"])

    def act(action_type, **args):
        nonlocal state
        actor = state["current_player"]
        state = apply_action(state, dict(type=action_type, player=actor, **args))

    for company in ("SV", "CS", "DH", "MH", "CA", "BO"):
        act("buy_private", company=company)
        if state["pending_par"] is not None:
            state = apply_action(
                state, {"type": "par", "player": state["pending_par"], "price": 100}
            )
    bought = 0
    for _ in range(100):
        if state["round"] == "operating":
            break
        if state["current_player"] == "p3" and bought < 4:
            act("buy_shares", corporation="B&O")
            bought += 1
            act("end_turn")
        else:
            act("pass")
    assert state["round"] == "operating" and state["current_corporation"] == "B&O"
    iterations = 0
    while not state["finished"]:
        iterations += 1
        assert iterations < 2000, "Game failed to terminate"
        if state["round"] == "stock":
            act("pass")
            continue
        step = state["operating_turn"]["step"]
        if step == "track":
            if not state["board"]["J14"]["tile"]:
                act("lay_tile", hex="J14", tile="57", rotation=0)
            else:
                act("skip")
        elif step == "token":
            act("skip")
        elif step == "routes":
            if state["corporations"]["B&O"]["trains"]:
                act(
                    "run_routes",
                    routes=[{"train": "2-0", "paths": [["I15", 1], ["J14", 1]]}],
                )
            else:
                act("skip")
        elif step == "dividend":
            act("dividend", kind="payout")
        elif step == "train":
            if not state["corporations"]["B&O"]["trains"]:
                act("buy_train", train="2-0")
            else:
                act("end_turn")
        else:
            raise AssertionError(step)
    return state


class FullGame1830Tests(unittest.TestCase):
    def test_initial_auction_through_bank_exhaustion_and_final_scoring(self):
        state = play_bank_game()
        self.assertTrue(state["finished"])
        self.assertEqual(state["end_reason"], "bank")
        self.assertLessEqual(state["bank"], 0)
        self.assertGreater(state["stock_round"], 20)
        self.assertEqual(state["operating_turn"]["step"], "train")
        self.assertEqual(
            state["result"],
            {
                p["id"]: p["cash"]
                + sum(
                    price(c) * c["holdings"][p["id"]] // 10
                    for c in state["corporations"].values()
                )
                + sum(
                    private["value"]
                    for private in state["privates"].values()
                    if not private["closed"] and private["owner"] == p["id"]
                )
                for p in state["players"].values()
            },
        )
        check_invariants(state)
        serialized = json.dumps(state)
        self.assertEqual(json.loads(serialized), state)
        self.assertEqual(replay(["Alice", "Bob", "Carol"], state["history"]), state)


class RecordedGame1830Tests(unittest.TestCase):
    def test_recorded_games_match_independent_final_scores(self):
        from pathlib import Path
        from app.engine1830 import replay

        folder = Path(__file__).with_name("fixtures")
        paths = sorted(folder.glob("*.json"))
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(game=path.name):
                record = json.loads(path.read_text())
                state = replay(record["names"], record["actions"], record["player_ids"])
                self.assertTrue(state["finished"])
                self.assertEqual(state["result"], record["result"])
                self.assertEqual(state["end_reason"], record["end_reason"])
                self.assertEqual(state["revision"], len(record["actions"]))
                self.assertEqual(json.loads(json.dumps(state)), state)
                self.assertEqual(
                    [entry for entry in state["log"] if entry.startswith("Phase ")],
                    ["Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase D"],
                )
