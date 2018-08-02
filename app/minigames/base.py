from typing import List

from app.base import Move


class Minigame:
    """
    A State object for the game, used to evaluate rules that apply only to subsections of hte game itself.
    """
    def run(self, move: Move, **kwargs) -> bool:
        raise NotImplementedError()

    def errors(self) -> List[str]:
        raise NotImplementedError()

    def next(self, **kwargs) -> str:
        raise NotImplementedError()
