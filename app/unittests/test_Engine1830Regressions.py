"""Regression coverage for the six defects identified in the 1830 review."""

import unittest
from app.engine1830 import new_game, apply_action, RuleError, validate_state
from app.engine1830 import engine as E, board as B
from app.unittests import test_Engine1830 as fixtures


class ReviewRepros(unittest.TestCase):
    def fixture(self, corporation="B&O"):
        f = fixtures.Rules1830Tests("runTest")
        f.setUp()
        f.operating(corporation)
        return f

    def test_emergency_private_sale_is_permitted_by_section_24(self):
        f = self.fixture()
        f.washington()
        f.to_train()
        f.s["stock_round"] = 2
        f.cash(f.s["corporations"]["B&O"], 0)
        f.cash(f.s["players"]["p3"], 0)
        # DH is owned by p3; buyer p1 consents to pay $100 during the forced purchase.
        f.act(
            "offer",
            player="p1",
            kind="private",
            item="DH",
            seller="p3",
            buyer="p1",
            price=100,
        )
        f.act("buy_private", company="DH", buyer="p1", price=100)
        self.assertEqual(f.s["players"]["p3"]["cash"], 100)
        self.assertEqual(f.s["operating_turn"]["step"], "train")
        f.act("buy_train", train="2-0")
        self.assertEqual(f.s["players"]["p3"]["cash"], 20)
        self.assertIn("2-0", f.s["corporations"]["B&O"]["trains"])

    def test_emergency_private_sale_requires_shortfall_and_train_step(self):
        for condition in ("before_train", "affordable", "has_train", "no_consent"):
            with self.subTest(condition=condition):
                f = self.fixture()
                f.washington()
                f.to_train()
                f.cash(f.s["corporations"]["B&O"], 0)
                f.cash(f.s["players"]["p3"], 0)
                if condition == "before_train":
                    f.s["operating_turn"]["step"] = "track"
                    f.s["operating_turn"]["dividend"] = False
                elif condition == "affordable":
                    f.cash(f.s["players"]["p3"], 80)
                elif condition == "has_train":
                    f.train(
                        "B&O",
                        next(
                            t
                            for t in f.s["trains"]
                            if f.s["trains"][t]["owner"] == "depot"
                        ),
                    )
                if condition != "no_consent":
                    f.act(
                        "offer",
                        player="p1",
                        kind="private",
                        item="DH",
                        seller="p3",
                        buyer="p1",
                        price=100,
                    )
                f.reject("buy_private", company="DH", buyer="p1", price=100)

    def test_bankruptcy_allowed_after_all_legal_stock_sales(self):
        f = self.fixture()
        f.washington()
        f.to_train()
        c = f.s["corporations"]["B&O"]
        c["holdings"].update(p3=40, p1=30)
        c["ipo"] = 30
        E._position(f.s, c, [0, 1])  # $67 market value; $80 2-train still available.
        f.cash(c, 0)
        f.cash(f.s["players"]["p3"], 0)
        validate_state(f.s)
        f.act("emergency_sell", corporation="B&O", percent=10)
        self.assertEqual(f.s["players"]["p3"]["cash"], 67)
        f.reject(
            "emergency_sell", corporation="B&O", percent=10
        )  # Would transfer presidency.
        f.act("bankrupt")  # No legal sale can produce the remaining $13.
        self.assertTrue(f.s["finished"])

    def test_separate_cities_cannot_collapse_on_upgrade(self):
        old = B.tile_for("59", 0)
        new = B.tile_for("64", 0)
        mapping = B.preserved_mapping(old, new)
        self.assertTrue(
            mapping is None or len(set(mapping)) == 2,
            "Two separate cities were mapped to one city: %r" % mapping,
        )

    def test_unfloated_home_reservation_follows_city_mapping(self):
        f = self.fixture("C&O")
        s = f.s
        s["phase"] = "3"
        old = s["board"]["G19"]
        mapping = B.preserved_mapping(old, B.tile_for("54", 0))
        self.assertEqual(mapping, [1, 0])
        # A token supplies a controlled railhead for the upgrade.
        s["board"]["G19"]["tokens"][1] = ["C&O"]
        B.lay_tile(s, "C&O", "G19", "54", 0)
        self.assertTrue(B.reserved_home(s, "G19", 1, "PRR"))
        self.assertFalse(B.reserved_home(s, "G19", 0, "PRR"))
        c = s["corporations"]["NYNH"]
        E._set_par(s, c, 100)
        c["holdings"]["p1"] = 60
        c["ipo"] = 40
        c["president"] = "p1"
        E._float(c)
        s["round"] = "stock"
        s["phase"] = "3"
        s["or_number"] = 1
        E._start_operating(s)
        s["or_index"] = s["or_order"].index("NYNH")
        E._start_corporation(s)
        self.assertIn(
            "NYNH",
            s["board"]["G19"]["tokens"][mapping[0]],
            "NYNH home was placed in the wrong city after upgrade",
        )

    def test_erie_base_does_not_move_when_first_tile_is_laid(self):
        f = self.fixture("ERIE")
        f.act("home_token", city=1)
        self.assertIn("ERIE", f.s["board"]["E11"]["tokens"][1])
        f.s["phase"] = "3"
        f.act("lay_tile", hex="E11", tile="59", rotation=0)
        self.assertIn(
            "ERIE",
            f.s["board"]["E11"]["tokens"][1],
            "Erie base moved from city 1 to city 0 during initial construction",
        )

    def test_token_connectivity_cannot_reverse_across_junction(self):
        f = self.fixture()
        f.act("lay_tile", hex="I17", tile="9", rotation=1)
        f.s["phase"] = "3"
        f.s["operating_turn"].update(step="track", laid=False)
        f.act("lay_tile", hex="I17", tile="23", rotation=4)
        f.s["operating_turn"].update(step="track", laid=False)
        f.reject("lay_tile", hex="H16", tile="57", rotation=2)
        # Independently test token reachability with the destination constructed.
        f.s["board"]["H16"] = B.tile_for("57", 2)
        f.s["tiles"]["57"] -= 1
        legal_routes = B.route_candidates(f.s, "B&O", limit=1000)
        self.assertFalse(any("H16:n0" in r["vertices"] for r in legal_routes))
        with self.assertRaises(RuleError):
            f.act("place_token", hex="H16")

    def test_home_upgrade_cannot_deadlock_end_of_stock_round(self):
        s = new_game(["A", "B", "C"])
        s["phase"] = "3"
        co = s["corporations"]["C&O"]
        E._set_par(s, co, 67)
        co["holdings"]["p2"] = 60
        co.update(ipo=40, president="p2", funded=True, home_placed=True)
        E._float(co)
        E._pay(s, "bank", "C&O", 1000)
        s["board"]["F6"]["tokens"][0] = ["C&O"]
        s["board"]["G19"]["tokens"][1] = ["C&O"]
        # A valid upgrade transfers C&O from old city 1 to new city 0.
        # NYNH's reserved old city 0 must consequently become new city 1.
        B.lay_tile(s, "C&O", "G19", "54", 0)
        self.assertEqual(s["board"]["G19"]["tokens"][0], ["C&O"])
        home = s["corporations"]["NYNH"]
        E._set_par(s, home, 100)
        home["holdings"]["p1"] = 60
        home.update(ipo=40, president="p1")
        E._float(home)
        E._start_stock(s)
        validate_state(s)
        for player in ("p1", "p2", "p3"):
            s = apply_action(s, {"type": "pass", "player": player})
        self.assertEqual(s["round"], "operating")
        self.assertEqual(s["board"]["G19"]["tokens"][1], ["NYNH"])

    def test_malformed_hex_is_a_rule_error(self):
        f = self.fixture()
        with self.assertRaises(RuleError):
            apply_action(
                f.s,
                {
                    "type": "lay_tile",
                    "player": "p3",
                    "hex": [],
                    "tile": "57",
                    "rotation": 0,
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
