from typing import List, Union

from app.base import Token, Route, PublicCompany, PrivateCompany, err, Color, City, Town
from app.game_map import GameBoard
from app.minigames.OperatingRound.operating_round import OperatingRoundMove
from app.minigames.base import Minigame, MinigameFlow
from app.state import MutableGameState


class OperatingRound(Minigame):

    def __init__(self):
        self.rusted_train_type: str = None
        self.trains_rusted: str = None

    def run(self, move: OperatingRoundMove, state: MutableGameState) -> bool:
        move.backfill(state)

        if move.construct_track and not self.isValidTrackPlacement(move, state) or \
                move.purchase_token and not self.isValidTokenPlacement(move, state) or \
                move.run_route and not self.isValidRoute(move, state) or \
                not self.isValidPaymentOption(move, state) or \
                move.buy_train and not self.isValidTrainPurchase(move, state):
            return False

        self.constructTrack(move, state)
        self.purchaseToken(move, state)
        self.runRoutes(move, state)
        self.payDividends(move, state)

        return True

    def constructTrack(self, move: OperatingRoundMove, state: MutableGameState):
        track = move.track
        board = state.board
        if move.construct_track and self.isValidTrackPlacement(move, state):
            put_back_track = board.placeTrack(move.track_placement_location, track)  # Adds track to the board
            state.trackUsed(track)  # Removes track from the available tracks
            state.trackAvailable(put_back_track)  # If valid, add this track back to the list of what you can do.

    def purchaseToken(self, move: OperatingRoundMove, state: MutableGameState):
        token: Token = move.token
        board: GameBoard = state.board
        if move.purchase_token and self.isValidTokenPlacement(move, state):
            board.setToken(public_company=token.public_company,
                           city=token.city,
                           location=token.location)

    def runRoutes(self, move: OperatingRoundMove, state: MutableGameState):
        routes: List[Route] = move.routes
        board: GameBoard = state.board
        public_company = move.public_company

        if move.run_route and self.isValidRoute(move, state):
            for route in routes:
                public_company.addIncome(board.calculateRoute(route))

    def payDividends(self, move: OperatingRoundMove, state: MutableGameState):
        if move.pay_dividend:
            raise NotImplementedError()  # TODO: Need to spread cash between owners and whatever.
        else:
            move.public_company.incomeToCash()

    def purchaseTrain(self, move: OperatingRoundMove, state: MutableGameState):
        if move.buy_train and self.isValidTrainPurchase(move, state):
            pass

    def isValidPaymentOption(self, move: OperatingRoundMove, state: MutableGameState):
        # TODO: Validate the payment (to players or to company)
        return self.validate([])

    def isValidTrainPurchase(self, move: OperatingRoundMove, state: MutableGameState):
        return self.validate([
            err(
                False,
                "You don't have enough money"
            ),
            err(
                False,
                "That train is not for sale"
            ),
        ])

    def atLeastOneStation(self, move: OperatingRoundMove):
        station_nodes = set()  # TODO: P1: You can't pass through the same station twice.
        for route in move.routes:
            stations = route.full_route.intersection(station_nodes)
            if len(stations) < 1:
                return False
        return True

    def areStationsDisjoint(self, move: OperatingRoundMove):
        station_nodes = set()  # TODO: P1: You can't pass through the same station twice.
        passed_through = set()
        for route in move.routes:
            stations = route.full_route.intersection(station_nodes)
            if stations in passed_through:
                return False
            passed_through = passed_through.union(passed_through)
        return True

    def areRoutesDisjoint(self, move: OperatingRoundMove):
        city_nodes = set()  # TODO: P1: You can pass through the same city nodes but nothing else.
        passed_through = set()
        for route in move.routes:
            #
            invalid_repetition_nodes = passed_through.intersection(
                route.full_route
            ).difference(city_nodes)

            if len(invalid_repetition_nodes) > 0:
                return False

            passed_through = passed_through.union(route.full_route)
        return True

    def atLeasttwoCities(self, move: OperatingRoundMove):
        city_nodes = set()  # TODO: P1: You can pass through the same city nodes but nothing else.
        for route in move.routes:
            if len(route.full_route.intersection(city_nodes)) < 2:
                return False
        return True

    def isValidRoute(self, move: OperatingRoundMove, state: MutableGameState):
        """When determining valid routes, you also need to take into account the state of the board
        after the currently queued tile placement is made."""
        # TODO: P2: You also need to take into account any rail placements
        all_routes_exist = [state.board.doesCityRouteExist(move.public_company, start, end) for start, end, _ in
                            move.routes]
        # all_possible_routes = None  # nx.all_simple_paths(graph, start, end)

        return self.validator(
            (
                False not in all_routes_exist,
                "You don't have control of that route",
                state.board.error_list
            ),
            (
                self.atLeasttwoCities(move),
                "Each route must join at least two cities"
            ),
            (
                True,  # TODO: P4: We may have to add in some kind of one way edge (ugh) to handle this.
                "You cannot reverse across a junction"
            ),
            (
                True,  # Because of the way the route information is handled, this is not possible
                "You cannot change track at a cross-over"
            ),
            (
                self.areRoutesDisjoint(move),
                "You cannot travel the same track section twice"
            ),
            (
                self.areStationsDisjoint(move),
                "You cannot use the same station twice"
            ),
            # (
            #     False,
            #     "Two trains cannot overlap"
            # ),
            (
                self.atLeastOneStation(move),
                "At least one city must be occupied by that corporation's token"
            ),
            (
                not move.public_company.hasNoTrains(),
                "You need to have a train in order to run a route"
            ),
        )

    def isValidTokenPlacement(self, move: OperatingRoundMove, state: MutableGameState):
        token = move.token
        company_stations = state.board.findCompanyTokenCities(move.public_company)

        return self.validate([
            err(
                move.token.location == move.public_company.base or len(company_stations) > 0,
                "Your first token needs to be in your company's base location: {}",
                move.public_company.base
            ),
            err(
                move.public_company == move.token.public_company,
                "You can only place a token for your own company ({}, {})",
                move.public_company.name,
                move.token.public_company.name
            ),
            err(
                # TODO: P1: Add in the initial track that exists for all cities?
                state.board.hasTrack(move.token.location),
                "There is no track there"
            ),
            err(
                len(state.board.getTokens(token.city)) < state.board.maxTokens(token.city),
                "There are no free spots to place a token: Max ()",
                state.board.maxTokens(token.city)
            ),
            err(move.token.location == move.public_company.base or
                True in (state.board.doesCityRouteExist(move.public_company, cs, move.token.city)
                         for cs in company_stations),
                "You cannot connect to the location to place a token"
            ),
            err(
                move.token.city not in company_stations,
                "You cannot put two tokens for the same company in one location"
            ),
            err(
                len(company_stations) < len(move.public_company.token),
                "There are no remaining tokens for that company"
            ),
            # err(
            #     False,
            #     "You cannot place more than one token in one turn"
            # ),
            # # TODO: P4: I really don't care about this rule right now..
            # err(
            #     False,
            #     "You cannot place a token in Erie's home town before Erie"
            # ),
        ])

    def isValidConnectionToOtherTrack(self, move: OperatingRoundMove, state: MutableGameState):
        game_board = state.board
        company_stations = game_board.findCompanyTokenCities(move.public_company)

        inbound_locations = []  # TODO: P2: A list of all possible places from which we can connect to this track.
        # example: A tile on C6 has C6-1, C6-2 (etc).  It may only bind to C6-1 and C6-3 which binds to C4-3 and C8-1
        # We need to get all these possible connections, and make sure we can connect to any of them.
        # We can shortcut this if the person has no track.

        for station in company_stations:
            for inbound_location in inbound_locations:
                if game_board.doesRouteExist(move.public_company, station.name, inbound_location):
                    return True
        return False

    def isValidTrackPlacement(self, move: OperatingRoundMove, state: MutableGameState):
        game_board = state.board
        placement_track = move.track
        placement_track_location = move.track_placement_location

        rotated_track_connections = [
            (x.rotate(move.track.rotation),
             y.rotate(move.track.rotation)) for possibility
            in move.track.type.connections for x, y in possibility
        ]

        # We use the links to make sure we don't accidentally connect to a gray

        inbound_outbound_labels = [x.edge_name(placement_track_location) for x, _ in rotated_track_connections] \
                                  + [y.edge_name(placement_track_location) for _, y in rotated_track_connections]

        is_valid_orientation = False not in [
            game_board.hasExternalConnection(x) for x in inbound_outbound_labels
        ]

        hex_config = game_board.game_map.mapHexConfig.get(placement_track_location)

        cost = game_board.getCost(move.track_placement_location)

        return self.validator(
            (
                placement_track in game_board.game_tracks.available_track,
                "The track you selected is not available.",
                placement_track
            ),
            (
                game_board.isValidLocation(placement_track_location),
                "Your track needs to be on a location that exists"
            ),
            (
                placement_track in hex_config.track.type.upgrades,
                "Someone has already set a tile there"
            ),
            (
                # Make sure there is a route to the specific location, or you have no other placements?
                len(game_board.findCompanyTokenCities(move.public_company)) == 0 or
                self.isValidConnectionToOtherTrack(move, state),
                "Your track needs to connect to your track or it needs to be your originating city, "
                "except in special cases (the base cities of the NYC and Erie, "
                "and the hexagons containing the C&SL and D&H Private Companies)"
            ),
            (
                hex_config.track.type.color != Color.YELLOW and
                move.track.type.color == Color.BROWN,
                "You need to have a yellow tile before laying a brown tile"
            ),
            (
                hex_config.track.type.color != Color.BROWN and
                move.track.type.color == Color.RED,
                "You need to have a brown tile before laying a red tile"
            ),
            (
                is_valid_orientation,
                "A tile may not be placed so that a track runs off the grid /"
                "A tile may not terminate against the blank side of a grey hexagon /"
                "A tile may not terminate against a solid blue hexside in a lake or river"
            ),
            (
                cost <= move.public_company.cash,
                "{} don't have enough money to build tile there",
                move.public_company.name
            ),
            (
                not hex_config.requires_private_company or
                hex_config.requires_private_company.belongs_to.id ==
                move.public_company.id,
                "That tile requires the company to own a Private Company ({})",
                hex_config.requires_private_company.name
            ),
            (
                len(hex_config.cities) == 0 and move.track.type.cities != 0,
                "That location requires you to use a tile that has no cities"
            ),
            (
                len(hex_config.cities) == 1 and move.track.type.cities != 1,
                "That location requires you to use a tile that has one city"
            ),
            (
                len(hex_config.cities) == 2 and move.track.type.cities != 2,
                "That location requires you to use a tile that has two city"
            ),
            (
                len(hex_config.towns) == 0 and move.track.type.towns != 0,
                "That location requires you to use a tile that has no towns"
            ),
            (
                len(hex_config.towns) == 1 and move.track.type.towns != 1,
                "That location requires you to use a tile that has one town"
            ),
            (
                len(hex_config.towns) == 2 and move.track.type.towns != 2,
                "That location requires you to use a tile that has two towns"
            ),
            (
                set(hex_config.track.connections()) <= set(move.track.connections()),
                "Replacement tiles must maintain all previously existing route connections"
            ),
        )

    def companyHasARoute(self, pc: PublicCompany, state: MutableGameState) -> bool:
        stations = state.board.findCompanyTokenCities(pc)
        game_board = state.board

        # TODO: P1: Get a list of all cities and towns that are available
        all_destinations: List[Union[City, Town]] = []

        # Step 1: Does the company have any stations?
        if len(stations) > 0:
            # Step 2: Does the company have any valid routes from that station to any city or town?
            for station in stations:
                for destination in all_destinations:
                    if game_board.doesCityRouteExist(pc, station, destination):
                        return True

        return False

    def next(self, state: MutableGameState) -> MinigameFlow:
        """Need to pass it to Operating Round or to handle a situation where trains have rusted"""
        state.operating_round_turn += 1

        public_companies: List[PublicCompany] = state.public_companies
        if self.rusted_train_type:
            for pc in public_companies:
                pc.removeRustedTrains(self.rusted_train_type)
                if pc.hasNoTrains() and self.companyHasARoute(pc, state):
                    return MinigameFlow("TrainsRusted", False)

        if state.operating_round_turn < len([p for p in state.public_companies if p.isFloated()]):
            return MinigameFlow("OperatingRound", False)

        elif state.operating_round_phase < state.total_operating_round_phases:
            state.operating_round_turn = 0
            state.operating_round_phase += 1
            return MinigameFlow("OperatingRound", True)  # Triggers reorders as necessary.

        return MinigameFlow("StockRound", False)

    @staticmethod
    def onStart(state: MutableGameState) -> None:
        private_companies: List[PrivateCompany] = state.private_companies
        for pc in private_companies:
            pc.distributeRevenue()

    @staticmethod
    def onTurnStart(state: MutableGameState) -> None:
        super().onTurnStart(state)

    @staticmethod
    def onTurnComplete(state: MutableGameState) -> None:
        # Check all the other companies for rusted trains
        super().onTurnComplete(state)

    @staticmethod
    def onComplete(state: MutableGameState) -> None:
        super().onComplete(state)
