"""Home-token progression, saved-game migration and out-of-turn discovery."""

import unittest
import json
from copy import deepcopy
from app.engine1830 import (
    apply_action,
    new_game,
    migrate_state,
    legal_actions,
    RuleError,
)
from app.engine1830 import board as B, engine as E
from app.unittests import test_Engine1830 as fixtures
from app.unittests import test_Engine1830API as api_fixtures


def fixture(corporation=None):
    f = fixtures.Rules1830Tests("runTest")
    f.setUp()
    if corporation:
        f.operating(corporation)
    return f


def legacy_new_york():
    f = fixture("C&O")
    f.s["phase"] = "3"
    f.s["board"]["G19"]["tokens"][1] = ["C&O"]
    B.lay_tile(f.s, "C&O", "G19", "54", 0)
    f.shares("NYNH", "p2", 60)
    E._market_move(f.s, f.s["corporations"]["NYNH"], "right")
    E._start_stock(f.s)
    f.s["schema_version"] = 1
    for c in f.s["corporations"].values():
        c.pop("home_city")
    return f


class StateAndActionTests(unittest.TestCase):
    def test_erie_cannot_advance_without_home_and_can_finish_after_placing_it(self):
        for kind, args in (
            ("dividend", {"kind": "withhold"}),
            ("run_routes", {"routes": []}),
            ("place_token", {"hex": "E11"}),
        ):
            with self.subTest(action=kind):
                f = fixture("ERIE")
                original = deepcopy(f.s)
                initial = legal_actions(f.s)
                self.assertIn("skip", initial["types"])
                self.assertIn("home_token", initial["types"])
                self.assertNotIn("dividend", initial["types"])
                self.assertEqual(f.s, original)
                f.reject(kind, **args)
                f.act("skip")
                f.reject("skip")
                self.assertNotIn("skip", legal_actions(f.s)["types"])
                self.assertNotIn("dividend", legal_actions(f.s)["types"])
                f.act("home_token", city=1)
                f.to_train()
                f.act("end_turn")
                self.assertEqual(f.s["round"], "stock")

    def test_legacy_new_york_mapping_allows_stock_round_to_finish(self):
        f = legacy_new_york()
        original = deepcopy(f.s)
        migrated = migrate_state(f.s)
        self.assertEqual(f.s, original)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["revision"], original["revision"])
        self.assertEqual(migrated["history"], original["history"])
        self.assertEqual(migrated["corporations"]["NYNH"]["home_city"], 1)
        self.assertEqual(migrate_state(migrated), migrated)
        # Public apply_action also migrates callers' legacy snapshots atomically.
        for _ in range(3):
            f.act("pass")
        self.assertEqual(f.s["round"], "operating")
        self.assertEqual(f.s["board"]["G19"]["tokens"], [["C&O"], ["NYNH"]])

    def test_legacy_placed_nynh_home_is_repaired(self):
        f = legacy_new_york()
        f.s["board"]["G19"]["tokens"] = [["NYNH"], []]
        f.s["corporations"]["NYNH"]["home_placed"] = True
        migrated = migrate_state(f.s)
        self.assertEqual(migrated["board"]["G19"]["tokens"], [[], ["NYNH"]])

    def test_legacy_erie_choice_is_preserved(self):
        f = fixture("ERIE")
        f.act("home_token", city=1)
        f.s["schema_version"] = 1
        for c in f.s["corporations"].values():
            c.pop("home_city")
        migrated = migrate_state(f.s)
        self.assertEqual(migrated["corporations"]["ERIE"]["home_city"], 1)
        self.assertEqual(migrated["board"], f.s["board"])

    def test_unknown_schema_and_conflicting_repairs_are_rejected_atomically(self):
        f = legacy_new_york()
        f.s["corporations"]["NYNH"]["home_placed"] = True
        f.s["board"]["G19"]["tokens"] = [["NYNH"], ["C&O"]]
        original = deepcopy(f.s)
        with self.assertRaises(RuleError):
            migrate_state(f.s)
        self.assertEqual(f.s, original)
        current = new_game(["A", "B", "C"])
        current["schema_version"] = 99
        with self.assertRaises(RuleError):
            migrate_state(current)
        with self.assertRaises(RuleError):
            apply_action(current, {"type": "pass", "player": "p1"})

    def test_migration_rejects_blocked_legacy_reservation(self):
        f = legacy_new_york()
        f.s["board"]["G19"]["tokens"] = [[], ["C&O"]]
        original = deepcopy(f.s)
        with self.assertRaisesRegex(RuleError, "blocked home reservation"):
            migrate_state(f.s)
        self.assertEqual(f.s, original)

    def test_train_offer_discovery_only_includes_transaction_parties(self):
        f = fixture("B&O")
        f.shares("C&O", "p1", 20)
        f.train("C&O", "2-0")
        choices = legal_actions(f.s, "p1")["choices"]["offers"]
        offer = dict(kind="train", item="2-0", seller="C&O", buyer="B&O")
        self.assertIn(offer, choices)
        self.assertNotIn(offer, legal_actions(f.s, "p2")["choices"].get("offers", []))
        self.assertEqual(legal_actions(f.s, "unknown")["types"], [])
        f.act("offer", player="p1", price=80, **offer)

    def test_non_active_seller_can_discover_and_submit_offer(self):
        f = fixture("B&O")
        f.s["phase"] = "3"
        before = deepcopy(f.s)
        actions = legal_actions(f.s, "p1")
        self.assertEqual(f.s, before)
        self.assertEqual(actions["player"], "p1")
        self.assertEqual(actions["active_player"], "p3")
        self.assertIn("offer", actions["types"])
        offer = dict(kind="private", item="SV", seller="p1", buyer="B&O")
        self.assertIn(offer, actions["choices"]["offers"])
        f.act("offer", player="p1", price=20, **offer)
        f.act("buy_private", company="SV", buyer="B&O", price=20)
        self.assertEqual(f.s["privates"]["SV"]["owner"], "B&O")

    def test_between_turn_exchange_discovery_and_interrupt_restrictions(self):
        f = fixture()
        f.stock()
        f.shares("NYC", "p2", 20)
        f.act("pass")
        actions = legal_actions(f.s, "p1")
        self.assertIn("exchange_private", actions["types"])
        self.assertEqual(actions["choices"]["exchange_sources"], ["ipo"])
        f.act("exchange_private", player="p1", source="ipo")
        self.assertNotIn("exchange_private", legal_actions(f.s, "p1")["types"])
        f = fixture("B&O")
        f.act("skip")
        self.assertNotIn("exchange_private", legal_actions(f.s, "p1")["types"])
        f.s["pending_discards"] = ["B&O"]
        self.assertEqual(legal_actions(f.s, "p3")["types"], ["discard_train"])
        self.assertEqual(legal_actions(f.s, "p1")["types"], [])
        f = fixture()
        for private in f.s["privates"]:
            f.act("buy_private", company=private)
        self.assertEqual(legal_actions(f.s, "p3")["types"], ["par"])
        self.assertEqual(legal_actions(f.s, "p1")["types"], [])


class StateAndActionHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.http = api_fixtures.Rules1830APITests("runTest")
        await self.http.asyncSetUp()
        await self.http.start()
        self.game = await self.http.db.get_game_by_room_code(
            self.http.room["room_code"]
        )

    async def asyncTearDown(self):
        await self.http.asyncTearDown()

    async def test_erie_rejection_is_not_persisted_and_home_can_be_placed(self):
        f = fixture("ERIE")
        h = self.http
        await h.db.save_rules_state(self.game["id"], f.s, 0)
        token = h.room["player_tokens"][0]
        status, _ = await h.request(
            "POST",
            h.path + "/actions",
            {
                "expected_action_id": f.s["revision"],
                "action": {"type": "dividend", "kind": "withhold"},
            },
            token,
        )
        self.assertEqual(status, 422)
        status, current = await h.request("GET", h.path, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(current["state"], f.s)
        status, current = await h.request(
            "POST",
            h.path + "/actions",
            {
                "expected_action_id": f.s["revision"],
                "action": {"type": "home_token", "city": 1},
            },
            token,
        )
        self.assertEqual(status, 200, current)

    async def test_old_snapshot_is_migrated_on_read_and_persisted_on_action(self):
        f = legacy_new_york()
        h = self.http
        await h.db.save_rules_state(self.game["id"], f.s, 0)
        status, current = await h.request(
            "GET", h.path, token=h.room["player_tokens"][0]
        )
        self.assertEqual(status, 200)
        self.assertEqual(current["state"]["schema_version"], 2)
        self.assertEqual(current["state"]["revision"], f.s["revision"])
        saved = await h.db.get_latest_game_state(self.game["id"])

        self.assertEqual(json.loads(saved["state_json"])["schema_version"], 1)
        for slot in (0, 1, 2):
            status, current = await h.request(
                "POST",
                h.path + "/actions",
                {
                    "expected_action_id": current["state"]["revision"],
                    "action": {"type": "pass"},
                },
                h.room["player_tokens"][slot],
            )
            self.assertEqual(status, 200, current)
        self.assertEqual(
            current["state"]["board"]["G19"]["tokens"], [["C&O"], ["NYNH"]]
        )
        saved = await h.db.get_latest_game_state(self.game["id"])
        self.assertEqual(json.loads(saved["state_json"])["schema_version"], 2)

    async def test_unknown_saved_schema_returns_conflict(self):
        f = fixture()
        f.stock()
        f.s["schema_version"] = 99
        h = self.http
        await h.db.save_rules_state(self.game["id"], f.s, 0)
        status, _ = await h.request("GET", h.path, token=h.room["player_tokens"][0])
        self.assertEqual(status, 409)
