"""Exercise the actual ASGI router, authentication, persistence, and concurrency."""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "multiplayer" / "backend"


class Rules1830APITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        sys.path.insert(0, str(BACKEND))
        try:
            from server import app
            from database import db
        except ImportError as error:
            self.skipTest("Multiplayer dependencies required: %s" % error)
        self.app, self.db = app, db
        self.directory = tempfile.TemporaryDirectory()
        self.original_path = db.db_path
        db.db_path = Path(self.directory.name) / "games.sqlite"
        await db.initialize()
        status, self.room = await self.request(
            "POST", "/api/1830/games", {"max_players": 3}
        )
        self.assertEqual(status, 200)
        self.path = "/api/1830/games/" + self.room["room_code"]

    async def asyncTearDown(self):
        if hasattr(self, "original_path"):
            self.db.db_path = self.original_path
            self.directory.cleanup()
        if str(BACKEND) in sys.path:
            sys.path.remove(str(BACKEND))

    async def request(self, method, path, data=None, token=None):
        messages = []
        headers = [(b"content-type", b"application/json")]
        if token:
            headers.append((b"authorization", ("Bearer " + token).encode()))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 5000),
            "server": ("127.0.0.1", 8000),
        }
        delivered = False

        async def receive():
            nonlocal delivered
            if delivered:
                await asyncio.sleep(0)
                return {"type": "http.disconnect"}
            delivered = True
            return {
                "type": "http.request",
                "body": json.dumps(data).encode() if data is not None else b"",
                "more_body": False,
            }

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        status = next(
            m["status"] for m in messages if m["type"] == "http.response.start"
        )
        body = b"".join(
            m.get("body", b"") for m in messages if m["type"] == "http.response.body"
        )
        return status, json.loads(body) if body else None

    async def start(self):
        status, result = await self.request(
            "POST",
            self.path + "/start",
            {"player_names": ["Alice", "Bob", "Carol"]},
            self.room["creator_token"],
        )
        self.assertEqual(status, 200, result)
        return result

    async def test_malformed_hex_rejected_without_persistence(self):
        await self.start()
        from app.unittests import test_Engine1830 as fixtures

        fixture = fixtures.Rules1830Tests("runTest")
        fixture.setUp()
        fixture.operating("B&O")
        game = await self.db.get_game_by_room_code(self.room["room_code"])
        await self.db.save_rules_state(game["id"], fixture.s, 0)
        # Reach the operating-round board lookup that originally raised TypeError.
        # An auction-only request would reject the action before inspecting hex.
        initial = fixture.s
        for coord in ([], {}, 7, None):
            with self.subTest(hex=coord):
                status, result = await self.request(
                    "POST",
                    self.path + "/actions",
                    {
                        "expected_action_id": initial["revision"],
                        "action": {"type": "lay_tile", "hex": coord, "tile": "57"},
                    },
                    self.room["player_tokens"][2],
                )
                self.assertEqual(status, 422, result)
                status, current = await self.request(
                    "GET", self.path, token=self.room["player_tokens"][0]
                )
                self.assertEqual(status, 200)
                self.assertEqual(current["state"], initial)

    async def test_start_and_authenticated_state_no_tokens(self):
        result = await self.start()
        self.assertEqual(result["state"]["round"], "auction")
        self.assertEqual(len(result["state"]["corporations"]), 8)
        for token in [
            self.room["creator_token"],
            self.room["spectator_token"],
        ] + self.room["player_tokens"]:
            status, read = await self.request("GET", self.path, token=token)
            self.assertEqual(status, 200)
            self.assertNotIn(token, json.dumps(read))
        status, _ = await self.request("GET", self.path)
        self.assertEqual(status, 401)
        status, _ = await self.request("GET", self.path, token="wrong")
        self.assertEqual(status, 403)
        status, _ = await self.request("GET", "/api/games/" + self.room["room_code"])
        self.assertEqual(status, 404)

    async def test_only_creator_starts_and_cannot_restart(self):
        status, _ = await self.request(
            "POST",
            self.path + "/start",
            {"player_names": ["A", "B", "C"]},
            self.room["player_tokens"][0],
        )
        self.assertEqual(status, 403)
        await self.start()
        status, _ = await self.request(
            "POST",
            self.path + "/start",
            {"player_names": ["A", "B", "C"]},
            self.room["creator_token"],
        )
        self.assertEqual(status, 409)

    async def test_actions_persist_and_reject_impersonation_stale_and_illegal_moves(
        self,
    ):
        await self.start()
        payload = {
            "expected_action_id": 0,
            "action": {"type": "buy_private", "company": "SV"},
        }
        status, result = await self.request(
            "POST", self.path + "/actions", payload, self.room["player_tokens"][0]
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["state"]["revision"], 1)
        for token in (self.room["creator_token"], self.room["spectator_token"]):
            status, _ = await self.request(
                "POST", self.path + "/actions", payload, token
            )
            self.assertEqual(status, 403)
        status, _ = await self.request(
            "POST", self.path + "/actions", payload, self.room["player_tokens"][0]
        )
        self.assertEqual(status, 409)
        payload = {
            "expected_action_id": 1,
            "action": {"type": "buy_private", "company": "CS", "player": "p1"},
        }
        status, _ = await self.request(
            "POST", self.path + "/actions", payload, self.room["player_tokens"][1]
        )
        self.assertEqual(status, 403)
        payload["action"].pop("player")
        status, result = await self.request(
            "POST", self.path + "/actions", payload, self.room["player_tokens"][0]
        )
        self.assertEqual(status, 422, result)
        game = await self.db.get_game_by_room_code(self.room["room_code"])
        snapshot = await self.db.get_latest_game_state(game["id"])
        self.assertEqual(snapshot["move_number"], 1)

    async def test_concurrent_compare_and_append_allows_one_writer(self):
        result = await self.start()
        game = await self.db.get_game_by_room_code(self.room["room_code"])
        from app.engine1830 import apply_action

        state = apply_action(result["state"], {"type": "pass", "player": "p1"})
        outcomes = await asyncio.gather(
            self.db.save_rules_state(game["id"], state, 0),
            self.db.save_rules_state(game["id"], state, 0),
            return_exceptions=True,
        )
        self.assertEqual(sum(isinstance(o, ValueError) for o in outcomes), 1)
        self.assertEqual(sum(o is None for o in outcomes), 1)

    async def test_room_size_and_start_names_validation(self):
        status, _ = await self.request("POST", "/api/1830/games", {"max_players": 7})
        self.assertEqual(status, 422)
        status, _ = await self.request(
            "POST",
            self.path + "/start",
            {"player_names": ["A", "B"]},
            self.room["creator_token"],
        )
        self.assertEqual(status, 422)

    async def test_complete_recorded_game_over_authenticated_http(self):
        fixture = Path(__file__).with_name("fixtures") / "29133.json"
        record = json.loads(fixture.read_text())
        status, room = await self.request(
            "POST", "/api/1830/games", {"max_players": len(record["names"])}
        )
        self.assertEqual(status, 200)
        path = "/api/1830/games/" + room["room_code"]
        status, _ = await self.request(
            "POST",
            path + "/start",
            {"player_names": record["names"]},
            room["creator_token"],
        )
        self.assertEqual(status, 200)
        ids = {old: "p" + str(i + 1) for i, old in enumerate(record["player_ids"])}
        tokens = {
            ids[old]: room["player_tokens"][i]
            for i, old in enumerate(record["player_ids"])
        }
        result = None
        for revision, original in enumerate(record["actions"]):
            action = dict(original)
            for key in ("player", "seller", "buyer"):
                if key in action:
                    action[key] = ids.get(action[key], action[key])
            status, result = await self.request(
                "POST",
                path + "/actions",
                {"expected_action_id": revision, "action": action},
                tokens[action["player"]],
            )
            self.assertEqual(status, 200, (revision, action, result))
        self.assertTrue(result["state"]["finished"])
        self.assertEqual(
            result["state"]["result"],
            {ids[p]: value for p, value in record["result"].items()},
        )
        self.assertEqual(result["state"]["end_reason"], "bankruptcy")
        status, restored = await self.request(
            "GET", path, token=room["spectator_token"]
        )
        self.assertEqual(status, 200)
        self.assertEqual(restored, result)
        status, _ = await self.request(
            "POST",
            path + "/actions",
            {
                "expected_action_id": result["state"]["revision"],
                "action": {"type": "pass"},
            },
            room["player_tokens"][0],
        )
        self.assertEqual(status, 422)
