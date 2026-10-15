"""Real HTTP/SQLite and independent-process regressions for the backlog."""

import asyncio
import json
import sqlite3
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from app import engine1889
from app.engine1889 import engine as E
from app.unittests import test_Engine1830API as api
from app.unittests import test_EngineBacklog1889 as rule_fixtures


def worker():
    """Run one authenticated request in an independent ASGI/SQLite process."""
    from backend.server import app
    from backend.database import db

    request = json.loads(sys.stdin.readline())
    db.db_path = Path(request["database"])
    original = db.save_rules_state

    async def save(*args, **kwargs):
        print("READY", flush=True)
        await asyncio.get_running_loop().run_in_executor(None, sys.stdin.readline)
        return await original(*args, **kwargs)

    db.save_rules_state = save
    h = api.Rules1830APITests("runTest")
    h.app = app
    status, body = asyncio.run(
        h.request("POST", request["path"], request["data"], request["token"])
    )
    print(json.dumps(dict(status=status, body=body)), flush=True)


class BacklogHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = api.Rules1830APITests("runTest")
        await self.h.asyncSetUp()

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def room(self, variant, start=True):
        status, self.info = await self.h.request(
            "POST", "/api/" + variant + "/games", dict(max_players=3)
        )
        self.assertEqual(status, 200, self.info)
        self.path = "/api/" + variant + "/games/" + self.info["room_code"]
        if start:
            status, view = await self.h.request(
                "POST",
                self.path + "/start",
                dict(player_names=list("ABC")),
                self.info["creator_token"],
            )
            self.assertEqual(status, 200, view)
            return view["state"]

    async def action(self, revision, kind, player="p1", **fields):
        return await self.h.request(
            "POST",
            self.path + "/actions",
            dict(expected_action_id=revision, action=dict(type=kind, **fields)),
            self.info["player_tokens"][int(player[1:]) - 1],
        )

    async def test_malformed_saved_json_and_lifecycle_return_conflict_without_append(
        self,
    ):
        import aiosqlite

        for variant in ("1830", "1889"):
            for corruption in (
                "json",
                "array",
                "null",
                "scalar",
                "structure",
                "phase",
                "round",
            ):
                state = await self.room(variant)
                game = await self.h.db.get_game_by_room_code(self.info["room_code"])
                if corruption == "json":
                    raw = "{bad json"
                elif corruption == "array":
                    raw = "[]"
                elif corruption == "null":
                    raw = "null"
                elif corruption == "scalar":
                    raw = "42"
                elif corruption == "structure":
                    raw = "{}"
                else:
                    state[corruption] = "unknown"
                    raw = json.dumps(state)
                async with aiosqlite.connect(self.h.db.db_path) as connection:
                    await connection.execute(
                        "UPDATE game_states SET state_json=? WHERE game_id=?",
                        (raw, game["id"]),
                    )
                    await connection.commit()
                status, _ = await self.h.request(
                    "GET", self.path, token=self.info["spectator_token"]
                )
                self.assertEqual(status, 409, (variant, corruption))
                status, _ = await self.action(0, "pass")
                self.assertEqual(status, 409)
                saved = await self.h.db.get_latest_game_state(game["id"])
                self.assertEqual(saved["state_json"], raw)
                self.assertEqual(saved["move_number"], 0)

    async def test_boolean_and_float_revisions_are_not_coerced_over_http(self):
        for variant in ("1830", "1889"):
            state = await self.room(variant)
            for value in (False, True, 0.0, 0.5, "0", -1):
                status, _ = await self.action(value, "pass")
                self.assertEqual(status, 422, (variant, value))
            status, view = await self.h.request(
                "GET", self.path, token=self.info["spectator_token"]
            )
            self.assertEqual(view["state"], state)
            status, _ = await self.action(0, "pass")
            self.assertEqual(status, 200)

    async def test_bankruptcy_after_reordered_restore_matches_library(self):
        await self.room("1889")
        f = rule_fixtures.Backlog1889Tests("runTest").fixture()
        f.route()
        f.train_step()
        f.cash(f.s["corporations"]["IR"], 0)
        for player in f.s["players"].values():
            f.cash(player, 0)
        E._position(f.s, f.s["corporations"]["IR"], [10, 0])
        for cid in ("AR", "SR"):
            f.shares(cid, "p1", 30)
            E._position(f.s, f.s["corporations"][cid], [9, 0])
        action = dict(type="bankrupt", player="p1", expected_action_id=f.s["revision"])
        expected = engine1889.apply_action(f.s, action)
        stored = deepcopy(f.s)
        stored["corporations"] = dict(reversed(list(stored["corporations"].items())))
        game = await self.h.db.get_game_by_room_code(self.info["room_code"])
        await self.h.db.save_rules_state(game["id"], stored, 0)
        status, view = await self.action(stored["revision"], "bankrupt")
        self.assertEqual(status, 200, view)
        self.assertEqual(view["state"], expected)
        status, view = await self.h.request(
            "GET", self.path, token=self.info["spectator_token"]
        )
        self.assertEqual(view["state"], expected)

    async def test_dougo_last_ipo_and_pool_rejection_persist_atomically(self):
        for last_share in (False, True):
            await self.room("1889")
            f = rule_fixtures.Backlog1889Tests("runTest").fixture(False)
            for player in ("p1", "p2", "p3"):
                f.shares("IR", player, 30)
            if not last_share:
                f.s["corporations"]["IR"].update(ipo=0, pool=10)
            game = await self.h.db.get_game_by_room_code(self.info["room_code"])
            await self.h.db.save_rules_state(game["id"], f.s, 0)
            status, view = await self.action(
                f.s["revision"], "exchange_private", player="p2"
            )
            self.assertEqual(status, 200 if last_share else 422)
            status, view = await self.h.request(
                "GET", self.path, token=self.info["spectator_token"]
            )
            if last_share:
                self.assertEqual(view["state"]["corporations"]["IR"]["ipo"], 0)
                self.assertTrue(view["state"]["privates"]["DR"]["closed"])
            else:
                self.assertEqual(view["state"], f.s)

    async def race(self, path, data, token):
        payload = (
            json.dumps(
                dict(database=str(self.h.db.db_path), path=path, data=data, token=token)
            )
            + "\n"
        )
        children = []
        try:
            for _ in range(2):
                child = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-c",
                    "from app.unittests.test_EngineBacklogAPI import worker; worker()",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(Path(__file__).resolve().parents[2]),
                )
                children.append(child)
                child.stdin.write(payload.encode())
                await child.stdin.drain()
            for child in children:
                while True:
                    line = await asyncio.wait_for(child.stdout.readline(), 15)
                    if line == b"READY\n":
                        break
                    if not line:
                        self.fail((await child.stderr.read()).decode())
            replies = await asyncio.gather(
                *(asyncio.wait_for(c.communicate(b"GO\n"), 15) for c in children)
            )
            results = []
            for child, (stdout, stderr) in zip(children, replies):
                self.assertEqual(child.returncode, 0, stderr.decode())
                results.append(json.loads(stdout.decode().splitlines()[-1]))
            return results
        finally:
            for child in children:
                if child.returncode is None:
                    child.kill()
                    await child.wait()

    async def test_separate_server_processes_serialize_starts_and_actions(self):
        for variant in ("1830", "1889"):
            await self.room(variant, start=False)
            replies = await self.race(
                self.path + "/start",
                dict(player_names=list("ABC")),
                self.info["creator_token"],
            )
            self.assertEqual(sorted(r["status"] for r in replies), [200, 409])
            replies = await self.race(
                self.path + "/actions",
                dict(expected_action_id=0, action=dict(type="pass")),
                self.info["player_tokens"][0],
            )
            self.assertEqual(sorted(r["status"] for r in replies), [200, 409])
            status, view = await self.h.request(
                "GET", self.path, token=self.info["spectator_token"]
            )
            self.assertEqual(view["state"]["revision"], 1)
            with sqlite3.connect(self.h.db.db_path) as connection:
                game = await self.h.db.get_game_by_room_code(self.info["room_code"])
                self.assertEqual(
                    connection.execute(
                        "SELECT move_number FROM game_states WHERE game_id=? ORDER BY id",
                        (game["id"],),
                    ).fetchall(),
                    [(0,), (1,)],
                )

    async def test_locked_writer_is_controlled_and_same_revision_retries(self):
        old_timeout = self.h.db.lock_timeout
        self.h.db.lock_timeout = 0.05
        try:
            for variant in ("1830", "1889"):
                state = await self.room(variant)
                with sqlite3.connect(self.h.db.db_path) as writer:
                    writer.execute("BEGIN IMMEDIATE")
                    status, _ = await self.action(0, "pass")
                    self.assertEqual(status, 409)
                    status, body = await self.h.request(
                        "POST", "/api/" + variant + "/games", dict(max_players=3)
                    )
                    self.assertEqual(status, 503, body)
                    self.assertNotIn("player_tokens", body)
                    writer.rollback()
                status, view = await self.h.request(
                    "GET", self.path, token=self.info["spectator_token"]
                )
                self.assertEqual(view["state"], state)
                status, _ = await self.action(0, "pass")
                self.assertEqual(status, 200)
        finally:
            self.h.db.lock_timeout = old_timeout

    async def test_room_and_token_collisions_retry_without_partial_registration(self):
        from backend import database
        import aiosqlite

        counter = iter(range(1000))
        for variant in ("1830", "1889"):
            original = await self.room(variant)
            existing = deepcopy(self.info)
            with patch.object(
                database,
                "generate_room_code",
                side_effect=[existing["room_code"], "NEW" + variant],
            ):
                status, result = await self.h.request(
                    "POST", "/api/" + variant + "/games", dict(max_players=3)
                )
                self.assertEqual(status, 200, result)
            tokens = iter(
                [
                    "creator%d" % next(counter),
                    "spectator%d" % next(counter),
                    "slot%d" % next(counter),
                    existing["player_tokens"][0],
                    "slot%d" % next(counter),
                ]
            )

            def token():
                return next(tokens, "fresh%d" % next(counter))

            with patch.object(database, "generate_token", side_effect=token):
                status, result = await self.h.request(
                    "POST", "/api/" + variant + "/games", dict(max_players=3)
                )
                self.assertEqual(status, 200, result)
                self.assertNotIn(existing["player_tokens"][0], result["player_tokens"])
            with sqlite3.connect(self.h.db.db_path) as connection:
                before = connection.execute("SELECT COUNT(*) FROM games").fetchone()[0]
            real = aiosqlite.Connection.execute
            inserts = 0

            async def fail_second_slot(connection, sql, parameters=None):
                nonlocal inserts
                if sql.startswith("INSERT INTO players"):
                    inserts += 1
                    if inserts == 2:
                        raise aiosqlite.IntegrityError(
                            "forced token collision after first slot"
                        )
                return await real(connection, sql, parameters)

            with patch.object(aiosqlite.Connection, "execute", new=fail_second_slot):
                status, result = await self.h.request(
                    "POST", "/api/" + variant + "/games", dict(max_players=3)
                )
                self.assertEqual(status, 200, result)
            with sqlite3.connect(self.h.db.db_path) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM games").fetchone()[0],
                    before + 1,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM players WHERE game_id NOT IN (SELECT id FROM games)"
                    ).fetchone()[0],
                    0,
                )
                self.assertFalse(
                    connection.execute(
                        "SELECT game_id FROM players GROUP BY game_id HAVING COUNT(*) != 3"
                    ).fetchall()
                )
            with patch.object(
                database, "generate_token", return_value="same"
            ) as generator:
                status, body = await self.h.request(
                    "POST", "/api/" + variant + "/games", dict(max_players=3)
                )
                self.assertEqual(status, 503, body)
                self.assertEqual(generator.call_count, 25)
            status, view = await self.h.request(
                "GET", self.path, token=existing["spectator_token"]
            )
            self.assertEqual(view["state"], original)

    async def test_creation_retries_collisions_across_credential_roles(self):
        from backend import database
        from itertools import count

        serial = count()
        for variant in ("1830", "1889"):
            await self.room(variant)
            for existing, target in (
                (self.info["creator_token"], 2),
                (self.info["spectator_token"], 0),
                (self.info["player_tokens"][0], 1),
            ):
                first = ["cross_role_%d" % next(serial) for _ in range(5)]
                first[target] = existing
                values = iter(first)

                def token():
                    return next(values, "cross_role_%d" % next(serial))

                with patch.object(
                    database, "generate_token", side_effect=token
                ) as generator:
                    status, info = await self.h.request(
                        "POST", "/api/" + variant + "/games", dict(max_players=3)
                    )
                    self.assertEqual(status, 200, info)
                    self.assertEqual(generator.call_count, 10)
                credentials = [info["creator_token"], info["spectator_token"]] + info[
                    "player_tokens"
                ]
                self.assertNotIn(existing, credentials)
                self.assertEqual(len(set(credentials)), 5)
