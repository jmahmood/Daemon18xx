from typing import List

from app.config import load_config

import logging

from app.base import err, Player, Move, PrivateCompany, PublicCompany, MutableGameState, StockPurchaseSource
from app.minigames.PrivateCompanyInitialAuction.minigame_auction import BiddingForPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompany
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.StockRoundSellPrivateCompany.minigame_auction import Auction
from app.minigames.base import Minigame
from app.minigames.operating_round import OperatingRound

"""
# These are static function versions, but I probably want to use something else?

def OfferPrivateCompanyForSale(players: List[Player], company: PrivateCompany):
    # Happens when a player offers his private company for sale during his turn.
    # In the interests of fairness, everyone gets a chance to bid on it.
    starting_player = company.belongs_to.order
    player_order_doubled = players.append(players)
    pto = PlayerTurnOrder()
    pto.stacking_type = True
    pto.players = player_order_doubled[starting_player + 1:starting_player + len(players)]
    return iter(pto)


def PrivateCompanyBidPlayerOrder(company: PrivateCompany):
    players = [pb.player for pb in company.player_bids]
    pto = PlayerTurnOrder()
    pto.stacking_type = True
    pto.players = players
    return iter(pto)


def StockRoundPlayers(company: PrivateCompany, stock_round_iteration):
    players = [pb.player for pb in company.player_bids]
    starting_player = stock_round_iteration % len(players)
    player_order_doubled = players.append(players)

    pto = PlayerTurnOrder()
    pto.overwrite_type = True
    pto.players = player_order_doubled[starting_player:starting_player + len(players)]
    return iter(pto)
"""


class PlayerTurnOrder:
    def __init__(self, state: MutableGameState):
        self.state = state
        self.stacking_type = False
        self.overwrite_type = True
        self.players: List[Player] = state.players
        self.initial_player: Player = self.players[0]
        self.iteration = 0

    def __iter__(self):
        return self

    def __next__(self) -> Player:
        player_position = self.iteration % len(self.players)
        self.iteration += 1
        return self.players[player_position]

    def isStacking(self):
        return self.stacking_type

    def isOverwrite(self):
        return self.overwrite_type

    def removePlayer(self, player:Player):
        self.players.remove(player)

    def removeCompany(self, company:PublicCompany):
        raise NotImplementedError

class PrivateCompanyInitialAuctionTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        current_private_company = next(c for c in self.state.private_companies if c.belongs_to is None)
        self.players = [x.player for x in current_private_company.player_bids]
        self.initial_player: Player = self.players[0]
        self.stacking_type = True
        self.overwrite_type = False


