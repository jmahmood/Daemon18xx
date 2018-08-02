# This starts the 1830 Game Daemon.
# By Jawaad Mahmood (ideas@jawaadmahmood.com)

from typing import List
import os

import time


class Player:
    pass


class Move:
    """
    Contains all details of a move that is made, who made that move, and the data that they convey to represent the move.
    """
    @staticmethod
    def fromMessage(msg) -> "Move":
        """
        Required fields:
            Player
        :param msg:
        :return:
        """
        return Move()


class Minigame:
    """
    A State object for the game, used to evaluate rules that apply only to subsections of hte game itself.
    """
    def run(self, move: Move) -> bool:
        raise NotImplementedError()

    def errors(self) -> List[str]:
        raise NotImplementedError()

    def next(self) -> str:
        raise NotImplementedError()


class Game:
    @staticmethod
    def initialize(players: List[Player], state: dict) -> "Game":
        """

        :param players:
        :param state: Used to load data, if any.  If empty, everything defaults to a new game.
        :return:
        """
        game = Game()
        game.players = players
        return game

    def isOngoing(self) -> bool:
        return True

    def isValidMove(self, move: Move) -> bool:
        pass

    def isValidPlayer(self, player: Player) -> bool:
        pass

    def getMinigame(self) -> Minigame:
        """Creates a NEW INSTANCE of a mini game and passes it"""
        pass

    def performedMove(self, move: Move) -> bool:
        """
        Performs a move and sets the
        :param move:
        :return:
        """
        minigame = self.getMinigame()
        success = minigame.run(move)

        self.setMinigame(minigame.next()) if success else self.setError(minigame.errors())

        return success

    def setError(self, error_list: List[str]) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        pass

    def setMinigame(self, minigame_class: str) -> None:
        """A Minigame is a specific game state that evaluates more complex game rules.
        Bidding during private bidding, etc..."""
        pass

    def saveState(self) -> None:
        """This saves the current state to a data store.  Pickle or SQL.
        This is not necessary if you will run all the logic on the running process without quitting"""
        pass

    def notifyPlayers(self) -> None:
        """Sends a message to all players indicating that the state has been updated.
        Also sends error messages if any.
        This is not necessary if we are testing the """
        pass


def ongoing_game(pipe_filen="/tmp/mypipe"):
    """Conveys messages from a file pipe to the running daemon process"""
    pipe_path = pipe_filen
    if not os.path.exists(pipe_path):
        os.mkfifo(pipe_path)
    # Open the fifo. We need to open in non-blocking mode or it will stalls until
    # someone opens it for writting
    pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
    continue_game = True
    with os.fdopen(pipe_fd) as pipe:
        while continue_game:
            msg = pipe.read()
            if msg:
                yield Move.fromMessage(msg)
            print("Waiting for command.")
            time.sleep(0.5)
            continue_game = yield


def main(players: List[Player], state=None):
    """
    Game Damemon
    :param players:
    :param state:
    :return:
    """
    game = Game.initialize(players, state)
    for move in ongoing_game("/tmp/mypipe"):
        if game.isValidMove(move) and game.isValidPlayer(move.player) and game.performedMove(move):
            game.saveState()

        game.notifyPlayers()

        # Keep waiting for input if the game is ongoing.
        move.send(game.isOngoing())
