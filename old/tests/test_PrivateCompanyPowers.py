"""Tests for private company special powers."""

import unittest
import importlib
from app.base import (
    Player, PublicCompany, PrivateCompany, MutableGameState, GameBoard,
    Color, TerrainType, PowerType, Train, Route, Tile,
    SpecialPower, ExtraTokenPower, RevenueBonusPower, FreeTrackPower,
    TerrainDiscountPower, TrainDiscountPower
)
from app.minigames.operating_round import OperatingRound, OperatingRoundMove

cfg = importlib.import_module('app.config.1830')


class SpecialPowerTests(unittest.TestCase):
    """Tests for the SpecialPower base class."""

    def test_power_creation(self):
        """Power can be created with correct attributes."""
        power = SpecialPower(
            power_type=PowerType.EXTRA_TOKEN,
            description="Test power",
            active=True
        )
        self.assertEqual(power.power_type, PowerType.EXTRA_TOKEN)
        self.assertTrue(power.active)
        self.assertTrue(power.can_use())

    def test_power_with_limited_uses(self):
        """Power with limited uses decrements correctly."""
        power = SpecialPower(
            power_type=PowerType.FREE_TRACK,
            description="One-time track",
            uses_remaining=1
        )
        self.assertTrue(power.can_use())

        power.use()
        self.assertEqual(power.uses_remaining, 0)
        self.assertFalse(power.can_use())

    def test_power_expires_on_use(self):
        """Power marked to expire deactivates after use."""
        power = SpecialPower(
            power_type=PowerType.REVENUE_BONUS,
            description="One-shot bonus",
            expires_on_use=True
        )
        self.assertTrue(power.active)

        power.use()
        self.assertFalse(power.active)
        self.assertFalse(power.can_use())

    def test_power_deactivation(self):
        """Power can be manually deactivated."""
        power = SpecialPower(
            power_type=PowerType.EXTRA_TOKEN,
            description="Test power"
        )
        power.deactivate()
        self.assertFalse(power.active)
        self.assertFalse(power.can_use())


class RevenueBonusPowerTests(unittest.TestCase):
    """Tests for revenue bonus powers."""

    def test_fixed_bonus(self):
        """Fixed bonus adds correctly to revenue."""
        power = RevenueBonusPower(
            power_type=PowerType.REVENUE_BONUS,
            description="+$20 bonus",
            bonus_amount=20,
            bonus_multiplier=1.0
        )
        self.assertEqual(power.apply_bonus(100), 120)

    def test_multiplier_bonus(self):
        """Multiplier bonus increases revenue correctly."""
        power = RevenueBonusPower(
            power_type=PowerType.REVENUE_BONUS,
            description="+20% bonus",
            bonus_amount=0,
            bonus_multiplier=1.2
        )
        self.assertEqual(power.apply_bonus(100), 120)

    def test_combined_bonus(self):
        """Combined bonus applies both multiplier and fixed amount."""
        power = RevenueBonusPower(
            power_type=PowerType.REVENUE_BONUS,
            description="+20% and +$10",
            bonus_amount=10,
            bonus_multiplier=1.2
        )
        # (100 * 1.2) + 10 = 130
        self.assertEqual(power.apply_bonus(100), 130)


class FreeTrackPowerTests(unittest.TestCase):
    """Tests for free track powers."""

    def test_completely_free_track(self):
        """100% discount makes track free."""
        power = FreeTrackPower(
            power_type=PowerType.FREE_TRACK,
            description="Free track",
            discount_percent=1.0
        )
        self.assertEqual(power.get_discount_multiplier(), 0.0)

    def test_partial_discount(self):
        """Partial discount reduces cost correctly."""
        power = FreeTrackPower(
            power_type=PowerType.FREE_TRACK,
            description="Half price track",
            discount_percent=0.5
        )
        self.assertEqual(power.get_discount_multiplier(), 0.5)

    def test_color_specific_discount(self):
        """Discount applies only to specified colors."""
        power = FreeTrackPower(
            power_type=PowerType.FREE_TRACK,
            description="Free yellow track",
            discount_percent=1.0,
            tile_colors=[Color.YELLOW]
        )
        self.assertEqual(power.get_discount_multiplier(Color.YELLOW), 0.0)
        self.assertEqual(power.get_discount_multiplier(Color.GREEN), 1.0)


