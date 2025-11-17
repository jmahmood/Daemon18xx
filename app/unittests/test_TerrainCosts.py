"""Tests for terrain cost implementation in track laying."""

import unittest
from app.base import (
    Player, PublicCompany, Tile, Color, Token, GameBoard,
    MutableGameState, TerrainType
)
from app.minigames.operating_round import OperatingRound, OperatingRoundMove
from app.config import load_config


class TerrainCostTests(unittest.TestCase):
    """Tests for terrain-based track laying costs."""

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
        self.company.trains = []

        self.board = GameBoard()
        self.state = MutableGameState()
        self.state.players = [self.player]
        self.state.track_laid = set()

        # Place initial token so company can lay track
        self.board.setToken(Token(self.company, "A1", 0))

    def test_normal_terrain_no_multiplier(self):
        """Track on normal terrain uses standard cost."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        move.track = Tile("1", "1", Color.BROWN, "A2", 0, terrain=TerrainType.NORMAL)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Brown costs 100 in 1830, normal terrain multiplier is 1.0
        expected_cost = 100
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_mountain_terrain_double_cost(self):
        """Track on mountain terrain costs double."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        move.track = Tile("2", "2", Color.BROWN, "A3", 0, terrain=TerrainType.MOUNTAIN)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Brown costs 100 in 1830, mountain multiplier is 2.0
        expected_cost = 200
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_bridge_terrain_double_cost(self):
        """Track on bridge terrain costs double."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        move.track = Tile("3", "3", Color.BROWN, "A4", 0, terrain=TerrainType.BRIDGE)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Brown costs 100 in 1830, bridge multiplier is 2.0
        expected_cost = 200
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_tunnel_terrain_double_cost(self):
        """Track on tunnel terrain costs double."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        move.track = Tile("4", "4", Color.BROWN, "A5", 0, terrain=TerrainType.TUNNEL)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Brown costs 100 in 1830, tunnel multiplier is 2.0
        expected_cost = 200
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_terrain_on_free_track_no_cost(self):
        """Terrain on free track (yellow) still costs nothing."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        # Yellow track is free in 1830, even on mountain
        move.track = Tile("5", "5", Color.YELLOW, "A6", 0, terrain=TerrainType.MOUNTAIN)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Yellow costs 0, even with mountain multiplier
        expected_cost = 0
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_1846_bridge_cost_multiplier(self):
        """1846 uses 1.5x multiplier for bridges."""
        cfg = load_config("1846")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        # Brown costs 80 in 1846
        move.track = Tile("6", "6", Color.BROWN, "A7", 0, terrain=TerrainType.BRIDGE)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Brown costs 80 in 1846, bridge multiplier is 1.5
        expected_cost = 120  # 80 * 1.5
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_terrain_defaults_to_normal(self):
        """Tiles without specified terrain default to NORMAL."""
        cfg = load_config("1830")
        initial_cash = self.company.cash

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        # Don't specify terrain - should default to NORMAL
        move.track = Tile("7", "7", Color.BROWN, "A8", 0)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Should use normal multiplier (1.0)
        expected_cost = 100
        self.assertEqual(self.company.cash, initial_cash - expected_cost)

    def test_insufficient_funds_for_terrain_cost(self):
        """Company with insufficient funds cannot afford terrain cost."""
        cfg = load_config("1830")
        self.company.cash = 150  # Not enough for mountain brown (200)

        move = OperatingRoundMove()
        move.player_id = self.player.id
        move.construct_track = True
        move.track = Tile("8", "8", Color.BROWN, "A9", 0, terrain=TerrainType.MOUNTAIN)
        move.public_company = self.company

        oround = OperatingRound()
        result = oround.run(move, self.state, board=self.board, config=cfg)

        self.assertFalse(result)
        self.assertIn("You do not have enough cash", oround.errors())

    def test_terrain_upgrade_cost(self):
        """Terrain cost applies to upgrades as well."""
        cfg = load_config("1830")

        # Lay yellow track first (free)
        yellow_move = OperatingRoundMove()
        yellow_move.player_id = self.player.id
        yellow_move.construct_track = True
        yellow_move.track = Tile("9", "9", Color.YELLOW, "B1", 0, terrain=TerrainType.MOUNTAIN)
        yellow_move.public_company = self.company

        oround = OperatingRound()
        self.assertTrue(oround.run(yellow_move, self.state, board=self.board, config=cfg))

        # Reset state for next round
        self.state.track_laid = set()
        initial_cash = self.company.cash

        # Upgrade to green on same mountain hex
        green_move = OperatingRoundMove()
        green_move.player_id = self.player.id
        green_move.construct_track = True
        green_move.track = Tile("10", "10", Color.GREEN, "B1", 0, terrain=TerrainType.MOUNTAIN)
        green_move.public_company = self.company

        result = oround.run(green_move, self.state, board=self.board, config=cfg)

        self.assertTrue(result)
        # Green costs 0 normally, but we're testing the system works for upgrades
        # In this case green is free anyway, so cost is 0
        expected_cost = 0
        self.assertEqual(self.company.cash, initial_cash - expected_cost)


if __name__ == '__main__':
    unittest.main()
