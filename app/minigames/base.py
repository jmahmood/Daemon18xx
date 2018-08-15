from typing import List, Tuple, NamedTuple

import logging

from app.base import Move, MutableGameState


class LifeCycle:
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

    def next(self, state: MutableGameState) -> str:
        raise NotImplementedError()
