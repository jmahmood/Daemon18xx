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
        self.assertFalse(self.board.doesPathExist(start='f24-1', end='New York'))
        pc = self.public_companies[0]
        self.assertEqual(self.board.game_map.getCompanyTokens(pc), [])

        # Company has not yet placed anything, therefore it shouldn't have much of a graph.
        company_graph = self.board.game_map.generateCompanyGraph(pc)
        # This should have all the nodes but none of the edges.
        self.assertEqual(len(company_graph.nodes), len(self.board.game_map.graph.nodes))
        self.assertEqual(len(company_graph.edges), 0)

    def testTokenPlacement(self):
        """If you have no tokens, you must place a token to start"""
        move = OperatingRoundMove()
        pc = self.public_companies[0]
        token_hex = self.all_hextypes[pc.base]

        move.purchase_token = True
        move.construct_track = False  # TODO: P4: Should we call this place_track instead?
        move.run_route = False
        move.buy_train = False
        move.pay_dividend = False
        move.routes = False
        move.public_company = pc
        move.token = Token(token_hex.cities[0], pc, pc.base)

        mgs = MutableGameState()
        mgs.board = self.board

        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))



