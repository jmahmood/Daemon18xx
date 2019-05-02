"""Basic coverage"""
import networkx as nx

from app.base import PublicCompany, Token, Track, City, Town, TrackType, PrivateCompany, Train, TrainType
from app.game_map import MapHexConfig, GameBoard
from app.minigames.OperatingRound.minigame_operatinground import OperatingRound
import unittest

from app.minigames.OperatingRound.operating_round import OperatingRoundMove
from app.state import MutableGameState
from app.unittests.PrivateCompanyMinigameTests import fake_player


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

    def genericValidTrainPurchase(self, company_short_name="CPR",)  -> (
            OperatingRoundMove, MutableGameState, PublicCompany):
        """Create a Train Purchase Action"""
        move = OperatingRoundMove()
        pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == company_short_name)
        move.public_company = pc
        move.buy_train = True
        move.train_type = TrainType.A2TRAIN
        move.train_cost = 0  # The cost becomes the default cost.
        move.public_company.cash = 500000

        MutableGameState.players = [fake_player("A", 2000), fake_player("B", 2000), fake_player("C", 3000)]

        move.public_company.president = MutableGameState.players[0]


        mgs = MutableGameState()
        mgs.board = self.board
        mgs.game_phase = 2
        mgs.public_companies = self.public_companies
        mgs.private_companies = self.private_companies


        mgs.trains = [
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1)
        ]


        return move, mgs, pc


    def executeGenericTrackPlacement(self, company_short_name="CPR", location=None, track_id=199, track_rotation=0):
        move, mgs, pc = self.genericValidTrackPlacement(company_short_name, location, track_id, track_rotation)
        mg_or = OperatingRound()
        mg_or.constructTrack(move, mgs)


    def genericValidTrackPlacement(self, company_short_name="CPR", location=None, track_id=199, track_rotation=0):
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
        move.token_placement_location = pc.base

        mgs = MutableGameState()
        mgs.board = self.board
        mgs.public_companies = self.public_companies
        mgs.private_companies = self.private_companies

        return move, mgs, pc



class BankruptPlayerTrainPurchaseTests(ORBaseClass):
    def testTrainBoughtFromOtherCompany(self):
        raise NotImplemented()

    def testForcedTrainPurchase(self):
        raise NotImplemented



class PhaseChangeTrainPurchaseTests(ORBaseClass):
    pass

    def testExcessTrainsForSale(self):
        raise NotImplemented()


class TrainMultiplePurchaseTests(ORBaseClass):
    # When I developed this, I was under the mistaken impression that you could only
    # buy one train at a time.  Whoops.
    pass

