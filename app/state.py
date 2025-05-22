from typing import List

from app.config import load_config

import logging

from app.base import err, Player, Move, PrivateCompany, PublicCompany, MutableGameState
from app.minigames.PrivateCompanyInitialAuction.minigame_auction import BiddingForPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompany
from app.minigames.StockRound.minigame_stockround import StockRound
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
    """Holds state for the full ongoing game

    TODO: Need to clarify what state needs to be in the Game class,
    This probably needs to wait for all the minigames to be implemented and cleaned up.
    
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
        import copy
        game.state.players = players
        game.state.private_companies = copy.deepcopy(config.PRIVATE_COMPANIES)
        game.state.public_companies = copy.deepcopy(config.PUBLIC_COMPANIES)

        return game

    def __init__(self):
        self.state: MutableGameState = None
        self.current_player: Player = None
        self.player_order_fn_list = []
        self.errors_list = []
        self.config = None

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is of the type that is supposed to run this round.
        IE: You normally can't sell stock during an Operating Round"""
        # TODO: How do we determine the move type?
        # Some form of duck typing?
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
        return self.state

    def setPlayerOrder(self):
        """Initializes a function that inherits from PlayerTurnOrder"""

        player_order_functions = {
            "BuyPrivateCompany": PlayerTurnOrder,
            "BiddingForPrivateCompany": PrivateCompanyInitialAuctionTurnOrder,
            "StockRound": PlayerTurnOrder,
            "StockRoundSellPrivateCompany": None,
            "OperatingRound": None
        }

        player_order_generator = player_order_functions.get(self.minigame_class)(self.getState())

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
            "StockRoundSellPrivateCompany": None, #TODO
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


