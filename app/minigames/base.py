from typing import List, Tuple, NamedTuple

import logging

from app.base import Move, MutableGameState


class MinigameFlow(NamedTuple):
    """Used to determine what the next turn's Minigame class is - and whether we should force a re-order of things
    like player order.

    This is useful when we have the same name of a class (IE Stock round following stock round) and need to
    force a refresh.

    Developers Note
    ---------------

    Note: I am not very comfortable with this class.  It lets the Minigame influence stuff like player order; if possible,
    I want that handled through the Game class exclusively.  This feels like a possible refactoring target.

    Currently we have one class that handles all of the below:
        -> Is the action successful?  Yes or No
        -> Should we increment the player counter? Yes or No
        -> Execute the state changes

    This may make more sense if we have it all split up.
    """
    minigame_class: str
    force_player_reorder: bool
    do_not_increment_player: bool = False  # Player order should not be incremented; like if you reject an auction but still have a move waiting.

class LifeCycle:
    """
    This is necessary to have minigames perform final changes / deletions / whatever when interacting with the
    state object.
    """
    @staticmethod
    def onStart(kwargs: MutableGameState) -> None:
        logging.info("Minigame started")

    @staticmethod
    def onTurnStart(kwargs: MutableGameState) -> None:
        logging.info("Minigame started")

    @staticmethod
    def onComplete(kwargs: MutableGameState) -> None:
        logging.info("Minigame complete")

    @staticmethod
    def onTurnComplete(kwargs: MutableGameState) -> None:
        logging.info("Minigame turn complete")


class Minigame(LifeCycle):
    """
    A State object for the game, used to evaluate rules that apply only to subsections of hte game itself.
    """
    error_list: List[str] = []

    def validate(self,
                 possible_errors: List[str]):
        self.error_list = self.error_list + [err for err in possible_errors if err is not None]
        return len(self.error_list) == 0

    def run(self, move: Move, state: MutableGameState) -> bool:
        raise NotImplementedError()

    def errors(self) -> List[str]:
        return self.error_list

    def next(self, state: MutableGameState) -> MinigameFlow:
        raise NotImplementedError()