class TerrainDiscountPowerTests(unittest.TestCase):
    """Tests for terrain discount powers."""

    def test_ignore_all_terrain(self):
        """Power can ignore all terrain costs."""
        power = TerrainDiscountPower(
            power_type=PowerType.TERRAIN_DISCOUNT,
            description="Ignore terrain",
            discount_percent=1.0
        )
        self.assertTrue(power.applies_to_terrain(TerrainType.MOUNTAIN))
        self.assertTrue(power.applies_to_terrain(TerrainType.BRIDGE))

    def test_specific_terrain_only(self):
        """Power applies only to specific terrain types."""
        power = TerrainDiscountPower(
            power_type=PowerType.TERRAIN_DISCOUNT,
            description="Ignore mountains",
            discount_percent=1.0,
            terrain_types=[TerrainType.MOUNTAIN]
        )
        self.assertTrue(power.applies_to_terrain(TerrainType.MOUNTAIN))
        self.assertFalse(power.applies_to_terrain(TerrainType.BRIDGE))


class TrainDiscountPowerTests(unittest.TestCase):
    """Tests for train discount powers."""

    def test_fixed_discount(self):
        """Fixed discount reduces train cost correctly."""
        power = TrainDiscountPower(
            power_type=PowerType.TRAIN_DISCOUNT,
            description="$50 off trains",
            discount_amount=50
        )
        self.assertEqual(power.apply_discount(200), 150)

    def test_percentage_discount(self):
        """Percentage discount reduces train cost correctly."""
        power = TrainDiscountPower(
            power_type=PowerType.TRAIN_DISCOUNT,
            description="20% off trains",
            discount_percent=0.2
        )
        self.assertEqual(power.apply_discount(200), 160)

    def test_combined_discount(self):
        """Combined discount applies both percentage and fixed."""
        power = TrainDiscountPower(
            power_type=PowerType.TRAIN_DISCOUNT,
            description="20% + $20 off",
            discount_amount=20,
            discount_percent=0.2
        )
        # (200 * 0.8) - 20 = 140
        self.assertEqual(power.apply_discount(200), 140)

    def test_discount_floor_at_zero(self):
        """Discount cannot make train cost negative."""
        power = TrainDiscountPower(
            power_type=PowerType.TRAIN_DISCOUNT,
            description="$300 off",
            discount_amount=300
        )
        self.assertEqual(power.apply_discount(200), 0)


