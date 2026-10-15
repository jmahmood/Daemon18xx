"""Both real HTTP adapters enforce lifecycle, atomicity and the rule fixes."""

import asyncio
import unittest

from app.unittests import test_Engine1830API as api_fixtures
from app.unittests import test_EngineAuctionAndEmergency as rule_fixtures


class BackendAPIEdgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.h = api_fixtures.Rules1830APITests("runTest")
        await self.h.asyncSetUp()

    async def asyncTearDown(self):
        await self.h.asyncTearDown()

    async def room(self, variant, count=3, start=True):
        self.variant = variant
        status, self.info = await self.h.request(
            "POST", "/api/" + variant + "/games", {"max_players": count}
        )
        self.assertEqual(status, 200, self.info)
        self.path = "/api/" + variant + "/games/" + self.info["room_code"]
        if start:
            status, view = await self.h.request(
                "POST",
                self.path + "/start",
                {"player_names": list("ABCDEF")[:count]},
                self.info["creator_token"],
            )
            self.assertEqual(status, 200, view)
            return view

    async def submit(self, revision, actor, **action):
        return await self.h.request(
            "POST",
            self.path + "/actions",
            dict(expected_action_id=revision, action=action),
            self.info["player_tokens"][int(actor[1:]) - 1],
        )

    async def test_unstarted_rooms_missing_rooms_and_invalid_room_sizes(self):
        for variant in ("1830", "1889"):
            with self.subTest(variant=variant):
                await self.room(variant, start=False)
                status, _ = await self.h.request(
                    "GET", self.path, token=self.info["spectator_token"]
                )
                self.assertEqual(status, 409)
                status, _ = await self.submit(0, "p1", type="pass")
                self.assertEqual(status, 409)
                status, _ = await self.h.request(
                    "GET",
                    "/api/" + variant + "/games/MISSING",
                    token=self.info["spectator_token"],
                )
                self.assertEqual(status, 404)
                for size in (1, 7):
                    status, _ = await self.h.request(
                        "POST", "/api/" + variant + "/games", {"max_players": size}
                    )
                    self.assertEqual(status, 422)

    async def test_start_rejects_wrong_slot_count_blank_and_duplicate_names(self):
        for variant in ("1830", "1889"):
            await self.room(variant, start=False)
            for names in (["A", "B"], ["A", "A", "C"], ["A", " ", "C"]):
                status, _ = await self.h.request(
                    "POST",
                    self.path + "/start",
                    dict(player_names=names),
                    self.info["creator_token"],
                )
                self.assertEqual(status, 422)
            game = await self.h.db.get_game_by_room_code(self.info["room_code"])
            self.assertIsNone(await self.h.db.get_latest_game_state(game["id"]))

    async def test_simultaneous_start_only_initializes_once(self):
        for variant in ("1830", "1889"):
            await self.room(variant, start=False)
            replies = await asyncio.gather(
                *[
                    self.h.request(
                        "POST",
                        self.path + "/start",
                        dict(player_names=["A", "B", "C"]),
                        self.info["creator_token"],
                    )
                    for _ in range(2)
                ]
            )
            self.assertEqual(sorted(status for status, _ in replies), [200, 409])
            status, current = await self.h.request(
                "GET", self.path, token=self.info["spectator_token"]
            )
            self.assertEqual(status, 200)
            self.assertEqual(current["state"]["revision"], 0)

    async def test_invalid_action_envelopes_do_not_create_snapshots(self):
        for variant in ("1830", "1889"):
            initial = await self.room(variant)
            for payload in (
                {},
                dict(action=dict(type="pass")),
                dict(expected_action_id=-1, action=dict(type="pass")),
                dict(expected_action_id=0, action=[]),
                dict(expected_action_id=0, action=dict(type="unknown")),
            ):
                status, _ = await self.h.request(
                    "POST",
                    self.path + "/actions",
                    payload,
                    self.info["player_tokens"][0],
                )
                self.assertEqual(status, 422)
            status, current = await self.h.request(
                "GET", self.path, token=self.info["creator_token"]
            )
            self.assertEqual(current, initial)

    async def test_competitive_auction_uses_variant_bidder_order_over_http(self):
        for variant, company, face, preceding in (
            ("1830", "DH", 70, ("SV", "CS")),
            ("1889", "ER", 40, ("TR", "MF")),
        ):
            view = await self.room(variant, 4)
            actions = [
                dict(type="bid", company=company, price=face + 5),
                dict(type="pass"),
                dict(type="bid", company=company, price=face + 10),
                dict(type="pass"),
                dict(type="pass"),
                dict(type="bid", company=company, price=face + 15),
            ]
            actions += [dict(type="buy_private", company=c) for c in preceding]
            actions.append(dict(type="pass"))
            for action in actions:
                state = view["state"]
                status, view = await self.submit(
                    state["revision"], state["current_player"], **action
                )
                self.assertEqual(status, 200, view)
            state = view["state"]
            challenger = "p1" if variant == "1889" else "p3"
            self.assertEqual(state["current_player"], challenger)
            status, _ = await self.submit(state["revision"], "p2", type="pass")
            self.assertEqual(status, 422)
            status, restored = await self.h.request(
                "GET", self.path, token=self.info["spectator_token"]
            )
            self.assertEqual(restored["state"], state)
            status, view = await self.submit(state["revision"], challenger, type="pass")
            self.assertEqual(status, 200, view)
            self.assertEqual(view["state"]["privates"][company]["owner"], "p2")

    async def test_1889_repeat_emergency_block_is_rejected_after_database_reload(self):
        await self.room("1889")
        fixture = rule_fixtures.EmergencyBlock1889Tests("runTest")
        fixture.setUp()
        state = fixture.f.s
        game = await self.h.db.get_game_by_room_code(self.info["room_code"])
        await self.h.db.save_rules_state(game["id"], state, 0)
        status, view = await self.submit(
            state["revision"], "p1", type="emergency_sell", corporation="AR", percent=10
        )
        self.assertEqual(status, 200, view)
        status, restored = await self.h.request(
            "GET", self.path, token=self.info["player_tokens"][0]
        )
        self.assertEqual(status, 200)
        state = restored["state"]
        self.assertEqual(state["operating_turn"]["emergency_sales"], ["AR"])
        status, _ = await self.submit(
            state["revision"], "p1", type="emergency_sell", corporation="AR", percent=10
        )
        self.assertEqual(status, 422)
        record = await self.h.db.get_latest_game_state(game["id"])
        self.assertEqual(record["move_number"], state["revision"])

    async def test_1889_unknown_saved_schema_is_a_conflict(self):
        initial = await self.room("1889")
        state = initial["state"]
        state.update(schema_version=999, revision=1)
        game = await self.h.db.get_game_by_room_code(self.info["room_code"])
        await self.h.db.save_rules_state(game["id"], state, 0)
        status, _ = await self.h.request(
            "GET", self.path, token=self.info["spectator_token"]
        )
        self.assertEqual(status, 409)
        status, _ = await self.submit(1, "p1", type="pass")
        self.assertEqual(status, 409)

    async def test_cross_room_and_cross_variant_tokens_cannot_read_or_write(self):
        for variant in ("1830", "1889"):
            await self.room(variant)
            token = self.info["player_tokens"][0]
            await self.room(variant)
            status, _ = await self.h.request("GET", self.path, token=token)
            self.assertEqual(status, 403)
            status, _ = await self.h.request(
                "POST",
                self.path + "/actions",
                dict(expected_action_id=0, action=dict(type="pass")),
                token,
            )
            self.assertEqual(status, 403)
            other = "1889" if variant == "1830" else "1830"
            status, _ = await self.h.request(
                "GET",
                self.path.replace("/" + variant + "/", "/" + other + "/"),
                token=self.info["player_tokens"][0],
            )
            self.assertEqual(status, 404)

    async def test_catalog_board_and_variant_specific_metadata(self):
        for variant, count in (("1830", 93), ("1889", 52)):
            status, catalog = await self.h.request(
                "GET", "/api/" + variant + "/catalog"
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(catalog["hexes"]), count)
            self.assertTrue(catalog["tiles"])
            if variant == "1889":
                self.assertEqual(catalog["currency"], "JPY")
                self.assertEqual(catalog["par_prices"], [65, 70, 75, 80, 90, 100])
                self.assertEqual(set(catalog["phases"]), {"2", "3", "4", "5", "6", "D"})
                self.assertEqual(
                    set(catalog["train_types"]), {"2", "3", "4", "5", "6", "D"}
                )
