"""Authenticated 1889 HTTP actions, legacy isolation and full SQLite game replay."""

import unittest
import json
from pathlib import Path
from app.unittests import test_Engine1830API as api_fixtures
from app.unittests import test_Engine1889 as fixtures
from app.engine1889 import new_game, apply_action


class Rules1889APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.http = api_fixtures.Rules1830APITests("runTest")
        await self.http.asyncSetUp()
        self.legacy_1830_room = self.http.room
        self.legacy_1830_path = self.http.path
        await self.room(3)

    async def asyncTearDown(self):
        await self.http.asyncTearDown()

    async def room(self, count):
        status, info = await self.http.request(
            "POST", "/api/1889/games", {"max_players": count}
        )
        self.assertEqual(status, 200, info)
        self.http.room = info
        self.http.path = "/api/1889/games/" + info["room_code"]

    async def start(self, names=None):
        h = self.http
        status, result = await h.request(
            "POST",
            h.path + "/start",
            {"player_names": names or ["Alice", "Bob", "Carol"]},
            h.room["creator_token"],
        )
        self.assertEqual(status, 200, result)
        return result

    async def test_authentication_variant_and_legacy_room_isolation(self):
        h = self.http
        await self.start()
        for token in [h.room["creator_token"], h.room["spectator_token"]] + h.room[
            "player_tokens"
        ]:
            status, result = await h.request("GET", h.path, token=token)
            self.assertEqual(status, 200)
            self.assertEqual(result["state"]["variant"], "1889")
            self.assertNotIn(token, json.dumps(result))
        for token, expected in (
            (None, 401),
            ("wrong", 403),
            (self.legacy_1830_room["player_tokens"][0], 403),
        ):
            status, _ = await h.request("GET", h.path, token=token)
            self.assertEqual(status, expected)
        status, _ = await h.request("GET", "/api/games/" + h.room["room_code"])
        self.assertEqual(status, 404)
        status, _ = await h.request(
            "GET", h.path.replace("/1889/", "/1830/"), token=h.room["player_tokens"][0]
        )
        self.assertEqual(status, 404)
        status, _ = await h.request("POST", "/api/games/create", {"max_players": 3})
        self.assertEqual(status, 404)
        legacy = await h.db.create_game(variant="1889", max_players=3, engine="legacy")
        status, _ = await h.request(
            "GET",
            "/api/1889/games/" + legacy["room_code"],
            token=h.room["player_tokens"][0],
        )
        self.assertEqual(status, 404)
        for token in (h.room["spectator_token"], h.room["creator_token"]):
            status, _ = await h.request(
                "POST",
                h.path + "/actions",
                {"expected_action_id": 0, "action": {"type": "pass"}},
                token,
            )
            self.assertEqual(status, 403)
        status, _ = await h.request(
            "POST",
            h.path + "/start",
            {"player_names": ["A", "B", "C"]},
            h.room["creator_token"],
        )
        self.assertEqual(status, 409)

    async def test_rejected_stale_impersonated_actions_and_concurrent_writers(self):
        h = self.http
        initial = await self.start()
        token = h.room["player_tokens"][0]
        for action, status_expected in (
            ({"type": "lay_tile", "hex": [], "tile": "5"}, 422),
            ({"type": "pass", "player": "p2"}, 403),
        ):
            status, _ = await h.request(
                "POST",
                h.path + "/actions",
                {"expected_action_id": 0, "action": action},
                token,
            )
            self.assertEqual(status, status_expected)
        status, current = await h.request("GET", h.path, token=token)
        self.assertEqual(current, initial)
        import asyncio

        payload = {
            "expected_action_id": 0,
            "action": {"type": "buy_private", "company": "TR"},
        }
        replies = await asyncio.gather(
            *[h.request("POST", h.path + "/actions", payload, token) for _ in range(2)]
        )
        self.assertEqual(sorted(status for status, _ in replies), [200, 409])
        status, _ = await h.request("POST", h.path + "/actions", payload, token)
        self.assertEqual(status, 409)

    async def test_ehime_interrupt_rejects_corporation_actor_and_resumes(self):
        h = self.http
        await self.start()
        f = fixtures.Rules1889Tests("runTest")
        f.setUp()
        f.operating()
        f.s["phase"] = "3"
        f.act(
            "offer",
            player="p3",
            kind="private",
            item="ER",
            seller="p3",
            buyer="IR",
            price=40,
        )
        game = await h.db.get_game_by_room_code(h.room["room_code"])
        await h.db.save_rules_state(game["id"], f.s, 0)
        revision = f.s["revision"]
        status, view = await h.request(
            "POST",
            h.path + "/actions",
            {
                "expected_action_id": revision,
                "action": {
                    "type": "buy_private",
                    "company": "ER",
                    "buyer": "IR",
                    "price": 40,
                },
            },
            h.room["player_tokens"][0],
        )
        self.assertEqual(status, 200, view)
        self.assertEqual(view["state"]["current_player"], "p3")
        revision = view["state"]["revision"]
        action = {
            "type": "lay_tile",
            "hex": "C4",
            "tile": "14",
            "rotation": 1,
            "special": "ER",
        }
        status, _ = await h.request(
            "POST",
            h.path + "/actions",
            {"expected_action_id": revision, "action": action},
            h.room["player_tokens"][0],
        )
        self.assertEqual(status, 422)
        status, view = await h.request(
            "POST",
            h.path + "/actions",
            {"expected_action_id": revision, "action": action},
            h.room["player_tokens"][2],
        )
        self.assertEqual(status, 200, view)
        self.assertEqual(view["state"]["current_player"], "p1")
        self.assertFalse(view["state"]["operating_turn"]["laid"])

    async def test_catalog_start_authority_and_legacy_database_migration(self):
        h = self.http
        status, catalog = await h.request("GET", "/api/1889/catalog")
        self.assertEqual(status, 200)
        self.assertEqual(catalog["layout"], "flat")
        self.assertEqual(catalog["currency"], "JPY")
        self.assertEqual(len(catalog["hexes"]), 52)
        self.assertEqual(catalog["par_prices"], [65, 70, 75, 80, 90, 100])
        status, _ = await h.request(
            "POST",
            h.path + "/start",
            {"player_names": ["A", "B", "C"]},
            h.room["player_tokens"][0],
        )
        self.assertEqual(status, 403)
        import sqlite3

        old_path = Path(h.directory.name) / "legacy.sqlite"
        with sqlite3.connect(old_path) as conn:
            conn.execute("""CREATE TABLE games (
                id INTEGER PRIMARY KEY, room_code TEXT UNIQUE, variant TEXT, status TEXT,
                creator_token TEXT, spectator_token TEXT, max_players INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.execute(
                "INSERT INTO games (room_code,variant,status,max_players) VALUES ('OLD','1889','waiting',3)"
            )
        database = type(h.db)(old_path)
        await database.initialize()
        await database.initialize()
        old = await database.get_game_by_room_code("OLD")
        self.assertEqual(old["engine"], "legacy")
        info = await database.create_game(
            variant="1889", max_players=3, engine="python"
        )
        new = await database.get_game_by_room_code(info["room_code"])
        self.assertEqual(new["engine"], "python")
        self.assertEqual(old["variant"], new["variant"])

    async def test_complete_recorded_game_http_exact_scores_and_reload(self):
        record = json.loads(
            (Path(__file__).parent / "fixtures" / "1889" / "962.json").read_text()
        )
        await self.room(4)
        h = self.http
        await self.start(record["names"])
        mapping = {old: "p" + str(i + 1) for i, old in enumerate(record["player_ids"])}
        state = new_game(record["names"])
        for revision, original in enumerate(record["actions"]):
            action = dict(original)
            for field in ("player", "buyer", "seller"):
                if field in action:
                    action[field] = mapping.get(action[field], action[field])
            player = action["player"]
            token = h.room["player_tokens"][int(player[1:]) - 1]
            status, result = await h.request(
                "POST",
                h.path + "/actions",
                {"expected_action_id": revision, "action": action},
                token,
            )
            self.assertEqual(status, 200, (revision, action, result))
            # Reconstruct independently through the Python library after each persisted action.
            state = apply_action(state, dict(action, expected_action_id=revision))
            self.assertEqual(result["state"], state)
            if revision == len(record["actions"]) // 2:
                status, restored = await h.request(
                    "GET", h.path, token=h.room["spectator_token"]
                )
                self.assertEqual(status, 200)
                self.assertEqual(restored["state"], state)
        self.assertTrue(state["finished"])
        self.assertEqual(
            state["result"],
            {mapping[p]: score for p, score in record["result"].items()},
        )
        status, restored = await h.request(
            "GET", h.path, token=h.room["spectator_token"]
        )
        self.assertEqual(restored["state"], state)
        self.assertEqual(restored["state"]["end_reason"], "bank")
