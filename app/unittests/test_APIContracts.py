"""Validate public discovery against real game state and standard JSON Schema."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from app import engine1830, engine1889
from app.unittests import test_Engine1830API as api_fixtures


class APIContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.http = api_fixtures.Rules1830APITests("runTest")
        await self.http.asyncSetUp()

    async def asyncTearDown(self):
        await self.http.asyncTearDown()

    async def room(self, variant):
        status, room = await self.http.request(
            "POST", "/api/" + variant + "/games", {"max_players": 3}
        )
        self.assertEqual(status, 200)
        path = "/api/" + variant + "/games/" + room["room_code"]
        status, view = await self.http.request(
            "POST",
            path + "/start",
            {"player_names": ["A", "B", "C"]},
            room["creator_token"],
        )
        self.assertEqual(status, 200, view)
        return path, room, view

    async def test_catalogs_preserve_raw_data_and_expose_parsed_geometry_and_components(
        self,
    ):
        from importlib import import_module

        for variant in ("1830", "1889"):
            data = import_module("app.engine" + variant + ".data")
            board = import_module("app.engine" + variant + ".board")
            original = deepcopy(data.BOARD_DATA)
            status, result = await self.http.request(
                "GET", "/api/" + variant + "/catalog"
            )
            self.assertEqual(status, 200)
            for key, value in original.items():
                self.assertEqual(result[key], json.loads(json.dumps(value)))
            self.assertEqual(result["board"], board.initial_board())
            self.assertEqual(
                result["edge_deltas"], [list(pair) for pair in board.DELTAS]
            )
            self.assertEqual(result["par_prices"], list(data.PAR_PRICES))
            self.assertEqual(result["market"], data.MARKET)
            for tid in data.BOARD_DATA["tiles"]:
                self.assertEqual(result["tile_geometry"][tid], board.tile_for(tid, 0))
            self.assertEqual(
                set(result["components"]["corporations"]), set(data.CORPORATIONS)
            )
            for kind, values in data.TRAIN_TYPES.items():
                self.assertEqual(
                    result["components"]["train_types"][kind]["price"], values[1]
                )
            self.assertEqual(
                result["components"]["train_types"]["D"]["unlimited"], variant == "1889"
            )
            self.assertEqual(data.BOARD_DATA, original)

    async def test_action_hints_follow_authenticated_seat_and_pending_interrupts(self):
        for variant, engine in (("1830", engine1830), ("1889", engine1889)):
            path, room, initial = await self.room(variant)
            for seat, token in enumerate(room["player_tokens"], 1):
                status, view = await self.http.request("GET", path, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(
                    view["legal_actions"],
                    engine.legal_actions(initial["state"], "p" + str(seat)),
                )
                self.assertEqual(
                    view["currency"], "USD" if variant == "1830" else "JPY"
                )
            status, view = await self.http.request(
                "POST",
                path + "/actions",
                {"expected_action_id": 0, "action": {"type": "pass"}},
                room["player_tokens"][0],
            )
            self.assertEqual(status, 200)
            self.assertEqual(
                view["legal_actions"], engine.legal_actions(view["state"], "p1")
            )
            self.assertEqual(view["legal_actions"]["active_player"], "p2")
        from app.unittests.test_Engine1830 import Rules1830Tests

        fixture = Rules1830Tests("runTest")
        fixture.setUp()
        fixture.operating("ERIE")
        path, room, _ = await self.room("1830")
        game = await self.http.db.get_game_by_room_code(room["room_code"])
        await self.http.db.save_rules_state(game["id"], fixture.s, 0)
        for index, token in enumerate(room["player_tokens"], 1):
            status, view = await self.http.request("GET", path, token=token)
            self.assertEqual(status, 200)
            self.assertEqual(
                view["legal_actions"],
                engine1830.legal_actions(fixture.s, "p" + str(index)),
            )
        # Existing ER seller-interrupt HTTP regressions remain part of full discovery.

    async def test_published_schemas_are_valid_and_reject_malformed_parameters(self):
        for variant in ("1830", "1889"):
            status, schema = await self.http.request(
                "GET", "/api/" + variant + "/schema"
            )
            self.assertEqual(status, 200)
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            actions = schema["properties"]["action"]["oneOf"]
            names = {action["title"] for action in actions}
            self.assertEqual("home_token" in names, variant == "1830")
            self.assertEqual("run_best_routes" in names, variant == "1889")
            for action in actions:
                for example in action["examples"]:
                    validator.validate(dict(expected_action_id=0, action=example))
            for action in (
                {"type": "unknown"},
                {"type": "bid", "company": "X"},
                {"type": "lay_tile", "hex": "A1", "tile": "7", "rotation": 6},
                {"type": "sell_shares", "corporation": "X", "percent": 15},
                {"type": "dividend", "payout": "yes"},
                {
                    "type": "run_routes",
                    "routes": [{"train": "2-0", "paths": [["A1", True]]}],
                },
            ):
                self.assertFalse(
                    validator.is_valid(dict(expected_action_id=0, action=action)),
                    action,
                )
            self.assertIn("STALE_REVISION", schema["x-error-codes"])

    async def test_openapi_describes_each_variant_action_body_and_error_shape(self):
        status, document = await self.http.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        for variant in ("1830", "1889"):
            operation = document["paths"][
                "/api/" + variant + "/games/{room_code}/actions"
            ]["post"]
            schema = operation["requestBody"]["content"]["application/json"]["schema"]
            self.assertTrue(schema["properties"]["action"]["oneOf"])
            self.assertIn("expected_action_id", schema["required"])
            errors = operation["responses"]["422"]["content"]["application/json"][
                "schema"
            ]
            self.assertIn("code", errors["properties"])

    async def test_error_codes_preserve_detail_status_and_rejected_state(self):
        for variant in ("1830", "1889"):
            path, room, initial = await self.room(variant)
            for token, status_expected, code in (
                (None, 401, "AUTH_REQUIRED"),
                ("wrong", 403, "INVALID_CREDENTIAL"),
            ):
                status, body = await self.http.request("GET", path, token=token)
                self.assertEqual((status, body["code"]), (status_expected, code))
                self.assertIsInstance(body["detail"], str)
            for payload, code in (
                ({}, "REQUEST_VALIDATION_FAILED"),
                (
                    {"expected_action_id": 1, "action": {"type": "pass"}},
                    "STALE_REVISION",
                ),
                (
                    {"expected_action_id": 0, "action": {"type": "unknown"}},
                    "RULE_VIOLATION",
                ),
                (
                    {
                        "expected_action_id": 0,
                        "action": {"type": "pass", "player": "p2"},
                    },
                    "PLAYER_MISMATCH",
                ),
            ):
                status, body = await self.http.request(
                    "POST", path + "/actions", payload, room["player_tokens"][0]
                )
                self.assertEqual(body["code"], code)
                self.assertEqual(
                    status,
                    (
                        403
                        if code == "PLAYER_MISMATCH"
                        else 409 if code == "STALE_REVISION" else 422
                    ),
                )
                self.assertIn("detail", body)
            status, view = await self.http.request(
                "GET", path, token=room["creator_token"]
            )
            self.assertEqual(view, initial)


class RecordedActionContractTests(unittest.TestCase):
    def test_existing_recordings_fit_their_variant_action_contract(self):
        from backend.contracts import action_contract

        root = Path(__file__).with_name("fixtures")
        for variant, filenames in (
            ("1830", ["29133.json", "1830_game_end_bank.json"]),
            ("1889", ["1889/962.json", "1889/authored_all_phases.json"]),
        ):
            validator = Draft202012Validator(action_contract(variant))
            for filename in filenames:
                record = json.loads((root / filename).read_text())
                for revision, action in enumerate(record["actions"]):
                    with self.subTest(
                        variant=variant, file=filename, revision=revision
                    ):
                        validator.validate(
                            dict(expected_action_id=revision, action=action)
                        )
