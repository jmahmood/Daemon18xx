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
    def __init__(self) -> None:
        super().__init__()
        self.private_company: PrivateCompany = None
        self.private_company_order: int = None
        self.move_type: BidType = None
        self.bid_amount: int = None

    def backfill(self, **kwargs) -> None:
        super().backfill(**kwargs)

        private_companies = [pc for pc in kwargs.get("private_companies") if pc.order == self.private_company_order]
        self.private_company = private_companies[0]

    @staticmethod
    def fromMove(move: "Move") -> "Move":
        ret = BuyPrivateCompanyMove()
        msg: dict = json.loads(move.msg)
        ret.move_type = BidType(msg.get('move_type'))
        ret.private_company_order = msg.get('private_company')
        ret.private_company = None
        ret.player_id = msg.get("player_id")
        ret.player = None
        ret.bid_amount = msg.get("bid_amount")
        return ret


class BiddingForPrivateCompany(Minigame):

    def validate_bid(self, move: BuyPrivateCompanyMove):
        # User needs to be one of the users who bid already.
        # User needs to not have passed on this company yet.
        valid_bidders = [pb.player for pb in move.private_company.player_bids]
        minimum_bid = max([move.private_company.actual_cost] +
                          [pb.bid_amount for pb in move.private_company.player_bids]) + 5

        return self.validate([
            ("You can't bid on this now, bitterboi.",
             move.player in valid_bidders),

            ("You can't only keep bidding until you've passed once.)",
             move.player not in [pc.passed_by for pc in move.private_company.passed_by]),

            ("Someone already owns this cheatingboi. {0}".format(move.private_company.belongs_to.name),
             move.private_company.hasOwner()),

            ("You cannot afford poorboi. {} (You have: {})".format(move.bid_amount, move.player.cash),
             move.player.hasEnoughMoney(move.bid_amount)),

            ("Your bid is too small weenieboi. {} (Minimum Bid: {})".format(move.bid_amount, minimum_bid),
             move.bid_amount >=  minimum_bid),
        ])

    def validate_pass(self, move: BuyPrivateCompanyMove):
        valid_bidders = [pb.player for pb in move.private_company.player_bids]
        is_valid_bidder = move.player in valid_bidders
        hasnt_passed = move.player not in move.private_company.passed_by
        other_bidder_remain = len(set(valid_bidders) - set(move.private_company.passed_by)) > 1

        return self.validate([
            ("You can't pass on this - heck you can't bid on this.  "
             "There probably is something wrong with your UI implementation that is letting you make a move.",
             is_valid_bidder),

            ("You already passed.",
             hasnt_passed),

            ("You are the only bidder left; you can't pass.  You should have received the stock already",
             other_bidder_remain),
        ])



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
            move.private_company.setBelongs(move.player)
            return True
        return False

    def run(self, move: BuyPrivateCompanyMove, **kwargs) -> bool:
        move.backfill(**kwargs)

        if BidType.BID == move.move_type:
            if self.validate_bid(move):
                move.private_company.bid(move.player, move.bid_amount)
                self.validate_sold(move)
                return True

        if BidType.PASS == move.move_type:
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

    def validate_buy(self, move: BuyPrivateCompanyMove, **kwargs):
        """Ensures you can buy the Private company;
        Player order validations are out of scope"""
        private_companies: List[PrivateCompany] = kwargs.get("private_companies")
        cost_of_private_company = move.private_company.actual_cost

        wrong_order = [pc.name for pc in private_companies
            if pc.order < move.private_company_order and not pc.hasOwner()]

        return self.validate([
            ("Someone already owns this cheatingboi. {0}".format(move.private_company.belongs_to.name),
             move.private_company.hasOwner()),

            ("You can't buy this yet. {0}".format(",".join(wrong_order)),
             len(wrong_order) > 0),

            ("You cannot afford poorboi. {} (You have: {})".format(cost_of_private_company, move.player.cash),
             move.player.hasEnoughMoney(cost_of_private_company)),
        ])

    def validate_bid(self, move: BuyPrivateCompanyMove, **kwargs):
        minimum_bid = max([move.private_company.actual_cost] +
                          [pb.bid_amount for pb in move.private_company.player_bids]) + 5

        return self.validate([
            ("Someone already owns this cheatingboi. {0}".format(move.private_company.belongs_to.name),
             move.private_company.hasOwner()),

            ("You cannot afford poorboi. {} (You have: {})".format(move.bid_amount, move.player.cash),
             move.player.hasEnoughMoney(move.bid_amount)),

            ("Your bid is too small weenieboi. {} (Minimum Bid: {})".format(move.bid_amount, minimum_bid),
             move.bid_amount >=  minimum_bid),
        ])

    def validate_pass(self, move: BuyPrivateCompanyMove):
        actual_cost = move.private_company.actual_cost
        return self.validate([
            ("You must purchase the private company if its price has been reduced to zero. ({})".format(actual_cost),
             move.private_company.actual_cost > 0),
        ])

    def run(self, move: BuyPrivateCompanyMove, **kwargs) -> bool:
        """kwargs passes along additional read-only variables that provide context, such as
        the number of players (so you know if you need to reduce the price on a private company)"""

        if BidType.BUY == move.move_type:
            if self.validate_buy(move):
                move.private_company.setBelongs(move.player)
                return True

        if BidType.BID == move.move_type:
            if self.validate_bid(move):
                move.private_company.bid(move.player, move.bid_amount)
                return True

        if BidType.PASS == move.move_type:
            if self.validate_pass(move):
                move.private_company.passed(move.player)
                move.private_company.reduce_price(len(kwargs.get('players')))
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
