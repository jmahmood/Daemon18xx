"""Basic coverage"""
from app.base import PublicCompany, Token, Track, City, Town, TrackType
from app.minigames.OperatingRound.minigame_operatinground import OperatingRound
import unittest

from app.minigames.OperatingRound.operating_round import OperatingRoundMove


class SimulateFirstStockRoundTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.cities = City.load()
        self.towns = Town.load()
        self.all_tracks = TrackType.load()



    def testPurchaseToken(self):

        move = OperatingRoundMove()
        move.purchase_token = True
        move.construct_track = True
        move.run_route = False
        move.buy_train = False
        move.pay_dividend = False
        move.routes = False
        move.public_company = PublicCompany()
        move.token = Token()
        move.track = Track()
        move.track_placement_location = "A1"



        mg_or = OperatingRound()
