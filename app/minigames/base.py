from typing import List

from app.base import Move


class Minigame:
    """
    A State object for the game, used to evaluate rules that apply only to subsections of hte game itself.
    """
    error_list: List[str] = []

    def validate(self, possible_errors: dict) -> bool:
        self.error_list = [error_message for error_message, valid in possible_errors.items() if not valid]
        return len(self.error_list) == 0

    def run(self, move: Move, **kwargs) -> bool:
        raise NotImplementedError()

    def errors(self) -> List[str]:
        return self.error_list

    def next(self, **kwargs) -> str:
        raise NotImplementedError()
