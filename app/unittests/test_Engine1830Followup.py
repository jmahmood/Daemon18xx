"""Regression coverage for loop connectivity and M&H operating control."""

import unittest
from copy import deepcopy

from app.engine1830 import validate_state
from app.engine1830 import board as B, engine as E
from app.unittests import test_Engine1830 as fixtures
from app.unittests import test_Engine1830API as api_fixtures


def fixture():
    result = fixtures.Rules1830Tests("runTest")
    result.setUp()
    return result


def loop_fixture():
    f = fixture()
    f.operating("C&O")
    f.s["phase"] = "3"
    f.s["privates"]["SV"]["owner"] = "C&O"
    # Controlled existing railhead: H12 (Columbus), plus the usual Cleveland base.
    f.s["board"]["H12"]["tokens"][0] = ["C&O"]
    for coord, tile, rotation in (
        ("H14", "7", 1),
        ("G13", "9", 2),
        ("F12", "8", 3),
        ("E13", "7", 5),
        ("F14", "7", 1),
        ("F12", "28", 5),
        ("G13", "24", 2),
    ):
        B.lay_tile(f.s, "C&O", coord, tile, rotation)
    validate_state(f.s)
    return f


def exchange_fixture():
    f = fixture()
    f.stock()
    # Entire prefix uses public actions: p2 starts NYC; p1 and p3 buy 20% each.
    f.act("pass")
    f.act("buy_shares", corporation="NYC", price=100)
    f.act("end_turn")
    for purchase in (True, True, False, True, True):
        if purchase:
            f.act("buy_shares", corporation="NYC")
            f.act("end_turn")
        else:
            f.act("pass")
    for _ in range(3):
        f.act("pass")
    assert f.s["round"] == "operating"
    assert f.s["current_corporation"] == "NYC"
    assert f.s["current_player"] == "p2"
    validate_state(f.s)
    return f


class FollowupRegressions(unittest.TestCase):
    def test_closed_loop_cannot_make_disconnected_construction_legal(self):
        f = loop_fixture()
        f.reject("lay_tile", hex="G15", tile="8", rotation=5)

    def test_closed_loop_cannot_make_disconnected_token_legal(self):
        f = loop_fixture()
        # Isolate station placement even if the construction check is corrected.
        for coord, tile, rotation in (("G15", "8", 5), ("H16", "57", 2)):
            f.s["board"][coord] = B.tile_for(tile, rotation)
            f.s["tiles"][tile] -= 1
        validate_state(f.s)
        self.assertFalse(
            any(
                "H16:n0" in r["vertices"]
                for r in B.route_candidates(f.s, "C&O", limit=1000)
            )
        )
        f.reject("place_token", hex="H16")

    def test_loop_does_not_block_a_genuine_connection(self):
        f = loop_fixture()
        B.lay_tile(f.s, "C&O", "F14", "27", 1)
        f.s["privates"]["DH"]["owner"] = "C&O"
        f.act("lay_tile", hex="F16", tile="57", rotation=1)
        self.assertTrue(
            any(
                "F16:n0" in r["vertices"]
                for r in B.route_candidates(f.s, "C&O", limit=1000)
            )
        )
        f.act("place_token", hex="F16")
        self.assertIn("C&O", f.s["board"]["F16"]["tokens"][0])

    def test_mh_transfer_of_another_company_preserves_current_turn(self):
        for future in (False, True):
            with self.subTest(nyc_will_operate=future):
                f = fixture()
                f.stock()
                for player in (("p2", "p1", "p3") if future else ("p2", "p1")):
                    f.shares("NYC", player, 20)
                co = f.shares("C&O", "p3", 60)
                E._market_move(f.s, co, "right")
                f.s["or_number"] = 1
                E._start_operating(f.s)
                before = deepcopy(f.s)
                f.act("exchange_private", player="p1")
                self.assertEqual(f.s["corporations"]["NYC"]["president"], "p1")
                self.assertEqual(f.s["current_corporation"], "C&O")
                self.assertEqual(f.s["current_player"], "p3")
                self.assertEqual(f.s["operating_turn"], before["operating_turn"])
                f.act("dividend", kind="withhold")
                f.act("end_turn")
                if future:
                    self.assertEqual(f.s["current_corporation"], "NYC")
                    self.assertEqual(f.s["current_player"], "p1")

    def test_mh_presidency_transfer_hands_operating_turn_to_new_president(self):
        f = exchange_fixture()
        before = deepcopy(f.s)
        f.act("exchange_private", player="p1")
        self.assertEqual(f.s["corporations"]["NYC"]["president"], "p1")
        self.assertEqual(f.s["operating_turn"], before["operating_turn"])
        self.assertEqual(f.s["or_order"], before["or_order"])
        self.assertEqual(f.s["or_index"], before["or_index"])
        self.assertEqual(f.s["bank"], before["bank"])
        self.assertEqual(
            f.s["corporations"]["NYC"]["cash"], before["corporations"]["NYC"]["cash"]
        )
        self.assertEqual(f.s["board"], before["board"])
        # The new president must be able to continue the already scheduled turn.
        f.act("skip", player="p1")
        self.assertEqual(f.s["operating_turn"]["step"], "token")


class HTTPFollowupRegression(unittest.IsolatedAsyncioTestCase):
    async def test_mh_exchange_can_continue_over_http(self):
        http = api_fixtures.Rules1830APITests("runTest")
        await http.asyncSetUp()
        try:
            await http.start()
            f = exchange_fixture()
            game = await http.db.get_game_by_room_code(http.room["room_code"])
            await http.db.save_rules_state(game["id"], f.s, 0)
            status, exchanged = await http.request(
                "POST",
                http.path + "/actions",
                {
                    "expected_action_id": f.s["revision"],
                    "action": {"type": "exchange_private"},
                },
                http.room["player_tokens"][0],
            )
            self.assertEqual(status, 200, exchanged)
            revision = exchanged["state"]["revision"]
            status, result = await http.request(
                "POST",
                http.path + "/actions",
                {"expected_action_id": revision, "action": {"type": "skip"}},
                http.room["player_tokens"][0],
            )
            self.assertEqual(status, 200, result)
        finally:
            await http.asyncTearDown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
