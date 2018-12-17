"""Basic coverage"""
import networkx as nx

from app.base import PublicCompany, Token, Track, City, Town, TrackType, PrivateCompany
from app.game_map import MapHexConfig, GameBoard
from app.minigames.OperatingRound.minigame_operatinground import OperatingRound
import unittest

from app.minigames.OperatingRound.operating_round import OperatingRoundMove
from app.state import MutableGameState


class ORBaseClass(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.private_companies = PrivateCompany.load()
        self.public_companies = PublicCompany.load()
        self.cities = City.load()
        self.towns = Town.load()
        self.all_tracks_types = TrackType.load()
        self.all_hextypes = MapHexConfig.load()
        self.board = GameBoard.initialize()

    def executeGenericTilePlacement(self, company_short_name="CPR", location=None, track_id=199, track_rotation=0):
        move, mgs, pc = self.genericValidTilePlacement(company_short_name, location, track_id, track_rotation)
        mg_or = OperatingRound()
        mg_or.constructTrack(move, mgs)

    def genericValidTilePlacement(self, company_short_name="CPR", location=None, track_id=199, track_rotation=0):
        if location is None:
            raise AttributeError(
                "You must set a location before doing a tile placement. There is no generic tile placement location")
        move = OperatingRoundMove()
        move.track_type_id = track_id

        pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == company_short_name)
        pc.cash = 500000

        move.construct_track = True  # TODO: P4: Should we call this place_track instead?
        move.public_company = pc
        generic_test_track = self.board.getAvailableTrack(move.track_type_id)

        move.track = generic_test_track.rotate(track_rotation)
        move.track_placement_location = location

        mgs = MutableGameState()
        mgs.board = self.board
        mgs.public_companies = self.public_companies
        mgs.private_companies = self.private_companies

        return move, mgs, pc

    def genericValidInitialTokenPlacement(self, company_short_name="CPR") -> (
            OperatingRoundMove, MutableGameState, PublicCompany):
        move = OperatingRoundMove()
        pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == company_short_name)
        token_hex = self.all_hextypes[pc.base]
        move.purchase_token = True
        move.public_company = pc
        move.token = Token(token_hex.cities[0], pc, pc.base)

        mgs = MutableGameState()
        mgs.board = self.board
        mgs.public_companies = self.public_companies
        mgs.private_companies = self.private_companies

        return move, mgs, pc


class TrainPurchaseTests(ORBaseClass):
    def testValidPurchase(self):
        raise NotImplemented()

    # Valid edge cases

    def testValidSameCitiesDifferentRoutes(self):
        """You can start or end in the same city; that is fine.
        You only cannot reuse the same tracks to do so (or the same station)"""
        raise NotImplemented()

    def testTrainBoughtFromOtherCompany(self):
        raise NotImplemented()

    def testDieselCostsLessWithTradein(self):
        raise NotImplemented()

    def testPhaseChangeOccursWhileBuyingTrain(self):
        raise NotImplemented()

    def testCanTradeFirst4TrainForDiesel(self):
        raise NotImplemented()

    def testExcessTrainsForSale(self):
        raise NotImplemented()

    def testForcedTrainPurchase(self):
        raise NotImplemented

    # Invalid conditions

    def testTooPoor(self):
        raise NotImplemented()

    def testTrainNotAvailable(self):
        raise NotImplemented()

    def testTrainLimitExceeded(self):
        raise NotImplemented()


class DividendPaymentTests(ORBaseClass):
    def testValidDividendPayout(self):
        raise NotImplemented()

    def testValidHordeCash(self):
        raise NotImplemented()

    # Valid edge cases

    # Invalid conditions


class RouteTests(ORBaseClass):
    def testValidRoute(self):
        raise NotImplemented()

    # Valid edge cases

    def testValidSameCitiesDifferentRoutes(self):
        """You can start or end in the same city; that is fine.
        You only cannot reuse the same tracks to do so (or the same station)"""
        raise NotImplemented()

    # Invalid conditions

    def testOnlyOneCity(self):
        raise NotImplemented()

    def testRouteTooBigForAvailableTrain(self):
        raise NotImplemented()

    def testRoutesNotDisjoint(self):
        raise NotImplemented()

    def testStationsNotDisjoint(self):
        raise NotImplemented()

    def testNoStations(self):
        raise NotImplemented()

    def testNotEnoughTrainsAvailable(self):
        raise NotImplemented()


