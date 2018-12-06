# This starts the 1830 Game Daemon.
# By Jawaad Mahmood (ideas@jawaadmahmood.com)

from typing import List
import os

import time

from app.base import Player, Move
from app.game import Game


def ongoing_game(pipe_filen="/tmp/mypipe"):
    """Conveys messages from a file pipe to the running daemon process"""
    pipe_path = pipe_filen
    if not os.path.exists(pipe_path):
        os.mkfifo(pipe_path)
    # Open the fifo. We need to open in non-blocking mode or it will stalls until
    # someone opens it for writing
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


def main(players: List[Player], saved_game=None):
    """
    Game Daemon
    :param saved_game:
    :param players:
    :param state:
    :return:
    """
    game = Game.initialize(players, saved_game)
    game.setPlayerOrder()  # Rah.
    for move in ongoing_game("/tmp/mypipe"):

        if game.isValidMove(move) and game.isValidPlayer(move.player) and game.performedMove(move):
            game.saveState()

        game.notifyPlayers()
        game.setPlayerOrder()


        # Keep waiting for input if the game is ongoing.
        move.send(game.isOngoing())
