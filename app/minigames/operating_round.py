from typing import List

from app.base import PrivateCompany, Move, GameBoard, Track, Token, Route, PublicCompany, Train, Color, MutableGameState, err
from app.minigames.base import Minigame


class OperatingRoundMove(Move):
    def __init__(self):
        super().__init__()
        self.purchase_token: bool \
            = None  # Will you purchase a token?
        self.construct_track: bool \
            = None  # Will you set a track?
        self.run_route: bool \
            = None  # Will you run a route?
        self.buy_train: bool \
            = None  # Will you buy a train?
        self.pay_dividend: bool \
            = None  # Will you pay a dividend?
        self.routes: List[Route] = None
        self.public_company: PublicCompany = None
        self.token: Token = None
        self.track: Track = None
        self.train: Train = None

    pass


class RustedTrainMove(Move):
    def __init__(self):
        super().__init__()
        self.public_company: PublicCompany = None
        self.train: Train = None


class OperatingRound(Minigame):

    def __init__(self):
        super().__init__()
        self.rusted_train_type: str = None
        self.trains_rusted: str = None

    def run(self, move: OperatingRoundMove, game_state: MutableGameState, **extra) -> bool:
        move.backfill(game_state)
        move.board = extra.get("board")
        # Store board for later checks during ``next``
        self.board = move.board

        if move.construct_track and not self.isValidTrackPlacement(move) or \
            move.purchase_token and not self.isValidTokenPlacement(move) or \
            move.run_route and not self.isValidRoute(move) or \
            not self.isValidPaymentOption(move) or \
            move.buy_train and not self.isValidTrainPurchase(move):
            return False

        self.constructTrack(move, **extra)
        self.purchaseToken(move, **extra)
        self.runRoutes(move, **extra)
        self.payDividends(move, **extra)
        self.purchaseTrain(move)

        return True

    def constructTrack(self, move: OperatingRoundMove, **kwargs):
        track: Track = move.track
        board: GameBoard = kwargs.get("board")
        if move.construct_track and self.isValidTrackPlacement(move):
            board.setTrack(track)
            move.public_company.cash -= 0  # yellow tiles free in 1830

    def purchaseToken(self, move: OperatingRoundMove, **kwargs):
        token: Token = move.token
        board: GameBoard = kwargs.get("board")
        if move.purchase_token and self.isValidTokenPlacement(move):
            cost = move.public_company.next_token_cost()
            token = Token(token.company, token.location, cost)
            board.setToken(token)
            move.public_company.cash -= cost
            move.public_company.tokens_available -= 1
            move.token = token

    def runRoutes(self, move: OperatingRoundMove, **kwargs):
        routes: List[Route] = move.routes
        board: GameBoard = kwargs.get("board")
        public_company = move.public_company

        if move.run_route and self.isValidRoute(move):
            for route in routes:
                public_company.addIncome(board.calculateRoute(route))

    def payDividends(self, move: OperatingRoundMove, **kwargs):
        if move.pay_dividend:
            move.public_company.payDividends()
        else:
            move.public_company.incomeToCash()

    def purchaseTrain(self, move: OperatingRoundMove):
        if move.buy_train and self.isValidTrainPurchase(move):
            pc = move.public_company
            train = move.train
            pc.cash -= train.cost
            if pc.trains is None:
                pc.trains = []
            pc.trains = pc.trains + [train]
            if train.rusts_on:
                self.rusted_train_type = train.rusts_on

    def isValidPaymentOption(self, move: OperatingRoundMove):
        # TODO: Validate the payment (to players or to company)
        return self.validate([])


    def isValidTrainPurchase(self, move: OperatingRoundMove):
        train = move.train
        pc = move.public_company
        available_trains = move.available_trains if hasattr(move, 'available_trains') else []

        validations = [
            err(pc.cash >= train.cost, "You don't have enough money"),
            err(train in available_trains or not available_trains, "That train is not for sale"),
        ]

        return self.validate(validations)


    def isValidRoute(self, move: OperatingRoundMove):
        """Validate that all proposed routes follow a subset of the 1830 rules."""

        board: GameBoard = move.board if hasattr(move, 'board') else None
        pc = move.public_company
        routes = move.routes or []

        has_company_token = False
        for route in routes:
            for stop in route.stops:
                tokens_here = board.tokens.get(stop, []) if board else []
                if any(t.company == pc for t in tokens_here):
                    has_company_token = True
                    break

        validations = [
            err(all(len(r.stops) >= 2 for r in routes), "You must join at least two cities"),
            err(True, "You cannot reverse across a junction"),
            err(True, "You cannot change track at a cross-over"),
            err(True, "You cannot travel the same track section twice"),
            err(True, "You cannot use the same station twice"),
            err(True, "Two trains cannot overlap"),
            err(has_company_token, "At least one city must be occupied by that corporation's token"),
            err(pc.trains is not None and len(pc.trains) > 0, "You need to have a train in order to run a route"),
        ]

        return self.validate(validations)

    def isValidTokenPlacement(self, move: OperatingRoundMove):
        token = move.token
        board: GameBoard = move.board if hasattr(move, 'board') else None
        existing_tokens = board.tokens.get(token.location, []) if board else []
        same_company = [t for t in existing_tokens if t.company == token.company]

        validations = [
            err(token.location in board.board if board else False, "There is no track there"),
            err(len(existing_tokens) < 1, "There are no free spots to place a token"),
            err(token.location in board.board if board else False, "You cannot connect to the location to place a token"),
            err(len(same_company) == 0, "You cannot put two tokens for the same company a location"),
            err(token.company.tokens_available > 0, "There are no remaining tokens for that company"),
            err(True, "You cannot place more than one token in one turn"),
            err(True, "You cannot place a token in Erie's home town before Erie"),
        ]

        return self.validate(validations)

    def isValidTrackPlacement(self, move: OperatingRoundMove):
        track = move.track
        board: GameBoard = move.board if hasattr(move, 'board') else None
        existing = board.board.get(track.location) if board else None

        color_order = {
            Color.YELLOW: 1,
            Color.BROWN: 2,
            Color.RED: 3,
            Color.GRAY: 4
        }

        validations = [
            err(track.location is not None, "Your track needs to be on a location that exists"),
            err(existing is None or color_order[track.color] > color_order.get(existing.color, 0), "Someone has already set a tile there"),
            err(True, "Your track needs to connect to your track or it needs to be your originating city, except in special cases (the base cities of the NYC and Erie, and the hexagons containing the C&SL and D&H Private Companies)"),
            err(True, "You can only lay one tile"),
            err(existing is None or track.color != Color.BROWN or color_order.get(existing.color, 0) >= color_order[Color.YELLOW], "You need to have a yellow tile before laying a green tile"),
            err(existing is None or track.color != Color.RED or color_order.get(existing.color, 0) >= color_order[Color.BROWN], "You need to have a green tile before laying an orange tile"),
            err(True, "A tile may not be placed so that a track runs off the grid"),
            err(True, "A tile may not terminate against the blank side of a grey hexagon"),
            err(True, "A tile may not terminate against a solid blue hexside in a lake or river"),
            err(True, "You don't have enough money to build tile there"),
            err(True, "That tile requires the company to own a Private Company ({})"),
            err(True, "That location requires you to use a tile that has one city"),
            err(True, "That location requires you to use a tile that has two city"),
            err(True, "That location requires you to use a tile that has one town"),
            err(True, "That location requires you to use a tile that has two towns"),
            err(True, "Replacement tiles must maintain all previously existing route connections"),
            err(True, "You cannot access that tile from your company"),
        ]

        return self.validate(validations)

    def next(self, **kwargs) -> str:
        """Need to pass it to Operating Round or to handle a situation where trains have rusted"""

        public_companies: List[PublicCompany] = kwargs.get("public_companies")
        if self.rusted_train_type:
            for pc in public_companies:
                pc.removeRustedTrains(self.rusted_train_type)
                if pc.hasNoTrains() and not pc.hasValidRoute(getattr(self, "board", None)):
                    return "TrainsRusted"
            # Clear the rust event after processing
            self.rusted_train_type = None

        # Do we have another operating round?
        if kwargs.get("playerTurn").anotherCompanyWaiting():
            return "OperatingRound{}".format(kwargs.get("currentOperatingRound"))  # Continue the same Operating Round

        # Do we have another operating round?
        if not kwargs.get("playerTurn").anotherCompanyWaiting() and \
                        kwargs.get("currentOperatingRound") < kwargs.get("totalOperatingRounds"):
            current_or = kwargs.get("currentOperatingRound") + 1
            kwargs["currentOperatingRound"] = current_or
            kwargs.get("playerTurn").restart(current_or)  # Recalculate order for new OR
            return "OperatingRound{}".format(current_or)

        return "StockRound"


    @staticmethod
    def onStart(**kwargs) -> None:
        # Can non-floated companies own private companies??
        private_companies: List[PrivateCompany] = kwargs.get("private_companies")
        for pc in private_companies:
            pc.distributeRevenue()

        # Create a list of floated companies (?)

    @staticmethod
    def onTurnStart(**kwargs) -> None:
        super().onTurnStart(**kwargs)

    @staticmethod
    def onTurnComplete(**kwargs) -> None:
        # Check all the other companies for rusted trains
        super().onTurnComplete(**kwargs)

    @staticmethod
    def onComplete(**kwargs) -> None:
        super().onComplete(**kwargs)


class TrainsRusted(Minigame):
    """Your trains rusted and you have nothing left.  Absolutely not kosher."""
    # Very simplified emergency train purchase / bankruptcy logic.

    def __init__(self):
        super().__init__()
        self.bankrupt = False

    def next(self, **kwargs) -> str:
        """Return to the operating round unless the company is bankrupt."""
        current_or = kwargs.get("currentOperatingRound", "")
        if self.bankrupt:
            return "StockRound"
        return f"OperatingRound{current_or}"

    def run(self, move: RustedTrainMove, state: MutableGameState, **kwargs) -> bool:
        """Attempt to acquire a train for a company with none remaining."""
        move.backfill(state)
        company = move.public_company
        train = move.train

        if company.cash >= train.cost:
            company.cash -= train.cost
        elif company.cash + company.president.cash >= train.cost:
            diff = train.cost - company.cash
            company.president.cash -= diff
            company.cash = 0
        else:
            company.bankrupt = True
            self.bankrupt = True
            return True

        if company.trains is None:
            company.trains = []
        company.trains.append(train)
        return True
