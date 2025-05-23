from typing import List, Any

from app.base import (
    PrivateCompany,
    Move,
    GameBoard,
    Track,
    Token,
    Route,
    PublicCompany,
    Train,
    Color,
    MutableGameState,
    err,
)
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
            = False  # Will you pay a dividend? Defaults to False.
        self.routes: List[Route] = None
        self.public_company: PublicCompany = None
        self.token: Token = None
        self.track: Track = None
        self.train: Train = None
        self.config = None

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
        move.config = extra.get("config")
        # Store board for later checks during ``next``
        self.board = move.board

        if move.construct_track and not self.isValidTrackPlacement(move, game_state) or \
            move.purchase_token and not self.isValidTokenPlacement(move) or \
            move.run_route and not self.isValidRoute(move) or \
            not self.isValidPaymentOption(move) or \
            move.buy_train and not self.isValidTrainPurchase(move):
            return False

        self.constructTrack(move, game_state, **extra)
        self.purchaseToken(move, **extra)
        self.runRoutes(move, **extra)
        self.payDividends(move, **extra)
        self.purchaseTrain(move)

        return True

    def constructTrack(self, move: OperatingRoundMove, state: MutableGameState, **kwargs):
        track: Track = move.track
        board: GameBoard = kwargs.get("board")
        config = kwargs.get("config")
        if move.construct_track and self.isValidTrackPlacement(move, state):
            board.setTrack(track)
            if config is not None:
                cost = config.TRACK_LAYING_COSTS.get(track.color, 0)
            else:
                cost = 0
            move.public_company.cash -= cost
            state.track_laid.add(move.public_company.id)

    def purchaseToken(self, move: OperatingRoundMove, **kwargs):
        token: Token = move.token
        board: GameBoard = kwargs.get("board")
        if move.purchase_token and self.isValidTokenPlacement(move):
            cost = move.public_company.next_token_cost()
            token = Token(token.company, token.location, cost)
            board.setToken(token)
            move.public_company.cash -= cost
            move.public_company.tokens_available -= 1
            move.public_company.token_placed = True
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
        pc = move.public_company

        validations = [
            err(isinstance(move.pay_dividend, bool),
                "Dividend choice must be a boolean"),
            err(pc._income is not None,
                "Company must calculate income before distributing"),
        ]

        return self.validate(validations)


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

        def parse_loc(loc: str) -> tuple:
            """Return (row, col) tuple for board coordinates like 'A1'."""
            if not loc:
                return (0, 0)
            row = ord(loc[0].upper())
            try:
                col = int(loc[1:])
            except ValueError:
                col = 0
            return row, col

        has_company_token = False
        used_stops = set()
        invalid_track = False
        duplicate_stop = False
        disconnected = False
        capacities: List[int] = [int(''.join(filter(str.isdigit, t.type)) or 0) for t in (pc.trains or [])]
        capacities.sort(reverse=True)
        route_lengths = []
        for route in routes:
            route_seen = set()
            route_lengths.append(len(route.stops))
            for stop in route.stops:
                tokens_here = board.tokens.get(stop, []) if board else []
                if any(t.company == pc for t in tokens_here):
                    has_company_token = True

                if board and stop not in board.board and stop not in board.tokens:
                    invalid_track = True

                if stop in route_seen or stop in used_stops:
                    duplicate_stop = True
                route_seen.add(stop)
                used_stops.add(stop)

            if board and len(route.stops) >= 2:
                for a, b in zip(route.stops, route.stops[1:]):
                    if a not in board.board or b not in board.board:
                        disconnected = True
                        break
                    r1, c1 = parse_loc(a)
                    r2, c2 = parse_loc(b)
                    if not ((r1 == r2 and abs(c1 - c2) == 1) or (c1 == c2 and abs(r1 - r2) == 1)):
                        disconnected = True
                        break

        capacities_available = sorted(capacities, reverse=True)
        lengths_sorted = sorted(route_lengths, reverse=True)
        capacity_ok = len(lengths_sorted) <= len(capacities_available)
        for length, cap in zip(lengths_sorted, capacities_available):
            if length > cap:
                capacity_ok = False
                break

        validations = [
            err(routes != [] and all(len(r.stops) >= 2 for r in routes), "You must join at least two cities"),
            err(not invalid_track, "Route uses track that doesn't exist"),
            err(not duplicate_stop, "You cannot use the same station twice"),
            err(not disconnected, "Route must be a continuous connection"),
            err(has_company_token, "At least one city must be occupied by that corporation's token"),
            err(pc.trains is not None and len(pc.trains) >= len(routes) and len(pc.trains) > 0,
                "You need enough trains for the routes"),
            err(capacity_ok, "Route length exceeds train capacity"),
        ]

        return self.validate(validations)

    def isValidTokenPlacement(self, move: OperatingRoundMove):
        token = move.token
        board: GameBoard = move.board if hasattr(move, 'board') else None
        existing_tokens = board.tokens.get(token.location, []) if board else []
        same_company = [t for t in existing_tokens if t.company == token.company]

        cost = token.company.next_token_cost()

        validations = [
            err(board is not None and token.location in board.board, "There is no track there"),
            err(len(existing_tokens) < 1, "There are no free spots to place a token"),
            err(len(same_company) == 0, "You cannot put two tokens for the same company a location"),
            err(token.company.tokens_available > 0, "There are no remaining tokens for that company"),
            err(token.company.cash >= cost, "You don't have enough cash to buy a token"),
            err(not token.company.token_placed, "You have already placed a token this round"),
        ]

        return self.validate(validations)

    def isValidTrackPlacement(self, move: OperatingRoundMove, state: MutableGameState):
        track = move.track
        board: GameBoard = move.board if hasattr(move, 'board') else None
        existing = board.board.get(track.location) if board else None

        color_order = {
            Color.YELLOW: 1,
            Color.GREEN: 2,
            Color.BROWN: 3,
            Color.RED: 4,
            Color.GRAY: 5
        }

        has_company_token = any(
            t.company == move.public_company
            for tokens in board.tokens.values()
            for t in tokens
        ) if board else False

        already_laid = move.public_company.id in state.track_laid

        validations = [
            err(not already_laid, "That company already laid track this round"),
            err(track.location is not None, "Your track needs to be on a location that exists"),
            err(existing is None or color_order[track.color] == color_order.get(existing.color, 0) + 1,
                "Track upgrades must follow the colour progression"),
            err(existing is not None or has_company_token,
                "You cannot access that tile from your company"),
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
    def onStart(state: MutableGameState = None, **kwargs) -> None:
        """Prepare the game state for a new operating round."""
        if state is None:
            # Allow passing the state as the sole positional argument via kwargs
            if kwargs and isinstance(next(iter(kwargs.values())), MutableGameState):
                state = next(iter(kwargs.values()))
                kwargs = {}
            else:
                state = MutableGameState()

        private_companies: List[PrivateCompany] = kwargs.get(
            "private_companies", getattr(state, "private_companies", None)
        )
        if private_companies:
            for pc in private_companies:
                pc.distributeRevenue()

        # Reset track placement tracking for the new operating round
        state.track_laid = set()

        public_companies = kwargs.get(
            "public_companies", getattr(state, "public_companies", [])
        )
        for company in public_companies or []:
            company.token_placed = False

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