class TokenPlacementTests(ORBaseClass):
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

    def testValidTokenPlacement(self):
        """If you have no tokens, you must place a token to start"""

        # CPR uses a gray tile, so it should be inserted from the start
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(mg_or.error_list), 0)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

    def testInvalidTokenPlacementFirstPlacementWrongBaseLocation(self):
        """Your first token MUST be placed on your home city"""
        move, mgs, pc = self.genericValidInitialTokenPlacement()

        different_pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == "B&O")
        different_pc_token_hex = self.all_hextypes[different_pc.base]

        move.token = Token(different_pc_token_hex.cities[0], pc, different_pc_token_hex.location)

        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn("Your first token needs to be in your company's base location: {}".format(pc.base),
                      mg_or.error_list)

    def testInvalidTokenPlacementAnotherPublicCompanyToken(self):
        """Public Company #1 cannot place tokens for Public Company #2, even if it is in the correct space."""
        move, mgs, pc = self.genericValidInitialTokenPlacement()

        different_pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == "B&O")
        different_pc_token_hex = self.all_hextypes[different_pc.base]

        move.token = Token(different_pc_token_hex.cities[0], different_pc, different_pc_token_hex.location)

        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn("You can only place a token for your own company ({}, {})".format(move.public_company.name,
                                                                                        move.token.public_company.name),
                      mg_or.error_list)

    # TODO: P2: Check to see if you can correctly place the second track

    def testInvalidTokenPlacementNoTrackExists(self):
        """Public Company #1 cannot place tokens for Public Company #2, even if it is in the correct space."""
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()

        # First placement is executed.
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))

        # one round later..

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        ottawa = next((city for city in self.cities if city.name == "Ottawa"))
        move.token = Token(ottawa, pc, ottawa.location)
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn("There is no track there",
                      mg_or.error_list)

    def testInvalidConnectionBostonAtlanticCity(self):
        self.assertFalse(self.board.doesPathExist(start='Boston', end='Atlantic City'),
                         self.board.shortestPath(start="Boston", end="Atlantic City"))

    def testInvalidTokenPlacementCannotStealHQ(self):
        """Tokens may not be placed so as to block the base city of a Corporation which is not yet in operation"""
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        self.assertEqual(len(mg_or.error_list), 0)
        self.assertEqual(len(mgs.board.findCompanyTokenCities(move.public_company)), 0)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(mgs.board.findCompanyTokenCities(move.public_company)), 1)
        self.assertFalse(self.board.doesPathExist(start='Montreal', end='Boston'))
        self.assertFalse(self.board.doesPathExist(start='Montreal', end='Atlantic City'))

        self.executeGenericTilePlacement(location="b18", track_id=198, track_rotation=2)
        self.executeGenericTilePlacement(location="c19", track_id=9, track_rotation=1)
        self.executeGenericTilePlacement(location="d20", track_id=198, track_rotation=1)
        self.executeGenericTilePlacement(location="d22", track_id=9, track_rotation=0)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='Boston'))

        move = OperatingRoundMove()
        pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        token_hex = self.all_hextypes["e23"]
        move.purchase_token = True
        move.public_company = pc
        move.token = Token(token_hex.cities[0], pc, "e23")
        self.board.game_map.regenerateCompanyGraph(pc)

        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "Tokens may not be placed so as to block the base city of a Corporation which is not yet in operation",
            mg_or.error_list
        )

    def testInvalidTokenPlacementNoTokensLeft(self):
        raise NotImplemented()

    def testInvalidTokenPlacementAlreadyHaveStation(self):
        raise NotImplemented()

    def testInvalidTokenPlacementNoConnection(self):
        raise NotImplemented()

    def testInvalidTokenPlacementNoSpaceAvailable(self):
        raise NotImplemented()

    def testInvalidTokenPlacementNotCity(self):
        raise NotImplemented()

    def testInvalidTokenPlacementNoTrackNewYorkCentral(self):
        """New York Central's primary location has no pre-existing track and needs you to place one before you can
        place your token (I think)"""
        raise NotImplemented()

    def testInvalidTokenPlacementEerie(self):
        """Eerie has a special rule that prevents you from placing a tile into Buffalo or Dunkirk until it has already
        gone public w/ a token of its own"""
        raise NotImplemented()

    def testInvalidTokenLocationDoesntExist(self):
        raise NotImplemented()

    def testInvalidTokenLocationIsNotCity(self):
        raise NotImplemented()

    def testInvalidTokenTooPoor(self):
        raise NotImplemented()


