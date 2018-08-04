from typing import List

from app.base import Player, Move, PrivateCompany
from app.minigames.base import Minigame
from app.minigames.private_companies import BiddingForPrivateCompany, BuyPrivateCompany
from app.minigames.stock_round import StockRound


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

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        pass

    def isValidPlayer(self, player: Player) -> bool:
        pass

    def getState(self) -> dict:
        return {}

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        classes = {
            "BiddingForPrivateCompany": BiddingForPrivateCompany,
            "BuyPrivateCompany": BuyPrivateCompany,
            "StockRound": StockRound,
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

        self.setMinigame(minigame.next()) if success else self.setError(minigame.errors())

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
