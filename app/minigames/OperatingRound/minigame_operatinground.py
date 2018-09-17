from typing import List

from app.base import Token, Route, PublicCompany, PrivateCompany, err, Color
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
            put_back_track = board.setTrack(track)  # Adds track to the board
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
        # TODO: We may help users select routes, but they need to confirm the route they will run.

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

    def isValidRoute(self, move: OperatingRoundMove, state: MutableGameState):
        """When determining valid routes, you also need to take into account the state of the board
        after the currently queued tile placement is made."""
        # TODO: You also need to take into account any rail placements
        return self.validate([
            err(
                False,
                "You must join at least two cities"
            ),
            err(
                False,
                "You cannot reverse across a junction"
            ),
            err(
                False,
                "You cannot change track at a cross-over"
            ),
            err(
                False,
                "You cannot travel the same track section twice"
            ),
            err(
                False,
                "You cannot use the same station twice"
            ),
            err(
                False,
                "Two trains cannot overlap"
            ),
            err(
                False,
                "At least one city must be occupied by that corporation's token"
            ),
            err(
                False,
                "You need to have a train in order to run a route"
            ),
        ])

    def isValidTokenPlacement(self, move: OperatingRoundMove, state: MutableGameState):
        token = move.token
        return self.validate([
            err(
                False,
                "There is no track there"
            ),
            err(
                False,
                "There are no free spots to place a token"
            ),
            err(
                False,
                "You cannot connect to the location to place a token"
            ),
            err(
                False,
                "You cannot put two tokens for the same company in one location"
            ),
            err(
                False,
                "There are no remaining tokens for that company"
            ),
            err(
                False,
                "You cannot place more than one token in one turn"
            ),
            err(
                False,
                "You cannot place a token in Erie's home town before Erie"
            ),
        ])

    def isValidTrackPlacement(self, move: OperatingRoundMove, state: MutableGameState):
        game_board = state.board
        placement_track = move.track
        placement_track_location = move.track_placement_location

        company_stations = game_board.game_map.findCompanyStationCities(move.public_company)
        routes = game_board.findPaths(company_stations, placement_track_location)

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

        hex_config = game_board.game_map.map.get(placement_track_location)

        cost = game_board.getCost(move.track_placement_location)

        return self.validate([
            err(
                placement_track in game_board.available_track,
                "The track you selected is not available.",
                placement_track
            ),
            err(
                game_board.isValidLocation(placement_track_location),
                "Your track needs to be on a location that exists"
            ),
            err(
                placement_track in hex_config.track.type.upgrades,
                "Someone has already set a tile there"
            ),
            err(
                # Make sure there is a route to the specific location, or you have no other placements?
                len(company_stations) == 0 or len(routes) > 0,
                "Your track needs to connect to your track or it needs to be your originating city, "
                "except in special cases (the base cities of the NYC and Erie, "
                "and the hexagons containing the C&SL and D&H Private Companies)"
            ),
            # err(
            #     False,
            #     "You can only lay one tile"
            # ),
            err(
                hex_config.track.type.color != Color.YELLOW and
                move.track.type.color == Color.BROWN,
                "You need to have a yellow tile before laying a brown tile"
            ),
            err(
                hex_config.track.type.color != Color.BROWN and
                move.track.type.color == Color.RED,
                "You need to have a brown tile before laying a red tile"
            ),
            err(
                is_valid_orientation,
                "A tile may not be placed so that a track runs off the grid /"
                "A tile may not terminate against the blank side of a grey hexagon /"
                "A tile may not terminate against a solid blue hexside in a lake or river"
            ),
            err(
                cost <= move.public_company.cash,
                "{} don't have enough money to build tile there",
                move.public_company.name
            ),
            err(
                not hex_config.requires_private_company or
                hex_config.requires_private_company.belongs_to.id ==
                move.public_company.id,
                "That tile requires the company to own a Private Company ({})",
                hex_config.requires_private_company.name
            ),
            err(
                len(hex_config.cities) == 0 and move.track.type.cities != 0,
                "That location requires you to use a tile that has no cities"
            ),
            err(
                len(hex_config.cities) == 1 and move.track.type.cities != 1,
                "That location requires you to use a tile that has one city"
            ),
            err(
                len(hex_config.cities) == 2 and move.track.type.cities != 2,
                "That location requires you to use a tile that has two city"
            ),
            err(
                len(hex_config.towns) == 0 and move.track.type.towns != 0,
                "That location requires you to use a tile that has no towns"
            ),
            err(
                len(hex_config.towns) == 1 and move.track.type.towns != 1,
                "That location requires you to use a tile that has one town"
            ),
            err(
                len(hex_config.towns) == 2 and move.track.type.towns != 2,
                "That location requires you to use a tile that has two towns"
            ),
            err(
                set(hex_config.track.connections()) <= set(move.track.connections()),
                "Replacement tiles must maintain all previously existing route connections"
            ),
            err(
                len(routes) == 0, # TODO: This should be ignored if you are placing your first tile.
                "You cannot access that map location from your company")
        ])

    def next(self, state: MutableGameState) -> MinigameFlow:
        """Need to pass it to Operating Round or to handle a situation where trains have rusted"""
        state.operating_round_turn += 1

        public_companies: List[PublicCompany] = state.public_companies
        if self.rusted_train_type:
            for pc in public_companies:
                pc.removeRustedTrains(self.rusted_train_type)
                if pc.hasNoTrains() and not pc.hasValidRoute():
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