class TrackPlacementTests(ORBaseClass):
    def setUp(self):
        super().setUp()
        self.private_companies = PrivateCompany.load()
        self.public_companies = PublicCompany.load()
        self.cities = City.load()
        self.towns = Town.load()
        self.all_tracks_types = TrackType.load()
        self.all_hextypes = MapHexConfig.load()
        self.board = GameBoard.initialize()

    def testValidInitialTrackPlacement(self):
        # CPR uses a gray tile, so it should be inserted from the start

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        move, mgs, pc = self.genericValidTilePlacement(location="b18", track_rotation=1)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        mg_or.constructTrack(move, mgs)
        self.assertEqual(len(mg_or.error_list), 0)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='a17-6'))

    def testInvalidInitialTrackPlacement(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTilePlacement(location="b22", track_rotation=3)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        error = ("Your track needs to connect to your track or it needs to be your originating city, "
                 "except in special cases (the base cities of the NYC and Erie, "
                 "and the hexagons containing the C&SL and D&H Private Companies)")

        self.assertIn(error, mg_or.error_list, mg_or.error_list)

    def testInvalidTrackUnavailableTrack(self):
        """Uh oh.

            The way Tracks work is that we get a track id in a JSON file or something like that.
            However, we need to convert that to a Track, and we appear to be doing that outside
            the normal validation step.
        """
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        move, mgs, pc = self.genericValidTilePlacement(location="b18", track_rotation=1, track_id=200)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            """The track you selected is not available. {}""".format("200"),
            mg_or.error_list,
            mg_or.error_list,
        )

    def testInvalidTrackLocationDoesntExist(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        move, mgs, pc = self.genericValidTilePlacement(location="z99", track_rotation=1, track_id=200)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            """Your track needs to be on a location that exists""",
            mg_or.error_list,
            mg_or.error_list,
        )

    def testInvalidTrackConnectionToNeighbours(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        move, mgs, pc = self.genericValidTilePlacement(location="b18", track_rotation=0)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        error = ("Your track needs to connect to your track or it needs to be your originating city, "
                 "except in special cases (the base cities of the NYC and Erie, "
                 "and the hexagons containing the C&SL and D&H Private Companies)")

        self.assertIn(error, mg_or.error_list, mg_or.error_list)

    def testValidTrackConnectionToNeighbours(self):
        """Actually, I was wrong;
        https://boardgamegeek.com/article/13142170#13142170
        there is no requirement that a track lay has to connect to any track
        on another tile - except to preserve connections already present (not
        applicable in this case as there is no tile there already).

        You don't need to connect to the neighbour tracks.
        """
        pass

    def testInvalidTrackPlacementCannotStealPrivateCompanyLand(self):
        """
        From the rules: 6.2.2 (4) A railroad may not place a tile on a hex containing a private
        company owned by a player. A railroad may place a tile on a
        hex containing a private company that is closed or owned by a
        railroad.
        :return:
        """

        raise NotImplemented()

    def testTrackPlacementCanBuildOnOwnedPrivateCompanyLand(self):
        raise NotImplemented()

    def testTrackUpgrade(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        self.executeGenericTilePlacement(location="b18", track_rotation=1)

        move, mgs, pc = self.genericValidTilePlacement(track_id=197, location="b18", track_rotation=1)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())

    def testInvalidTrackUpgrade(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        self.executeGenericTilePlacement(location="b18", track_rotation=1)

        move, mgs, pc = self.genericValidTilePlacement(track_id=198, location="b18", track_rotation=1)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "Replacement tiles must maintain all previously existing route connections",
            mg_or.error_list,
            mg_or.error_list,
        )

        self.assertIn(
            "You cannot replace the current track with the track you selected"
            "; current: {}, yours: {} ({})".format("199", "198", "b18"),
            mg_or.error_list,
            mg_or.error_list,
        )

    def testInvalidTrackTooPoor(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        move, mgs, pc = self.genericValidTilePlacement(location="b18", track_rotation=1)
        move.public_company.cash = 15
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        print(mg_or.error_list)

    def testInvalidTrackCityTooSmall(self):
        """"AKA: Placing a 1 city tile on a 2 city hex"""
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="B&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTilePlacement(company_short_name="B&O", track_id=198, location="i17", track_rotation=0)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        mg_or.constructTrack(move, mgs)
        self.assertTrue(self.board.doesPathExist(start='Baltimore', end='i17-3'))
        mgs.board.game_map.regenerateCompanyGraph(move.public_company)
        self.assertTrue(self.board.doesRouteExist(move.public_company, start='Baltimore', end='i17-3'))
        self.assertTrue(self.board.doesPathExist(start='Baltimore', end='h18-6'))

        move, mgs, pc = self.genericValidTilePlacement(company_short_name="B&O", track_id=169, location="h18", track_rotation=5)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "That location requires you to use a tile that has two cities",
            mg_or.error_list
        )

    def testInvalidTrackCityTooLarge(self):
        """"AKA: Placing a 2 city tile on a 1 city hex"""
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="B&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTilePlacement(company_short_name="B&O", track_id=179, location="j14", track_rotation=2)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "That location requires you to use a tile that has one city",
            mg_or.error_list
        )

    def testInvalidTrackTownTooSmall(self):
        raise NotImplemented()

    def testInvalidTrackTownTooLarge(self):
        raise NotImplemented()
