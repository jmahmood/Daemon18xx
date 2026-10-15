"""Exercise the documented entry point over real HTTP, including restart recovery."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.log = tempfile.TemporaryFile(mode="w+")
        self.addCleanup(self.log.close)
        self.process = None
        self.addCleanup(self.stop)
        self.root = Path(__file__).resolve().parents[2]
        self.database = Path(self.directory.name) / "nested" / "games.sqlite3"
        self.start()

    def start(self):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        self.base = "http://127.0.0.1:" + str(port)
        environment = dict(
            os.environ,
            DAEMON18XX_DATABASE=str(self.database),
            DAEMON18XX_CORS_ORIGINS="http://frontend.example",
        )
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.server:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(self.root),
            env=environment,
            stdout=self.log,
            stderr=self.log,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                status, _, body = self.request("GET", "/health")
                if status == 200:
                    self.assertEqual(body, {"status": "ok"})
                    return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.05)
        self.log.seek(0)
        self.fail("Server failed to become ready:\n" + self.log.read())

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process = None

    def request(self, method, path, body=None, token=None, headers=None):
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if token:
            request_headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=request_headers,
            method=method,
        )
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read()
            return response.status, response.headers, json.loads(data) if data else None

    def test_documented_client_flow_for_both_variants_survives_restart(self):
        games = []
        for variant, company in (("1830", "SV"), ("1889", "TR")):
            prefix = "/api/" + variant
            status, _, catalog = self.request("GET", prefix + "/catalog")
            self.assertEqual(status, 200)
            self.assertTrue(catalog["tiles"])
            status, _, room = self.request(
                "POST", prefix + "/games", {"max_players": 3}
            )
            self.assertEqual(status, 200)
            path = prefix + "/games/" + room["room_code"]
            status, _, view = self.request(
                "POST",
                path + "/start",
                {"player_names": ["Alice", "Bob", "Carol"]},
                room["creator_token"],
            )
            self.assertEqual(status, 200, view)
            payload = {
                "expected_action_id": view["state"]["revision"],
                "action": {"type": "buy_private", "company": company},
            }
            status, _, view = self.request(
                "POST", path + "/actions", payload, room["player_tokens"][0]
            )
            self.assertEqual(status, 200, view)
            self.assertEqual(view["state"]["revision"], 1)
            self.assertEqual(view["state"]["privates"][company]["owner"], "p1")
            status, _, _ = self.request(
                "POST", path + "/actions", payload, room["player_tokens"][0]
            )
            self.assertEqual(status, 409)
            games.append((path, room, view["state"]))
        self.stop()
        self.start()
        for path, room, state in games:
            for token in (room["player_tokens"][0], room["spectator_token"]):
                status, _, restored = self.request("GET", path, token=token)
                self.assertEqual(status, 200)
                self.assertEqual(restored["state"], state)
                self.assertNotIn(token, json.dumps(restored))

    def test_external_browser_preflight_and_removed_prototype_endpoints(self):
        for origin, expected in (
            ("http://frontend.example", 200),
            ("http://unconfigured.example", 400),
        ):
            status, headers, _ = self.preflight(origin)
            self.assertEqual(status, expected)
            self.assertEqual(
                headers.get("access-control-allow-origin"),
                origin if expected == 200 else None,
            )
        for path in ("/api/games/ABC123", "/socket.io/"):
            status, _, _ = self.request("GET", path)
            self.assertEqual(status, 404)
        status, _, _ = self.request("POST", "/api/games/create", {})
        self.assertEqual(status, 404)
        status, _, schema = self.request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        for variant in ("1830", "1889"):
            self.assertIn(
                "/api/" + variant + "/games/{room_code}/actions", schema["paths"]
            )

    def preflight(self, origin):
        request = urllib.request.Request(
            self.base + "/api/1889/games",
            method="OPTIONS",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def test_readiness_fails_without_recreating_a_missing_database(self):
        backup = self.database.with_suffix(".backup")
        self.database.rename(backup)
        status, _, body = self.request("GET", "/health")
        self.assertEqual(status, 503)
        self.assertEqual(body["detail"], "Database unavailable")
        self.assertFalse(self.database.exists())
        backup.rename(self.database)
        status, _, _ = self.request("GET", "/health")
        self.assertEqual(status, 200)
