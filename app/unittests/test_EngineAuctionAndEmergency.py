"""Auction and forced-sale regressions exercised through public actions."""

import json
import unittest
from copy import deepcopy

from app import engine1830, engine1889
from app.engine1889 import engine as E
from app.unittests import test_Engine1889 as fixtures


class AuctionOrderingTests(unittest.TestCase):
    def test_bid_resets_consecutive_passes_before_first_private_sells(self):
        for module, target, face in ((engine1830, "DH", 70), (engine1889, "ER", 40)):
            with self.subTest(variant=module.__name__):
                self.module = module
                self.s = module.new_game(["A", "B", "C"])
                self.act("pass")
                self.act("pass")
                self.act("bid", company=target, price=face + 5)
                self.act("pass")
                self.act("pass")
                self.assertEqual(self.s["auction"]["discount"], 0)
                self.assertEqual(self.s["auction"]["passes"], 2)

    def auction(self, module):
        self.module = module
        self.s = module.new_game(["A", "B", "C", "D"])
        if module is engine1889:
            self.company, self.face, preceding = "ER", 40, ("TR", "MF")
        else:
            self.company, self.face, preceding = "DH", 70, ("SV", "CS")
        self.act("bid", company=self.company, price=self.face + 5)
        self.act("pass")
        self.act("bid", company=self.company, price=self.face + 10)
        self.act("pass")
        self.act("pass")
        self.act("bid", company=self.company, price=self.face + 15)
        for company in preceding:
            self.act("buy_private", company=company)
        self.assertEqual(
            self.s["current_player"], "p3" if module is engine1889 else "p1"
        )

    def act(self, kind, **args):
        actor = args.pop("player", self.s["current_player"])
        self.s = self.module.apply_action(self.s, dict(type=kind, player=actor, **args))

    def reject(self, kind, **args):
        original = deepcopy(self.s)
        with self.assertRaises(self.module.RuleError):
            self.act(kind, **args)
        self.assertEqual(self.s, original)

    def test_variant_bidder_order_after_pass_and_high_bid_cannot_withdraw(self):
        for module in (engine1830, engine1889):
            with self.subTest(variant=module.__name__):
                self.auction(module)
                self.act("pass")
                self.assertEqual(
                    self.s["current_player"], "p1" if module is engine1889 else "p3"
                )
                self.reject("pass", player="p2")
                self.act("pass")
                self.assertEqual(self.s["privates"][self.company]["owner"], "p2")
                start_cash = 420 if module is engine1889 else 600
                self.assertEqual(
                    self.s["players"]["p2"]["cash"], start_cash - self.face - 15
                )
                self.assertEqual(self.s["players"]["p1"]["cash"], start_cash)
                self.assertEqual(self.s["auction"]["bids"][self.company], {})
                self.assertEqual(self.s["current_player"], "p1")

    def test_raise_preserves_variant_bidder_order_and_refunds_losers(self):
        for module in (engine1830, engine1889):
            with self.subTest(variant=module.__name__):
                self.auction(module)
                self.act("bid", company=self.company, price=self.face + 20)
                self.assertEqual(
                    self.s["current_player"], "p1" if module is engine1889 else "p3"
                )
                self.act("pass")
                self.assertEqual(self.s["current_player"], "p2")
                self.act("bid", company=self.company, price=self.face + 25)
                self.assertEqual(
                    self.s["current_player"], "p3" if module is engine1889 else "p1"
                )
                self.act("pass")
                self.assertEqual(self.s["privates"][self.company]["owner"], "p2")
                start_cash = 420 if module is engine1889 else 600
                self.assertEqual(
                    self.s["players"]["p2"]["cash"], start_cash - self.face - 25
                )
                self.assertEqual(self.s["players"]["p1"]["cash"], start_cash)

    def test_only_original_bidders_may_raise_and_minimum_is_highest_plus_five(self):
        for module in (engine1830, engine1889):
            with self.subTest(variant=module.__name__):
                self.auction(module)
                self.reject(
                    "bid", player="p4", company=self.company, price=self.face + 20
                )
                self.reject("bid", company=self.company, price=self.face + 19)
                self.act("pass")
                self.reject(
                    "bid",
                    player="p3" if module is engine1889 else "p1",
                    company=self.company,
                    price=self.face + 20,
                )
                self.s = json.loads(json.dumps(self.s))
                self.assertEqual(
                    self.s["current_player"], "p1" if module is engine1889 else "p3"
                )
                self.act("bid", company=self.company, price=self.face + 20)
                self.assertEqual(self.s["current_player"], "p2")


