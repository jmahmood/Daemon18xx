import json
from enum import Enum
from typing import List

from app.base import Move, PrivateCompany, err
from app.base import MutableGameState
from app.minigames.PrivateCompanyInitialAuction.enums import BidType
from app.minigames.base import Minigame

class BuyPrivateCompanyMove(Move):
    """
    To generate a Private Company Move, you need to pass in a message that looks like the one below.

        {
            "private_company_order": 1, # int
            "move_type": "BUY",         # ENUM(BUY, BID, PASS)
            "player_id": "A",           # str
            "bid_amount": 0             # int
        }

    The "private_company_order" lets us determine which private company you were thinking about
    when you made the move itself (This also helps if the front-end is showing the wrong private
    company as the current one - we raise an error, and the frontend fixes it.)


    """

    def __init__(self) -> None:
        super().__init__()
        self.private_company: PrivateCompany = None
        self.private_company_order: int = None
        self.move_type: BidType = None
        self.bid_amount: int = None

    def backfill(self, game_state: MutableGameState) -> None:
        super().backfill(game_state)

        private_companies = [pc for pc in game_state.private_companies if pc.order == self.private_company_order]
        self.private_company = private_companies[0]

    @staticmethod
    def fromMove(move: "Move") -> "BuyPrivateCompanyMove":
        ret = BuyPrivateCompanyMove()
        msg: dict = json.loads(move.msg)
        ret.move_type = BidType[msg.get('move_type')]
        ret.private_company_order = msg.get(
            'private_company_order')  # What is the current private company being bid on?
        ret.private_company = None
        ret.player_id = msg.get("player_id")
        ret.player = None
        ret.bid_amount = msg.get("bid_amount")
        return ret
