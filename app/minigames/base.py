from typing import List, Tuple, NamedTuple

import logging

from app.base import Move, MutableGameState


class LifeCycle:
    """
    This is necessary to have minigames perform final changes / deletions / whatever when interacting with the
    state object.
    """
    @staticmethod
    def onStart(kwargs: MutableGameState) -> None:
        pass
        # logging.debug("Minigame started")

    @staticmethod
    def onTurnStart(kwargs: MutableGameState) -> None:
        pass
        # logging.debug("Minigame started")

    @staticmethod
    def onComplete(kwargs: MutableGameState) -> None:
        pass
        # logging.debug("Minigame complete")

    @staticmethod
    def onTurnComplete(kwargs: MutableGameState) -> None:
        pass
        # logging.debug("Minigame turn complete")


class Minigame(LifeCycle):
    """
    A State object for the game, used to evaluate rules that apply only to subsections of the game itself.
    """

    def __init__(self) -> None:
        super().__init__()
        self.error_list: List[str] = []

    def validate(self,
                 possible_errors: List[str]):
        # Clear previous errors before validating a new set of rules
        self.error_list = [err for err in possible_errors if err is not None]
        return len(self.error_list) == 0

    def run(self, move: Move, state: MutableGameState) -> bool:
        raise NotImplementedError()

    def errors(self) -> List[str]:
        return self.error_list

    def next(self, state: MutableGameState) -> str:
        raise NotImplementedError()