class EmergencyBlock1889Tests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.Rules1889Tests("runTest")
        self.f.setUp()
        self.f.operating()
        self.f.route()
        self.f.train_step()
        self.f.cash(self.f.s["corporations"]["IR"], 0)
        self.f.cash(self.f.s["players"]["p1"], 0)
        self.f.shares("AR", "p1", 50)
        E._position(self.f.s, self.f.s["corporations"]["AR"], [10, 0])

    def test_repeat_block_rejected_atomically_even_when_still_short(self):
        self.f.act("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(self.f.s["players"]["p1"]["cash"], 10)
        self.f.reject("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(self.f.s["corporations"]["AR"]["pool"], 10)

    def test_one_larger_block_gets_pre_sale_price_for_every_share(self):
        self.f.act("emergency_sell", corporation="AR", percent=30)
        self.assertEqual(self.f.s["players"]["p1"]["cash"], 30)
        self.assertEqual(self.f.s["corporations"]["AR"]["holdings"]["p1"], 20)
        self.f.reject("emergency_sell", corporation="AR", percent=10)

    def test_another_corporation_can_still_be_sold(self):
        self.f.shares("SR", "p2", 20)
        self.f.shares("SR", "p1", 10)
        E._position(self.f.s, self.f.s["corporations"]["SR"], [10, 1])
        self.f.act("emergency_sell", corporation="AR", percent=10)
        self.f.act("emergency_sell", corporation="SR", percent=10)
        self.assertEqual(self.f.s["players"]["p1"]["cash"], 30)

    def test_failed_sale_does_not_consume_block(self):
        self.f.reject("emergency_sell", corporation="AR", percent=40)
        self.f.act("emergency_sell", corporation="AR", percent=30)
        self.assertEqual(self.f.s["corporations"]["AR"]["pool"], 30)

    def test_block_survives_json_restore_and_cannot_be_bypassed_by_stock_sale(self):
        self.f.act("emergency_sell", corporation="AR", percent=10)
        self.f.s = engine1889.migrate_state(json.loads(json.dumps(self.f.s)))
        self.f.reject("emergency_sell", corporation="AR", percent=10)
        self.f.reject("sell_shares", corporation="AR", percent=10)

    def test_next_operating_turn_has_a_new_sale_block(self):
        self.f.act("emergency_sell", corporation="AR", percent=10)
        E._start_corporation(self.f.s)
        self.f.train_step()
        self.f.act("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(self.f.s["corporations"]["AR"]["pool"], 20)

    def test_bankruptcy_estimate_and_liquidation_respect_consumed_blocks(self):
        E._position(self.f.s, self.f.s["corporations"]["IR"], [10, 0])
        self.f.act("emergency_sell", corporation="AR", percent=10)
        self.assertEqual(E._maximum_emergency_sale(self.f.s, "p1", "AR"), 0)
        self.f.act("bankrupt")
        self.assertEqual(self.f.s["end_reason"], "bankruptcy")
        self.assertEqual(self.f.s["corporations"]["AR"]["pool"], 10)
        self.assertEqual(self.f.s["players"]["p1"]["cash"], 0)


if __name__ == "__main__":
    unittest.main()
