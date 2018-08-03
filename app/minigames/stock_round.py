from enum import Enum
from typing import List

from app.base import Move, PublicCompany, StockPurchaseSource, Player
from app.minigames.base import Minigame


class StockRoundType(Enum):
    BUY = 1
    SELL = 2
    PASS = 3
    SELL_PRIVATE_COMPANY = 4    # TODO - may choose to move it to a different minigame, since it involves player interaction


class StockRoundMove(Move):
    def __init__(self):
        super().__init__()
        self.player: Player = None
        self.source: StockPurchaseSource = None
        self.public_company: PublicCompany = None
        self.amount: int = None
        self.move_type: StockRoundType = None

    def backfill(self, **kwargs) -> None:
        pass

    @staticmethod
    def fromMove(move: "Move") -> "Move":
        ret = StockRoundMove()
        return ret


class StockRound(Minigame):
    """Buy / Sell Public Companies, Private Companies"""
    def errors(self) -> List[str]:
        pass

    def run(self, move: StockRoundMove, **kwargs) -> bool:
        move.backfill(**kwargs)


        if StockRoundType.BUY == StockRoundType(move.move_type):
            if self.validate_buy(move):
                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1

                # move.amount can only equal 1 if you are buying.
                move.public_company.buy(move.player, move.source, move.amount)
                move.public_company.checkPresident()
                move.public_company.checkFloated()

                return True

        if StockRoundType.SELL == StockRoundType(move.move_type):
            if self.validate_sell(move):
                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1

                move.public_company.sell(move.player, move.amount)
                move.public_company.checkPresident()
                return True

        if StockRoundType.PASS == StockRoundType(move.move_type):
            if self.validate_pass(move):
                kwargs['stock_round_play'] = kwargs['stock_round_play'] + 1
                kwargs['stock_round_passed'] = kwargs['stock_round_passed'] + 1
                # If every player passes during the stock round, the round is over.
                return True

    def next(self, **kwargs) -> str:
        players: List[Player] = kwargs.get('players')
        if kwargs['stock_round_play'] % len(players) == 0 \
                and kwargs['stock_round_play'] > 0 \
                and kwargs['stock_round_passed'] == len(players):
            public_companies: List[PublicCompany] = kwargs.get('public_companies')
            for public_company in public_companies:
                public_company.checkPriceIncrease()
                return "OperatingRound"
        return "StockRound"

    def validate_buy(self, move: StockRoundMove) -> bool:
        pass

    def validate_sell(self, move: StockRoundMove) -> bool:
        # You can only sell stock you own
        # You can only sell the amount you own.
        pass

    def validate_pass(self, move: StockRoundMove):
        pass

