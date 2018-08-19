from typing import List

from app.base import Player, Move, PrivateCompany, PublicCompany, MutableGameState
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
    def __init__(self):
        self.stacking_type = False
        self.overwrite_type = False
        self.players: List[Player] = []
        self.initial_player: Player = None
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
        return Game.initialize(player_objects)


    @staticmethod
    def initialize(players: List[Player], saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.state.players = players
        game.state.private_companies = PrivateCompany.allPrivateCompanies()
        game.state.public_companies = []

        return game

    def __init__(self):
        self.state: MutableGameState = None
        self.current_player = None
        self.player_order_fn_list = []

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is of the type that is supposed to run this round.
        IE: You normally can't sell stock during an Operating Round"""
        # TODO: How do we determine the move type?
        # Some form of duck typing?
        raise NotImplementedError

    def isValidPlayer(self, player: Player) -> bool:
        """The person who submitted the move must be the current player."""
        return player == self.current_player

    def getState(self) -> MutableGameState:
        return self.state

    def setPlayerOrder(self):
        """Initializes a function that inherits from PlayerTurnOrder"""
        self.player_order_fn_list.pop()

        player_order_functions = {
            "BuyPrivateCompany": PlayerTurnOrder,
            "BiddingForPrivateCompany": None,
            "StockRound": None,
            "StockRoundSellPrivateCompany": None,
            "OperatingRound": None
        }

        player_order_generator = player_order_functions.get(self.minigame_class)()

        if player_order_generator.stacking_type:
            self.player_order_fn_list.append(player_order_generator)

        if player_order_generator.overwrite_type:
            # Same class as the previous, keep the player order the same.
            if self.player_order_fn_list[-1].__class__.__name__ == player_order_generator.__class__.__name__:
                pass
            else:
                self.player_order_fn_list = [player_order_generator]


    def setCurrentPlayer(self):
        """
        Sets the player by incrementing the newest player_order_fn
        """
        self.current_player = next(self.player_order_fn_list[-1])

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
        pass

    def setMinigame(self, minigame_class: str) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = minigame_class

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