class TrainPurchaseTests(ORBaseClass):
    """There are some complexities w/ Train purchases; the worst revolve around the bankruptcy case.

    If your company is
        1. Bankrupt or
        2. Have no Trains,

    you should get shunted into a different TrainPurchase system.
    """
    def testTrainDifference(self):
        trains = [
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1)
        ]

        buy_train = [next(t for t in trains if t.train == TrainType.A2TRAIN)]

        trains = list(set(trains) - set(buy_train))
        self.assertEqual(len(trains), 2)


    def testValidPurchase(self):
        move, mgs, pc = self.genericValidTrainPurchase(company_short_name="B&O")

        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTrainPurchase(move, mgs), mg_or.error_list)

        move._prepareTrain(mgs)

        self.assertIsNotNone(move.train)
        self.assertNotIn(move.train, move.public_company.trains)
        self.assertNotIn(move.train, mgs.unavailable_trains)
        self.assertIn(move.train, mgs.trains)

        mg_or.purchaseTrain(move, mgs)
        self.assertIn(move.train, move.public_company.trains)
        self.assertIn(move.train, mgs.unavailable_trains)
        self.assertNotIn(move.train, mgs.trains)

        self.assertEqual(move.public_company.cash, 500000 - 20)

    # Invalid conditions
    def testTooPoor(self):
        move, mgs, pc = self.genericValidTrainPurchase(company_short_name="B&O")
        move.public_company.cash = 10
        move.public_company.president.cash = 0

        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTrainPurchase(move, mgs), mg_or.error_list)


    def testPresidentPaysToo(self):
        move, mgs, pc = self.genericValidTrainPurchase(company_short_name="B&O")
        move.public_company.cash = 10
        move.public_company.president.cash = 10

        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTrainPurchase(move, mgs), mg_or.error_list)

        move._prepareTrain(mgs)

        mg_or.purchaseTrain(move, mgs)

        self.assertEqual(move.public_company.cash, 0)
        self.assertEqual(move.public_company.president.cash, 0)


    # Invalid conditions
    def testTrainNotAvailable(self):
        move, mgs, pc = self.genericValidTrainPurchase(company_short_name="B&O")
        move.public_company.cash = 10
        move.train_type = 89

        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTrainPurchase(move, mgs), mg_or.error_list)

    #
    # # Valid edge cases
    #
    # def testDieselCostsLessWithTradein(self):
    #     raise NotImplemented()
    #
    # def testPhaseChangeOccursWhileBuyingTrain(self):
    #     raise NotImplemented()
    #
    # def testCanTradeFirst4TrainForDiesel(self):
    #     raise NotImplemented()



    def testTrainLimitExceeded(self):
        # phase = 2
        move, mgs, pc = self.genericValidTrainPurchase(company_short_name="B&O")
        move.public_company.cash = 50
        move.train_type = 2

        mg_or = OperatingRound()

        move.public_company.trains = [
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1),
            Train(TrainType.A2TRAIN, 20, 1)
        ]

        self.assertFalse(mg_or.isValidTrainPurchase(move, mgs),
                         "Company already has {} trains; it is phase {}".format(
                            len(move.public_company.trains),
                            mgs.game_phase
                            )
                         )



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
        move.token_placement_location = different_pc_token_hex.location

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
        move.token_placement_location = different_pc_token_hex.location

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
        self.assertTrue(self.board.doesPathExist(start='d24-1', end='Boston'))

        self.executeGenericTrackPlacement(location="b18", track_id=198, track_rotation=2)
        self.board.game_map.regenerateCompanyGraph(pc)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='c19-2'))

        self.executeGenericTrackPlacement(location="c19", track_id=9, track_rotation=1)
        self.board.game_map.regenerateCompanyGraph(pc)

        self.assertTrue(self.board.doesPathExist(start='Montreal', end='c19-2'))
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='c19-5'))
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='d20-2'))

        self.executeGenericTrackPlacement(location="d20", track_id=198, track_rotation=1)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='d22-1'))
        self.board.game_map.regenerateCompanyGraph(pc)

        self.executeGenericTrackPlacement(location="d22", track_id=9, track_rotation=0)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='d22-1'))
        self.board.game_map.regenerateCompanyGraph(pc)
        self.assertTrue(self.board.doesPathExist(start='Montreal', end='Boston'))

        move = OperatingRoundMove()
        pc = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        token_hex = self.all_hextypes["e23"]
        move.purchase_token = True
        move.public_company = pc
        move.token = Token(token_hex.cities[0], pc, "e23")
        move.token_placement_location = "e23"
        self.board.game_map.regenerateCompanyGraph(pc)

        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "Tokens may not be placed so as to block the base city of a Corporation which is not yet in operation",
            mg_or.error_list
        )

    def testInvalidTokenPlacementNoTokensLeft(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        valid_cities = list(c for c in self.cities if c.name != "Montreal")  # Everything except CPR's home town.

        for i in range(4):
            self.board.setToken(
                public_company=cpr,
                city=valid_cities[i],
                location=valid_cities[i].location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "There are no remaining tokens for that company",
            mg_or.error_list
        )

    def testInvalidTokenPlacementAlreadyHaveStation(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        montreal = list(c for c in self.cities if c.name == "Montreal")[0]  # CPR's home town.

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "You cannot put two tokens for the same company in one location",
            mg_or.error_list
        )

    def testInvalidTokenPlacementNoConnection(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        montreal = next(c for c in self.cities if c.name == "Montreal")  # CPR's home town.
        valid_cities = list(c for c in self.cities if c.name != "Montreal")

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        move.token = Token(valid_cities[0], cpr, valid_cities[0].location)
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "You cannot connect to the location to place a token",
            mg_or.error_list
        )

    def testInvalidTokenPlacementNoSpaceAvailable(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        bo = next(pc1 for pc1 in self.public_companies if pc1.short_name == "B&O")
        montreal = next(c for c in self.cities if c.name == "Montreal")  # CPR's home town.

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        move.token = Token(montreal, bo, montreal.location)
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))
        self.assertIn(
            "There are no free spots to place a token: Max ({})".format(1),
            mg_or.error_list
        )

    def testInvalidTokenPlacementNotCity(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        montreal = next(c for c in self.cities if c.name == "Montreal")  # CPR's home town.

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        # Where should we catch this kind of invalid request?

        move.token_placement_location = "h2"
        move._prepareToken(mgs)
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))

        self.assertIn(
            "There are no cities available in that location {}".format(move.token_placement_location),
            mg_or.error_list
        )

    def testInvalidTokenPlacementNoTrackNewYorkCentral(self):
        """New York Central's primary location has no pre-existing track and needs you to place one before you can
        place your token (I think)"""
        # TODO: P3
        pass

    def testInvalidTokenPlacementEerie(self):
        """Eerie has a special rule that prevents you from placing a tile into Buffalo or Dunkirk until it has already
        gone public w/ a token of its own"""
        # TODO: P3
        pass

    def testInvalidTokenLocationDoesntExist(self):
        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        montreal = next(c for c in self.cities if c.name == "Montreal")  # CPR's home town.

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)

        move, mgs, pc = self.genericValidInitialTokenPlacement()
        # Where should we catch this kind of invalid request?

        move.token_placement_location = "a1"
        move._prepareToken(mgs)
        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))

        self.assertIn(
            "That is not a valid tile location {}".format(move.token_placement_location),
            mg_or.error_list
        )

    def testInvalidTokenTooPoor(self):

        cpr = next(pc1 for pc1 in self.public_companies if pc1.short_name == "CPR")
        montreal = next(c for c in self.cities if c.name == "Montreal")  # CPR's home town.

        self.board.setToken(
            public_company=cpr,
            city=montreal,
            location=montreal.location)


        washington = next(c for c in self.cities if c.name == "Washington")  # Second token should cost 40 bucks.

        move, mgs, pc = self.genericValidInitialTokenPlacement()

        move.token_placement_location = washington.location
        move.token_placement_city = "Washington"
        move.token = Token(
            city=washington,
            public_company=cpr,
            location=washington.location
        )
        move.public_company.cash = 0

        mg_or = OperatingRound()
        self.assertFalse(mg_or.isValidTokenPlacement(move, mgs))

        self.assertIn(
            "Too poor, it costs {} dollars".format(40),
            mg_or.error_list
        )


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

        move, mgs, pc = self.genericValidTrackPlacement(location="b18", track_rotation=1)
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

        move, mgs, pc = self.genericValidTrackPlacement(location="b22", track_rotation=3)
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

        move, mgs, pc = self.genericValidTrackPlacement(location="b18", track_rotation=1, track_id=200)
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

        move, mgs, pc = self.genericValidTrackPlacement(location="z99", track_rotation=1, track_id=200)
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

        move, mgs, pc = self.genericValidTrackPlacement(location="b18", track_rotation=0)

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

        self.executeGenericTrackPlacement(location="b18", track_rotation=1)

        move, mgs, pc = self.genericValidTrackPlacement(track_id=197, location="b18", track_rotation=1)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())

    def testInvalidTrackUpgrade(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement()
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs))
        mg_or.purchaseToken(move, mgs)

        self.executeGenericTrackPlacement(location="b18", track_rotation=1)

        move, mgs, pc = self.genericValidTrackPlacement(track_id=198, location="b18", track_rotation=1)
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

        move, mgs, pc = self.genericValidTrackPlacement(location="b18", track_rotation=1)
        move.public_company.cash = 15
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "Canadian Pacific don't have enough money to build tile there",
            mg_or.error_list
        )

    def testInvalidTrackCityTooLarge(self):
        """"AKA: Placing a 1 city tile on a 2 city hex"""
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="B&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="B&O", track_id=198, location="i17", track_rotation=0)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        mg_or.constructTrack(move, mgs)
        self.assertTrue(self.board.doesPathExist(start='Baltimore', end='i17-3'))
        mgs.board.game_map.regenerateCompanyGraph(move.public_company)
        self.assertTrue(self.board.doesRouteExist(move.public_company, start='Baltimore', end='i17-3'))
        self.assertTrue(self.board.doesPathExist(start='Baltimore', end='h18-6'))

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="B&O", track_id=169, location="h18", track_rotation=5)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "That location requires you to use a tile that has two cities",
            mg_or.error_list
        )

    def testInvalidTrackCityTooSmall(self):
        """"AKA: Placing a 2 city tile on a 1 city hex"""
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="B&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="B&O", track_id=179, location="j14", track_rotation=2)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        self.assertIn(
            "That location requires you to use a tile that has one city",
            mg_or.error_list
        )

    def testInvalidTrackTownTooSmall(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="B&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="B&O", track_id=9, location="i17", track_rotation=0)
        self.assertTrue(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        mg_or.constructTrack(move, mgs)
        self.assertTrue(self.board.doesPathExist(start='Baltimore', end='i17-4'))

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="B&O", track_id=159, location="i19", track_rotation=5)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        # You can't upgrade a gray but the error message should come up anyway.

        self.assertIn(
            "That location requires you to use a tile that has one town",
            mg_or.error_list)

    def testInvalidTrackTownTooLarge(self):
        move, mgs, pc = self.genericValidInitialTokenPlacement(company_short_name="C&O")
        mg_or = OperatingRound()
        self.assertTrue(mg_or.isValidTokenPlacement(move, mgs), mg_or.error_list)
        mg_or.purchaseToken(move, mgs)
        self.assertEqual(len(self.board.findCompanyTokenCities(move.public_company)), 1)

        move, mgs, pc = self.genericValidTrackPlacement(company_short_name="C&O", track_id=149, location="g7", track_rotation=1)
        self.assertFalse(mg_or.isValidTrackPlacement(move, mgs), mg_or.errors())
        # You can't upgrade a gray but the error message should come up anyway.

        self.assertIn(
            "That location requires you to use a tile that has two towns",
            mg_or.error_list)
