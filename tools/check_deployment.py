"""Verify the real Compose deployment in a disposable project and volume.

Build the image first, then run: python tools/check_deployment.py
No existing Compose project or game database is modified.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="daemon18xx-backend")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project = "daemon18xx-check-" + uuid4().hex[:12]
    environment = dict(
        os.environ,
        DAEMON18XX_PORT="0",
        DAEMON18XX_DATABASE="/data/games.sqlite3",
        DAEMON18XX_CORS_ORIGINS="http://frontend.example",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory() as directory:
        override = Path(directory) / "image.json"
        override.write_text(
            json.dumps({"services": {"backend": {"image": args.image}}})
        )
        command = [
            "docker",
            "compose",
            "--project-name",
            project,
            "-f",
            str(root / "compose.yaml"),
            "-f",
            str(override),
        ]

        def compose(*arguments):
            return subprocess.check_output(
                command + list(arguments),
                cwd=str(root),
                env=environment,
                stderr=subprocess.STDOUT,
                text=True,
            )

        def request(method, path, body=None, token=None):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            req = urllib.request.Request(
                base + path,
                data=json.dumps(body).encode() if body is not None else None,
                headers=headers,
                method=method,
            )
            with opener.open(req, timeout=10) as response:
                return json.load(response)

        def ready():
            nonlocal base
            address = compose("port", "backend", "8000").strip()
            base = "http://" + address
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                try:
                    if request("GET", "/health") == {"status": "ok"}:
                        return
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(0.2)
            raise RuntimeError("Container did not become ready")

        def verify(games):
            for path, room, expected in games:
                for token in (
                    room["creator_token"],
                    room["spectator_token"],
                    room["player_tokens"][0],
                ):
                    result = request("GET", path, token=token)
                    if result["state"] != expected:
                        raise RuntimeError(
                            "Recovered game differs from the committed snapshot"
                        )

        base = ""
        try:
            compose("up", "-d", "--no-build")
            ready()
            container = compose("ps", "-q", "backend").strip()
            configuration = json.loads(
                subprocess.check_output(["docker", "inspect", container], text=True)
            )[0]
            assert (
                configuration["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"
            )
            assert any(
                mount["Destination"] == "/data" and mount["Type"] == "volume"
                for mount in configuration["Mounts"]
            )
            games = []
            for variant, company in (("1830", "SV"), ("1889", "TR")):
                prefix = "/api/" + variant
                schema = request("GET", prefix + "/schema")
                assert schema["x-contract-version"] == 1
                room = request("POST", prefix + "/games", {"max_players": 3})
                path = prefix + "/games/" + room["room_code"]
                request(
                    "POST",
                    path + "/start",
                    {"player_names": ["A", "B", "C"]},
                    room["creator_token"],
                )
                result = request(
                    "POST",
                    path + "/actions",
                    {
                        "expected_action_id": 0,
                        "action": {"type": "buy_private", "company": company},
                    },
                    room["player_tokens"][0],
                )
                assert result["state"]["revision"] == 1
                assert result["state"]["privates"][company]["owner"] == "p1"
                games.append((path, room, result["state"]))
            print(
                "Both variants: create, start and committed action passed.", flush=True
            )
            compose("restart", "backend")
            ready()
            verify(games)
            print("Process restart preserved games and credentials.", flush=True)
            compose("down", "--timeout", "10")
            compose("up", "-d", "--no-build")
            ready()
            verify(games)
            print(
                "Container removal/recreation preserved the named-volume games.",
                flush=True,
            )
            compose(
                "exec",
                "-T",
                "backend",
                "python",
                "-m",
                "backend.backup",
                "/data/games.sqlite3",
                "/data/backups/checkpoint.sqlite3",
            )
            for path, room, _ in games:
                result = request(
                    "POST",
                    path + "/actions",
                    {"expected_action_id": 1, "action": {"type": "pass"}},
                    room["player_tokens"][1],
                )
                assert result["state"]["revision"] == 2
            compose("stop", "--timeout", "10", "backend")
            compose(
                "run",
                "--rm",
                "--no-deps",
                "backend",
                "python",
                "-m",
                "backend.backup",
                "/data/backups/checkpoint.sqlite3",
                "/data/restored.sqlite3",
            )
            environment["DAEMON18XX_DATABASE"] = "/data/restored.sqlite3"
            compose("up", "-d", "--no-build", "--force-recreate")
            ready()
            verify(games)
            for path, room, _ in games:
                result = request(
                    "POST",
                    path + "/actions",
                    {"expected_action_id": 1, "action": {"type": "pass"}},
                    room["player_tokens"][1],
                )
                assert result["state"]["revision"] == 2
            print(
                "Backup restored the earlier revision and retained writable games and credentials.",
                flush=True,
            )
        except BaseException:
            try:
                print(compose("logs", "--no-color", "--tail", "80"), flush=True)
            except subprocess.CalledProcessError:
                pass
            raise
        finally:
            # Only the uniquely named project/volume created by this invocation.
            compose("down", "--volumes", "--remove-orphans", "--timeout", "10")
    print("Deployment verification passed; disposable resources removed.")


if __name__ == "__main__":
    main()
