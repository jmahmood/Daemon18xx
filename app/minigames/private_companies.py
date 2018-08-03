import json
from enum import Enum
from typing import List, NamedTuple

from app.base import Move, Player, PrivateCompany
from app.minigames.base import Minigame


class BidType(Enum):
    BUY = 1
    BID = 2
    PASS = 3


class BuyPrivateCompanyMove(Move):
    @staticmethod
    def fromMove(move: "Move") -> "Move":
        ret = BuyPrivateCompanyMove()
        msg: dict = json.loads(move.msg)
        ret.move_type = msg.get('bid_type')
        ret.private_company_order = msg.get('private_company')
        ret.private_company = None
        ret.player_id = msg.get("player")
        ret.player = None
        ret.bid_amount = msg.get("bid_amount")
        return ret

    move_type: BidType

    private_company: PrivateCompany  # This is a unique identifier for the private company in this game.
    private_company_order: str

    player: Player
    player_id: str

    bid_amount: int

    def backfill(self, **kwargs):
        """We do not have all the context when we receive a move; we are only passed a JSON text file, not the
        objects themselves.  We receive the objects from the game object when executing the Minigame.
        We bind those objects when the minigame is run, keeping ID values to allow us to match them up to the object itself"""

        for player in kwargs.get("players"):
            if player.id == self.player_id:
                self.player = player
                break

        for private_company in kwargs.get("private_companies"):
            if private_company.order == self.private_company_order:
                self.private_company = private_company
                break


class BiddingForPrivateCompany(Minigame):
    def errors(self) -> List[str]:
        pass

    def validate_bid(self, move: BuyPrivateCompanyMove):
        # User needs to be one of the users who bid already.
        # User needs to not have passed on this company yet.
        # TODO
        pass

    def validate_pass(self, move: BuyPrivateCompanyMove):
        # User needs to be one of the users who bid already.
        # You can't pass if you are the last user with a bid.
        # TODO
        pass

    def validate_sold(self, move: BuyPrivateCompanyMove):
        """
        If there is only one bidder left who hasn't passed, the stock belongs to him.
        :param move:
        :return:
        """
        all_bidders = set([player_bid.player for player_bid in move.private_company.player_bids])
        all_passers = set([pc.passed_by for pc in move.private_company.passed_by])

        if len(all_bidders - all_passers) == 1:
            purchaser = list(all_bidders - all_passers)[0]
            actual_cost_of_company = max([player_bid.bid_amount for player_bid in move.private_company.player_bids
                 if player_bid.player == purchaser]) # Player buys for max amount he bid.

            move.private_company.set_actual_cost(actual_cost_of_company)
            move.private_company.belongs(move.player)
            return True
        return False

    def run(self, move: BuyPrivateCompanyMove, **kwargs) -> bool:
        move.backfill(**kwargs)

        if BidType.BID == BidType(move.move_type):
            if self.validate_bid(move):
                move.private_company.bid(move.player, move.bid_amount)
                self.validate_sold(move)
                return True

        if BidType.PASS == BidType(move.move_type):
            if self.validate_pass(move):
                move.private_company.passed(move.player)
                self.validate_sold(move)
                return True

        return False

    def next(self, **kwargs) -> str:
        private_companies: List[PrivateCompany] = kwargs.get('private_companies')

        for pc in private_companies:
            if not pc.hasOwner() and not pc.hasBids():
                return "BuyPrivateCompany"

            if not pc.hasOwner() and pc.hasBids():
                return "BiddingForPrivateCompany"

        return "StockRound"


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

        if BidType.BUY == BidType(move.move_type):
            if self.validate_buy(move):
                move.private_company.belongs(move.player)
                return True

        if BidType.BID == BidType(move.move_type):
            if self.validate_bid(move):
                move.private_company.bid(move.player, move.bid_amount)
                return True

        if BidType.PASS == BidType(move.move_type):
            if self.validate_pass(move): # You cannot pass on a free company.
                move.private_company.passed(move.player)
                move.private_company.reduce_price(len(kwargs.get('Players')))
                return True

        return False

    def next(self,  **kwargs) -> str:
        private_companies: List[PrivateCompany] = kwargs.get('private_companies')

        for pc in private_companies:
            if not pc.hasOwner() and not pc.hasBids():
                return "BuyPrivateCompany"

            if not pc.hasOwner() and pc.hasBids():
                return "BiddingForPrivateCompany"

        return "StockRound"
