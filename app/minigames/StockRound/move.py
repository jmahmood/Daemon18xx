import json
from typing import List, Tuple

from app.base import Move, PublicCompany, StockPurchaseSource, MutableGameState
from app.minigames.StockRound.enums import StockRoundType


class StockRoundMove(Move):
    def __init__(self) -> None:
        super().__init__()

        # Sale  Fields
        self.for_sale_raw: List[List] = None
        self.for_sale: List[Tuple[PublicCompany, int]] = None  # A list of stocks you are selling this round.

        # Purchase fields
        self.public_company_id: str = None  # Used for purchase action only.
        self.public_company: PublicCompany = None  # Used for purchase actions only.
        self.source: StockPurchaseSource = None  # Used for purchase actions only
        self.ipo_price: int = None  # Used to set initial price for a stock. (First purchase only)
        self.move_type: StockRoundType = None

    def find_public_company(self, public_company_id: str, kwargs: MutableGameState):
        return next(pc for pc in kwargs.public_companies if pc.id == public_company_id)

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)
        if self.move_type not in [StockRoundType.PASS, StockRoundType.SELL]:
            self.public_company = self.find_public_company(self.public_company_id, kwargs)

        if self.move_type not in [StockRoundType.PASS, StockRoundType.BUY]:
            self.for_sale = []
            if self.for_sale_raw is not None:
                for company_id, amount in self.for_sale_raw:
                    self.for_sale.append((self.find_public_company(company_id, kwargs), amount))

    @staticmethod
    def fromMove(move: "Move") -> "StockRoundMove":
        ret = StockRoundMove()

        msg: dict = json.loads(move.msg)
        ret.public_company_id = msg.get('public_company_id')
        ret.player_id = msg.get("player_id")

        ret.move_type = StockRoundType[msg.get('move_type')]
        ret.ipo_price = int(msg.get("ipo_price", 0))
        ret.source = None if msg.get("source") is None else StockPurchaseSource[msg.get("source")]
        ret.for_sale_raw = msg.get("for_sale_raw")

        return ret
