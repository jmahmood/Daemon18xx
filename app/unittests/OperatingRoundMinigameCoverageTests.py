"""Basic coverage"""
from app.base import PublicCompany, Token, Track, City, Town, TrackType, PrivateCompany
from app.game_map import MapHexConfig, GameBoard
from app.minigames.OperatingRound.minigame_operatinground import OperatingRound
import unittest

from app.minigames.OperatingRound.operating_round import OperatingRoundMove
from app.state import MutableGameState


class OperatingRoundMinigame(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.private_companies = PrivateCompany.load()
        self.public_companies = PublicCompany.load()
        self.cities = City.load()
        self.towns = Town.load()
        self.all_tracks = TrackType.load()
        self.all_hextypes = MapHexConfig.load()
        self.board = GameBoard.initialize()

    def testGameBoardInitializationTest(self):
        self.assertTrue(self.board.doesPathExist(start='f24-1', end='f24-2'))
        self.assertTrue(self.board.doesPathExist(start='f24-1', end='d24-1'))
        self.assertTrue(self.board.doesPathExist(start='f24-1', end='Boston'))

    #
    # def testPurchaseToken(self):
    #     move = OperatingRoundMove()
    #     move.purchase_token = True
    #     move.construct_track = True  # TODO: P4: Should we call this place_track instead?
    #     move.run_route = False
    #     move.buy_train = False
    #     move.pay_dividend = False
    #     move.routes = False
    #     move.public_company = PublicCompany()
    #     move.token = Token(self.cities[0], self.public_companies[0], self.cities[0].map_hex_name)
    #     # move.track = Track()
    #     move.track_placement_location = "A1"
    #
    #     mgs = MutableGameState()
    #     mgs.board = self.board
    #
    #     mg_or = OperatingRound()
    #
    #     # mg_or.isValidTrackPlacement(move, mgs)


