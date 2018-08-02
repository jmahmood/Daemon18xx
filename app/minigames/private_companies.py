from enum import Enum
from typing import List, NamedTuple

from app.base import Move, Player, PrivateCompany
from app.minigames.base import Minigame


class BidType(Enum):
    BUY = 1
    BID = 2
    PASS = 3


class BuyPrivateCompanyMove(Move):
    bid_type: BidType
    private_company: PrivateCompany  # This is a unique identifier for the private company in this game.
    player: Player
    bid_amount: int


class BuyPrivateCompany(Minigame):
    """
    Used for the initial auction round of Private Companies
    Move:
    """

    def validate_buy(self, move: BuyPrivateCompanyMove):
        pass

    def validate_bid(self, move: BuyPrivateCompanyMove):
        pass

    def validate_pass(self, move: BuyPrivateCompanyMove):
        return move.private_company.actual_cost > 0

    def errors(self) -> List[str]:
        pass

    def run(self, move: BuyPrivateCompanyMove, **kwargs) -> bool:
        """kwargs passes along additional read-only variables that provide context, such as
        the number of players (so you know if you need to reduce the price on a private company)"""

        if BidType.BUY == BidType(move.bid_type):
            if self.validate_buy(move):
                move.private_company.belongs(move.player)
                return True

        if BidType.BID == BidType(move.bid_type):
            if self.validate_bid(move):
                move.private_company.bid(move.player, move.bid_amount)
                return True

        if BidType.PASS == BidType(move.bid_type):
            if self.validate_pass(move): # You cannot pass on a free company.
                move.private_company.passed()
                move.private_company.modify_price(len(kwargs.get('Players')))
                return True

        return False

    def next(self,  **kwargs) -> str:
        private_companies: List[PrivateCompany] = kwargs.get('private_companies')

        for pc in private_companies:
            if not pc.hasOwner() and not pc.hasBids():
                return "BuyPrivateCompany"
            if not pc.hasOwner() and pc.hasBids():
                return "BiddingForPrivateCompany"

        return "BuyStock"
