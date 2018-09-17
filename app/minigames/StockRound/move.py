import json
from typing import List, Tuple

import logging

from app.base import Move, PublicCompany, StockPurchaseSource, PrivateCompany
from app.minigames.StockRound.enums import StockRoundType
from app.state import MutableGameState


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

        # Start Private Company Auction
        self.private_company_shortname: str = None  # Used for purchase action only.
        self.private_company: PrivateCompany = None


    def find_private_company(self, private_company_shortname: str, state: MutableGameState):
        return next(pc for pc in state.private_companies if pc.short_name == private_company_shortname)

    def find_public_company(self, public_company_id: str, kwargs: MutableGameState):
        return next(pc for pc in kwargs.public_companies if pc.id == public_company_id)

    def backfill(self, state: MutableGameState) -> None:
        super().backfill(state)
        if self.move_type not in [StockRoundType.PASS, StockRoundType.SELL_PRIVATE_COMPANY, StockRoundType.SELL] and self.public_company_id != None:
            self.public_company = self.find_public_company(self.public_company_id, state)

        if self.move_type not in [StockRoundType.PASS, StockRoundType.SELL_PRIVATE_COMPANY, StockRoundType.BUY]:
            self.for_sale = []
            if self.for_sale_raw is not None and len(self.for_sale_raw) > 0:
                for company_id, amount in self.for_sale_raw:
                    self.for_sale.append((self.find_public_company(company_id, state), amount))

        if self.move_type == StockRoundType.SELL_PRIVATE_COMPANY:
            self.private_company = self.find_private_company(self.private_company_shortname, state)

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

        ret.private_company_shortname = msg.get("private_company_shortname")

        return ret
