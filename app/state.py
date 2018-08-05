from typing import List

from app.base import Player, Move, PrivateCompany, PublicCompany
from app.minigames.base import Minigame
from app.minigames.private_companies import BiddingForPrivateCompany, BuyPrivateCompany
from app.minigames.stock_round import StockRound

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
    """Holds state for the full ongoing game"""
    @staticmethod
    def initialize(players: List[Player], saved_game: dict = None) -> "Game":
        """

        :param players:
        :param saved_game: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.players = players
        game.private_companies = PrivateCompany.allPrivateCompanies()
        return game

    def __init__(self):
        self.current_player = None
        self.player_order_fn_list = []

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        """Determines whether or not the type of move submitted is of the type that is supposed to run this round.
        IE: You normally can't sell stock during an Operating Round"""
        pass

    def isValidPlayer(self, player: Player) -> bool:
        """The person who submitted the move must be the current player.
        This is more difficult than it seems, especially if we want to try to avoid holding unnecessary state.
        -> Player order is fixed until phases end
        -> Player order changes between different stock rounds
        -> There can be temporary player orders
            -> Private Company bid-offs
            -> Requesting bids for one's private company (This is quite complicated if we want to do it correctly)
                -> You make the request, everyone can submit a bid until you either accept one or cancel and do something else.
                -> IE: Everyone can make a "Move" (submit a bid) or you can revert the state
        -> Company operating rounds have different
        """
        pass

    def getState(self) -> dict:
        return {}

    def setPlayerOrderFn(self):
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
        Sets the player by incrementing the stacked player_order_fn
        """
        self.current_player = next(self.player_order_fn_list[-1])

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
            "StockRoundSellPrivateCompany": None, #TODO
            "OperatingRound": None  # TODO
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
        success = minigame.run(move, **self.getState())

        if success:
            if self.minigame_class != minigame.next():
                """When the minigame changes, you need to switch the player order usually."""
                self.setMinigame(minigame.next())
                self.setPlayerOrderFn()

            self.setCurrentPlayer()

        else:
            self.setError(minigame.errors())

        return success

    def setError(self, error_list: List[str]) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        pass

    def setMinigame(self, minigame_class: str) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        self.minigame_class = minigame_class

    def saveState(self) -> None:
        """This saves the current state to a data store.  Pickle or SQL?
        This is not necessary if you will run all the logic on the running process without quitting"""
        pass

    def notifyPlayers(self) -> None:
        """Sends a message to all players indicating that the state has been updated.
        Also sends error messages if any.

        This is not necessary if we are testing the application, and can be overridden where necessary"""
        pass
