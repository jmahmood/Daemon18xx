from app.base import Move
from app.minigames.base import Minigame


class TrainsRusted(Minigame):
    """Your trains rusted and you have nothing left.  Absolutely not kosher."""
    # TODO: Works like an auction.  How are we modelling auctions elsewhere?

    def next(self, **kwargs) -> str:
        pass

    def run(self, move: Move, **kwargs) -> bool:
        pass