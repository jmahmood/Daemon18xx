from enum import Enum
from typing import List, NamedTuple

import logging

from app.base import err, Player, Move, PrivateCompany, PublicCompany, MutableGameState
from app.minigames.PrivateCompanyInitialAuction.minigame_auction import BiddingForPrivateCompany
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompany
from app.minigames.PrivateCompanyStockRoundAuction.minigame_auction import StockRoundSellPrivateCompany
from app.minigames.PrivateCompanyStockRoundAuction.minigame_decision import StockRoundSellPrivateCompanyDecision
from app.minigames.StockRound.minigame_stockround import StockRound
from app.minigames.base import Minigame, MinigameFlow
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
        self.stacking_type = False  # Keeps the full palyer order stack and adds htis one on top
        self.replacement_type = False  # Replaces the topmost player turn order generator with this one.
        self.overwrite_type = True  # Replace all player turn order generators.
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


class StockRoundTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        try:
            self.iteration = next(i for i, p in enumerate(self.players)
                 if p.id == self.state.stock_round_last_buyer_seller_id) + 1 % len(self.players)
        except StopIteration:
            self.iteration = 0


class PrivateCompanyInitialAuctionTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        current_private_company = next(c for c in self.state.private_companies if c.belongs_to is None)
        self.players = [x.player for x in current_private_company.player_bids]
        self.initial_player: Player = self.players[0]
        self.stacking_type = True
        self.overwrite_type = False


class StockRoundSellPrivateCompanyTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        """Create a pivot (is that what we call it?) around the owner so that players are asked in order from his left
        whether or not they want to buy his private company"""
        super().__init__(state)
        owner = state.auctioned_private_company.belongs_to
        idx = state.players.index(owner)

        self.players = state.players[idx + 1:len(state.players)] + state.players[0:idx]
        self.initial_player: Player = self.players[0]
        self.stacking_type = True
        self.overwrite_type = False


class StockRoundPrivateCompanyDecisionTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        """Create a pivot (is that what we call it?) around the owner so that players are asked in order from his left
        whether or not they want to buy his private company"""
        super().__init__(state)
        self.players = [state.auctioned_private_company.belongs_to]
        self.stacking_type = False
        self.overwrite_type = False
        self.replacement_type = True

class Game:
    """Holds state for the full ongoing game

    TODO: Need to clarify what state needs to be in the Game class,
    This probably needs to wait for all the minigames to be implemented and cleaned up.
    
    """
    @staticmethod
    def start(players: List[str]) -> "Game":
        total_players = len(players)
        cash = int(2400 / total_players)
        player_objects = []
        for order, player_name in enumerate(players):
            player_objects.append(
                Player.create(player_name, cash, order)
            )
        game = Game.initialize(player_objects)
        game.setMinigame(MinigameFlow("BuyPrivateCompany", False))
        return game


    @staticmethod
    def initialize(players: List[Player], saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.state = MutableGameState()
        game.state.players = players
        game.state.private_companies = PrivateCompany.allPrivateCompanies()
        game.state.public_companies = PublicCompany.allPublicCompanies()

        return game

    def __init__(self):
        self.state: MutableGameState = None
        self.current_player: Player = None
        self.player_order_generators = []
        self.errors_list = []

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
            "StockRound": "StockRoundMove",
            "StockRoundSellPrivateCompany": "AuctionBidMove",
            "StockRoundSellPrivateCompanyDecision": "AuctionDecisionMove",
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

        player_order_generator_from_minigame = {
            "BuyPrivateCompany": PlayerTurnOrder,
            "BiddingForPrivateCompany": PrivateCompanyInitialAuctionTurnOrder,
            "StockRound": StockRoundTurnOrder,
            "StockRoundSellPrivateCompany": StockRoundSellPrivateCompanyTurnOrder,
            "StockRoundSellPrivateCompanyDecision": StockRoundPrivateCompanyDecisionTurnOrder,
            "OperatingRound": None
        }

        try:
            player_order_generator = player_order_generator_from_minigame.get(self.minigame_class)(self.getState())
        except TypeError:
            raise TypeError("Cannot find turn generator for {}".format(self.minigame_class))

        if player_order_generator.stacking_type:
            self.player_order_generators.append(player_order_generator)

        if player_order_generator.replacement_type:
            self.player_order_generators.pop()
            self.player_order_generators.append(player_order_generator)

        if player_order_generator.overwrite_type:
            # An overwrite type function usually clears the full stack of player order functions.
            # The only case in which we don't is if we are "resuming" a player stack.
            try:
                self.player_order_generators.pop()
            except IndexError:
                logging.warning("No old player order function available")

            if len(self.player_order_generators) > 0 and \
                            self.getPlayerOrderClass().__class__.__name__ == player_order_generator.__class__.__name__:
                logging.warning("keeping old player order generator")
            else:
                self.player_order_generators = [player_order_generator]

    def getPlayerOrderClass(self) -> PlayerTurnOrder:
        return self.player_order_generators[len(self.player_order_generators) - 1]

    def setCurrentPlayer(self):
        """
        Sets the player by incrementing the newest player_order_fn
        """
        self.current_player = next(self.getPlayerOrderClass())

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
            "StockRoundSellPrivateCompany": StockRoundSellPrivateCompany, #TODO
            "StockRoundSellPrivateCompanyDecision": StockRoundSellPrivateCompanyDecision,
            "OperatingRound1": OperatingRound,  # TODO
            "OperatingRound2": OperatingRound,  # TODO
            "OperatingRound3": OperatingRound,  # TODO
        }

        cls: type(Minigame) = classes[self.minigame_class]
        return cls()

    def performedMove(self, move: Move) -> bool:
        """
        Performs a move and mutate the Minigame / Player Order states
        :param move:
        :return:
        """
        self.errors_list = [] # game errors only last from when a move is made until a new move is performed.

        minigame = self.getMinigame()
        minigame.onTurnStart(self.getState())
        success = minigame.run(move, self.getState())

        if success:
            next_minigame = minigame.next(self.getState())

            if self.minigame_class != next_minigame.minigame_class or next_minigame.force_player_reorder:
                """When the minigame changes, you need to switch the player order usually."""
                minigame.onComplete(self.getState())
                self.setMinigame(next_minigame)
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

    def setMinigame(self, next_minigame: MinigameFlow) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = next_minigame.minigame_class

    def saveState(self) -> None:
        # TODO: Saves State
        """This saves the current state to a data store.  Pickle or SQL?
        This is not necessary if you will run all the logic on the running process without quitting"""
        pass

    def notifyPlayers(self) -> None:
        # TODO: Used for external communication to a front-end module.
        """Sends a message to all players indicating that the state has been updated.
        Also sends error messages if any.

        This is not necessary if we are testing the application, and can be overridden where necessary"""
        pass
