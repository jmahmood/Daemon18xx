from typing import List

from app.base import GameBoard, Token, Route, PublicCompany, MutableGameState, PrivateCompany, err
from app.minigames.OperatingRound.operating_round import OperatingRoundMove
from app.minigames.base import Minigame


class OperatingRound(Minigame):

    def __init__(self):
        self.rusted_train_type: str = None
        self.trains_rusted: str = None

    def run(self, move: OperatingRoundMove, **kwargs) -> bool:
        move.backfill(**kwargs)

        if move.construct_track and not self.isValidTrackPlacement(move) or \
            move.purchase_token and not self.isValidTokenPlacement(move) or \
            move.run_route and not self.isValidRoute(move) or \
            not self.isValidPaymentOption(move) or \
            move.buy_train and not self.isValidTrainPurchase(move):
            return False

        self.constructTrack(move, **kwargs)
        self.purchaseToken(move, **kwargs)
        self.runRoutes(move, **kwargs)
        self.payDividends(move, **kwargs)

        return True

    def constructTrack(self, move: OperatingRoundMove, **kwargs):
        track = move.track
        board: GameBoard = kwargs.get("board")
        if move.construct_track and self.isValidTrackPlacement(move):
            board.setTrack(track)

    def purchaseToken(self, move: OperatingRoundMove, **kwargs):
        token: Token = move.token
        board: GameBoard = kwargs.get("board")
        if move.purchase_token and self.isValidTokenPlacement(move):
            board.setToken(token)

    def runRoutes(self, move: OperatingRoundMove, **kwargs):
        routes: List[Route] = move.routes
        board: GameBoard = kwargs.get("board")
        public_company = move.public_company

        if move.run_route and self.isValidRoute(move):
            for route in routes:
                public_company.addIncome(board.calculateRoute(route))

    def payDividends(self, move: OperatingRoundMove, **kwargs):
        if move.pay_dividend:
            raise NotImplementedError()  # TODO: Need to spread cash between owners and whatever.
        else:
            move.public_company.incomeToCash()

    def purchaseTrain(self, move: OperatingRoundMove):
        if move.buy_train and self.isValidTrainPurchase(move):
            pass

    def isValidPaymentOption(self, move: OperatingRoundMove):
        # TODO: Validate the payment (to players or to company)
        return self.validate([])

    def isValidTrainPurchase(self, move: OperatingRoundMove):
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

    def isValidRoute(self, move: OperatingRoundMove):
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

    def isValidTokenPlacement(self, move: OperatingRoundMove):
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

    def isValidTrackPlacement(self, move: OperatingRoundMove):
        # TODO
        # Probably will have to implement a path finding algorithm for each company.
        # Dykstra's algo for tracks :o

        track = move.track
        return self.validate([
            err(
                False,
                "Your track needs to be on a location that exists"
            ),
            err(
                False,
                "Someone has already set a tile there"
            ),
            err(
                False,
                "Your track needs to connect to your track or it needs to be your originating city, "
                "except in special cases (the base cities of the NYC and Erie, "
                "and the hexagons containing the C&SL and D&H Private Companies)"
            ),
            err(
                False,
                "You can only lay one tile"
            ),
            err(
                False,
                "You need to have a yellow tile before laying a green tile"
            ),
            err(
                False,
                "You need to have a green tile before laying an orange tile"
            ),
            err(
                False,
                "A tile may not be placed so that a track runs off the grid"
            ),
            err(
                False,
                "A tile may not terminate against the blank side of a grey hexagon"
            ),
            err(
                False,
                "A tile may not terminate against a solid blue hexside in a lake or river"
            ),
            err(
                False,
                "You don't have enough money to build tile there"
            ),
            err(
                False,
                "That tile requires the company to own a Private Company ({})"
            ),
            err(
                False,
                "That location requires you to use a tile that has one city"
            ),
            err(
                False,
                "That location requires you to use a tile that has two city"
            ),
            err(
                False,
                "That location requires you to use a tile that has one town"
            ),
            err(
                False,
                "That location requires you to use a tile that has two towns"
            ),
            err(
                False,
                "Replacement tiles must maintain all previously existing route connections"
            ),
            err(
                False,
                "You cannot access that tile from your company")
        ])

    def next(self, **kwargs) -> str:
        """Need to pass it to Operating Round or to handle a situation where trains have rusted"""

        public_companies: List[PublicCompany] = kwargs.get("public_companies")
        if self.rusted_train_type:
            for pc in public_companies:
                pc.removeRustedTrains(self.rusted_train_type)
                if pc.hasNoTrains() and not pc.hasValidRoute():
                    return "TrainsRusted"

        # Do we have another operating round?
        if kwargs.get("playerTurn").anotherCompanyWaiting():
            return "OperatingRound{}".format(kwargs.get("currentOperatingRound"))  # Continue the same Operating Round

        # Do we have another operating round?
        if not kwargs.get("playerTurn").anotherCompanyWaiting() and \
                        kwargs.get("currentOperatingRound") < kwargs.get("totalOperatingRounds"):
            # TODO increment current operating round
            kwargs.get("playerTurn").restart() # Should re-calculate the turn order and run a new operating round from the start.
            return "OperatingRound{}".format(kwargs.get("currentOperatingRound") + 1)

        return "StockRound"

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