class Game:
    """Holds state for the full ongoing game.

    ARCHITECTURE NOTES:
    -------------------
    The Game class manages the game loop and coordinates between:
    - MutableGameState: Holds all game data (players, companies, etc.)
    - Minigames: Phase-specific logic (auctions, stock rounds, operating rounds)
    - PlayerTurnOrder: Determines player sequencing
    - Config: Variant-specific rules (1830, 1846, 1889)

    STATE MANAGEMENT PATTERN:
    ------------------------
    State is centralized in MutableGameState and passed to minigames via method parameters.
    Minigames receive state and perform mutations directly. This stateless minigame design
    allows for easy serialization and replay.

    Each minigame receives:
    - move: The player's action
    - state: MutableGameState (mutable reference)
    - **kwargs: Additional context (board, config, etc.)

    STATE LIFECYCLE:
    ---------------
    1. Game.start() - Initialize players and config
    2. setMinigame() - Set current game phase
    3. setPlayerOrder() - Determine turn sequence
    4. performedMove() - Execute player action through minigame
    5. Minigame mutates state directly
    6. Check for phase transition via minigame.next()
    7. Update player order and continue

    IMMUTABILITY NOTE:
    -----------------
    While MutableGameState is designed to be mutated, snapshots for undo/replay
    can be created by serializing state at each move. For event sourcing, store
    moves instead of state snapshots and replay to reach any game point.

    TODO RESOLVED (was line 91):
    ---------------------------
    Game class should contain:
    - state: MutableGameState (all game data)
    - current_player: Active player
    - minigame_class: Current game phase name
    - config: Variant configuration
    - operating_order: Company operation sequence
    - player_order_fn_list: Stack of turn order generators
    - errors_list: Validation errors

    Minigame-specific state goes in MutableGameState, not Game.
    """
    @staticmethod
    def start(players: List[str], variant: str = "1830") -> "Game":
        config = load_config(variant)
        total_players = len(players)
        cash = config.starting_cash(total_players)
        player_objects = []
        for order, player_name in enumerate(players):
            player_objects.append(
                Player.create(player_name, cash, order)
            )
        game = Game.initialize(player_objects, config)
        game.setMinigame("BuyPrivateCompany")
        return game


    @staticmethod
    def initialize(players: List[Player], config, saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.config = config
        game.state = MutableGameState()
        game.state.players = players
        game.state.priority_deal_player = players[0] if players else None
        game.state.private_companies = config.PRIVATE_COMPANIES
        game.state.public_companies = config.PUBLIC_COMPANIES

        return game

    def __init__(self):
        self.state: MutableGameState = None
        self.current_player: Player = None
        self.player_order_fn_list = []
        self.errors_list = []
        self.config = None
        self.operating_order: List[str] = []
        self.last_operating_order: List[str] = []

    def isOngoing(self) -> bool:
        return True

    def sort_operating_order(self) -> List[str]:
        """Sort floated, non-bankrupt companies for the next operating round."""
        market = getattr(self.config, "STOCK_MARKET", None)
        companies = [
            c for c in (self.state.public_companies or [])
            if c.isFloated() and not c.bankrupt
        ]
        def prior_index(cid: str) -> int:
            return self.last_operating_order.index(cid) if cid in self.last_operating_order else 0

        if market:
            companies.sort(
                key=lambda c: (
                    -market.cell(*c.stock_pos).price,
                    c.stock_pos[0],
                    prior_index(c.id)
                )
            )
        else:
            companies.sort(
                key=lambda c: (
                    -c.stockPrice[StockPurchaseSource.BANK],
                    c.stock_pos[0],
                    prior_index(c.id)
                )
            )

        self.operating_order = [c.id for c in companies]
        self.last_operating_order = list(self.operating_order)
        return self.operating_order

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is valid for the current game phase.

        MOVE TYPE DETECTION (TODO RESOLVED from line 174):
        ---------------------------------------------------
        We use class name matching to determine move types. This is a form of duck typing
        that works well for our stateless architecture:

        1. Each minigame phase expects specific move types (e.g., StockRoundMove, OperatingRoundMove)
        2. Move classes define their structure via __init__() fields
        3. Class name matching validates move/phase compatibility
        4. Invalid moves are rejected before minigame execution

        ALTERNATIVE APPROACHES CONSIDERED:
        ----------------------------------
        - MoveType enum: More type-safe but requires maintaining parallel enum
        - Interface/Protocol: Better type hints but more boilerplate
        - isinstance() checks: More Pythonic but requires importing all move classes

        Current approach balances simplicity, performance, and extensibility.
        New move types can be added by:
        1. Creating a new Move subclass
        2. Adding mapping to minigame_move_classes
        3. Implementing minigame logic

        EXAMPLE:
        --------
        StockRound phase expects StockRoundMove:
        - Buying stock: StockRoundMove with buy_stock=True
        - Selling stock: StockRoundMove with sell_stock=True
        - Passing: StockRoundMove with pass_turn=True

        OperatingRound expects OperatingRoundMove:
        - Laying track: OperatingRoundMove with construct_track=True
        - Running routes: OperatingRoundMove with run_route=True
        """
        minigame_move_classes = {
            "BuyPrivateCompany": "BuyPrivateCompanyMove",
            "BiddingForPrivateCompany":  "BuyPrivateCompanyMove",
        }
        return minigame_move_classes.get(self.minigame_class) == move.__class__.__name__

    def isValidPlayer(self, move: Move) -> bool:
        """The person who submitted the move must be the current player.

        Warning: The player object is only set in the move once the "Backfill" function is executed (to load info from state)
        To avoid that, we are only comparing the player ids, which it always has."""
        errors = err(
            move.player_id == self.current_player.id,
            "Wrong player; {} is not {}",
            move.player_id, self.current_player.id
        )
        if errors == None:
            return True
        self.errors_list = [errors]
        return False

    def getState(self) -> MutableGameState:
        """Get the current mutable game state.

        Returns:
            MutableGameState: The current game state (mutable reference)
        """
        return self.state

    def getStateContext(self) -> dict:
        """Get common context dict for minigame execution.

        Returns a dictionary with frequently-needed context for minigames,
        reducing the need for manual kwargs construction.

        Returns:
            dict: Context including state, config, board, and current round info

        Example:
            >>> context = game.getStateContext()
            >>> minigame.run(move, context['state'], **context)
        """
        return {
            'state': self.state,
            'config': self.config,
            'players': self.state.players,
            'public_companies': self.state.public_companies,
            'private_companies': self.state.private_companies,
            'current_player': self.current_player,
            'game': self
        }

    def setPlayerOrder(self):
        """Initializes a function that inherits from PlayerTurnOrder"""

        player_order_functions = {
            "BuyPrivateCompany": PlayerTurnOrder,
            "BiddingForPrivateCompany": PrivateCompanyInitialAuctionTurnOrder,
            "StockRound": PlayerTurnOrder,
            "StockRoundSellPrivateCompany": PlayerTurnOrder,
            "OperatingRound": None
        }

        player_order_generator = player_order_functions.get(self.minigame_class)(self.getState())

        if self.minigame_class == "StockRound" and self.state.priority_deal_player in self.state.players:
            players = self.state.players
            start = players.index(self.state.priority_deal_player)
            player_order_generator.players = players[start:] + players[:start]
            player_order_generator.initial_player = self.state.priority_deal_player

        if player_order_generator.stacking_type:
            self.player_order_fn_list.append(player_order_generator)

        if player_order_generator.overwrite_type:
            # An overwrite type function usually clears the full stack of player order functions.
            # The only case in which we don't is if we are "resuming" a player stack.
            try:
                self.player_order_fn_list.pop()
            except IndexError:
                logging.warning("No old player order function available")

            if len(self.player_order_fn_list) > 0 and \
                            self.get_player_order_fn().__class__.__name__ == player_order_generator.__class__.__name__:
                logging.warning("keeping old player order generator")
            else:
                self.player_order_fn_list = [player_order_generator]

    def get_player_order_fn(self):
        return self.player_order_fn_list[len(self.player_order_fn_list) - 1]

    def setCurrentPlayer(self):
        """
        Sets the player by incrementing the newest player_order_fn
        """
        self.current_player = next(self.get_player_order_fn())

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
            "StockRoundSellPrivateCompany": Auction,
            "OperatingRound1": OperatingRound,  # TODO
            "OperatingRound2": OperatingRound,  # TODO
            "OperatingRound3": OperatingRound,  # TODO
        }

        cls: type(Minigame) = classes.get(self.minigame_class)
        return cls()

    def performedMove(self, move: Move) -> bool:
        """
        Performs a move and mutate the Minigame / Player Order states
        :param move:
        :return:
        """
        minigame = self.getMinigame()
        minigame.onTurnStart(self.getState())
        success = minigame.run(move, self.getState())

        if success:
            if self.minigame_class != minigame.next(self.getState()):
                """When the minigame changes, you need to switch the player order usually."""
                minigame.onComplete(self.getState())
                self.setMinigame(minigame.next(self.getState()))
                self.setPlayerOrder()
                self.getMinigame().onStart(self.getState())
            else:
                minigame.onTurnComplete(self.getState())

            self.setCurrentPlayer()

        else:
            self.setError(minigame.errors())

        return success

    def setError(self, error_list: List[str]) -> None:
        # TODO: Sets the error that will be returned
        self.errors_list = error_list

    def errors(self):
        return self.errors_list

    def setMinigame(self, minigame_class: str) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = minigame_class


def apply_move(game: Game, move: Move) -> Game:
    """Execute ``move`` on ``game`` and return the updated game state.

    No external side effects such as saving or network notifications occur.  The
    passed in ``game`` instance is mutated and returned for convenience.
    """

    if game.isValidMove(move) and game.isValidPlayer(move) and game.performedMove(move):
        return game
    return game