class PrivateCompanyPowerIntegrationTests(unittest.TestCase):
    """Tests for private company power integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.cash = 500
        self.company.trains = [Train("2", 100)]

        self.private_company = PrivateCompany.initiate(
            order=1,
            name="Test Private",
            short_name="TP",
            cost=50,
            revenue=10,
            base="A1"
        )
        self.private_company.belongs_to_company = self.company

        self.state = MutableGameState()
        self.state.players = [self.player]
        self.state.public_companies = [self.company]
        self.state.private_companies = [self.private_company]
        self.state.track_laid = set()

        self.board = GameBoard()

    def test_private_company_with_no_powers(self):
        """Private company with no powers works normally."""
        self.assertEqual(len(self.private_company.special_powers), 0)
        self.assertFalse(self.private_company.has_active_power(PowerType.FREE_TRACK))

    def test_private_company_with_revenue_bonus(self):
        """Private company with revenue bonus applies correctly."""
        bonus_power = RevenueBonusPower(
            power_type=PowerType.REVENUE_BONUS,
            description="+$20 revenue",
            bonus_amount=20
        )
        self.private_company.special_powers = [bonus_power]

        self.assertTrue(self.private_company.has_active_power(PowerType.REVENUE_BONUS))
        powers = self.private_company.get_powers_by_type(PowerType.REVENUE_BONUS)
        self.assertEqual(len(powers), 1)
        self.assertEqual(powers[0].apply_bonus(50), 70)

    def test_private_company_with_multiple_powers(self):
        """Private company can have multiple different powers."""
        powers = [
            RevenueBonusPower(
                power_type=PowerType.REVENUE_BONUS,
                description="+$10 revenue",
                bonus_amount=10
            ),
            FreeTrackPower(
                power_type=PowerType.FREE_TRACK,
                description="Free yellow track",
                discount_percent=1.0,
                tile_colors=[Color.YELLOW]
            )
        ]
        self.private_company.special_powers = powers

        self.assertTrue(self.private_company.has_active_power(PowerType.REVENUE_BONUS))
        self.assertTrue(self.private_company.has_active_power(PowerType.FREE_TRACK))
        self.assertFalse(self.private_company.has_active_power(PowerType.TRAIN_DISCOUNT))


class OperatingRoundPowerIntegrationTests(unittest.TestCase):
    """Tests for power integration in operating round."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Player.create("TestPlayer", 1000, 0)
        self.company = PublicCompany.initiate(
            id="TEST",
            name="Test Company",
            short_name="TC",
            tokens_available=4,
            token_costs=[0, 40, 60, 80]
        )
        self.company.president = self.player
        self.company.cash = 500
        self.company.trains = [Train("2", 100)]

        self.private_company = PrivateCompany.initiate(
            order=1,
            name="Test Private",
            short_name="TP",
            cost=50,
            revenue=10,
            base="A1"
        )
        self.private_company.belongs_to_company = self.company

        self.state = MutableGameState()
        self.state.players = [self.player]
        self.state.public_companies = [self.company]
        self.state.private_companies = [self.private_company]
        self.state.track_laid = set()

        self.board = GameBoard()
        # Add a token so track placement is valid
        from app.base import Token
        token = Token(self.company, "A1", 0)
        self.board.setToken(token)

    def test_free_track_power_reduces_cost(self):
        """Free track power makes track laying free."""
        # Add free track power
        power = FreeTrackPower(
            power_type=PowerType.FREE_TRACK,
            description="Free yellow track",
            discount_percent=1.0,
            tile_colors=[Color.YELLOW]
        )
        self.private_company.special_powers = [power]

        # Create track laying move
        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.public_company = self.company
        move.construct_track = True
        move.track = Tile(
            id="1",
            id_v2="1",
            color=Color.YELLOW,
            location="A2",
            rotation=0
        )

        initial_cash = self.company.cash
        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Yellow track is free in 1830, so power doesn't matter here
        # but it should still work
        self.assertEqual(self.company.cash, initial_cash)

    def test_terrain_discount_power_reduces_mountain_cost(self):
        """Terrain discount power reduces mountain costs."""
        # Add terrain discount power
        power = TerrainDiscountPower(
            power_type=PowerType.TERRAIN_DISCOUNT,
            description="Ignore mountains",
            discount_percent=1.0,
            terrain_types=[TerrainType.MOUNTAIN]
        )
        self.private_company.special_powers = [power]

        # Create track on mountain terrain (BROWN costs 100 in 1830)
        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.public_company = self.company
        move.construct_track = True
        move.track = Tile(
            id="3",
            id_v2="3",
            color=Color.BROWN,
            location="A2",
            rotation=0,
            terrain=TerrainType.MOUNTAIN
        )

        # Place green track first (upgrade path: Yellow -> Green -> Brown)
        green_tile = Tile("2", "2", Color.GREEN, "A2", 0)
        self.board.setTrack(green_tile)

        initial_cash = self.company.cash
        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result, f"Move failed: {oround.errors()}")
        # Brown track normally costs 100, mountain doubles to 200
        # Power ignores mountain, so cost should be 100
        expected_cost = 100
        self.assertEqual(self.company.cash, initial_cash - expected_cost,
                        f"Expected {expected_cost} cost, but cash changed from {initial_cash} to {self.company.cash}")


if __name__ == '__main__':
    unittest.main()
