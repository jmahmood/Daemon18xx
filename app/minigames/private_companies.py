import json
from enum import Enum
from typing import List

from app.base import Move, PrivateCompany, err
from app.base import MutableGameState
from app.minigames.base import Minigame


class BidType(Enum):
    BUY = 1
    BID = 2
    PASS = 3


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

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)

        private_companies = [pc for pc in kwargs.private_companies if pc.order == self.private_company_order]
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


class BiddingForPrivateCompany(Minigame):
    def validateBid(self, move: BuyPrivateCompanyMove):
        # User needs to be one of the users who bid already.
        # User needs to not have passed on this company yet.
        valid_bidders = [pb.player for pb in move.private_company.player_bids]
        minimum_bid = max([move.private_company.actual_cost] +
                          [pb.bid_amount for pb in move.private_company.player_bids]) + 5

        return self.validate([
            err(
                move.player in valid_bidders,
                "You can't bid on this now, bitterboi."
            ),

            err(
                move.player not in move.private_company.passed_by,
                "You can only keep bidding until you've passed once.",
             ),

            err(
                move.private_company.hasNoOwner(),
                "Someone already owns this cheatingboi. {0}",
                move.private_company.belongs_to
            ),

            err(
                move.player.hasEnoughMoney(move.bid_amount),
                "You cannot afford poorboi. {} (You have: {})",
                move.bid_amount, move.player.cash
            ),

            err(
                move.bid_amount >= minimum_bid,
                "Your bid is too small weenieboi. {} (Minimum Bid: {})",
                move.bid_amount, minimum_bid
            ),

        ])

    def validatePass(self, move: BuyPrivateCompanyMove):
        valid_bidders = [pb.player for pb in move.private_company.player_bids]
        is_valid_bidder = move.player in valid_bidders
        hasnt_passed = move.player not in move.private_company.passed_by
        other_bidder_remain = len(set(valid_bidders) - set(move.private_company.passed_by)) > 1

        return self.validate([
            err(
                is_valid_bidder,
                "You can't pass on this - heck you can't bid on this.  "
                          "There probably is something wrong with your UI implementation that "
                          "is letting you make a move."),

            err(
                hasnt_passed,
                "You already passed on this company."),

            err(
                other_bidder_remain,
                "You are the only bidder left; you can't pass.  You should have received the stock already."
            ),
        ])

    def validateSold(self, move: BuyPrivateCompanyMove):
        """
        If there is only one bidder left who hasn't passed, the stock belongs to him.
        :param move:
        :return:
        """
        all_bidders = set([bidder for bidder, bid_amount in move.private_company.player_bids])
        all_passers = set([pc for pc in move.private_company.passed_by])

        if len(all_bidders - all_passers) == 1:
            purchaser = list(all_bidders - all_passers)[0]
            actual_cost_of_company = max([player_bid.bid_amount for player_bid in move.private_company.player_bids
                                          if player_bid.player == purchaser])  # Player buys for max amount he bid.

            move.private_company.setActualCost(actual_cost_of_company)
            move.private_company.setBelongs(next(player_bid.player for player_bid
                                                 in move.private_company.player_bids
                                                 if player_bid.bid_amount == actual_cost_of_company))
            return True
        return False

    def run(self, move: BuyPrivateCompanyMove, kwargs: MutableGameState) -> bool:
        move.backfill(kwargs)

        if BidType.BID == move.move_type:
            if self.validateBid(move):
                move.private_company.bid(move.player, move.bid_amount)
                self.validateSold(move)
                return True

        if BidType.PASS == move.move_type:
            if self.validatePass(move):
                move.private_company.passed(move.player)
                move.private_company.passed_by.append(move.player)
                self.validateSold(move)
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
    """

    def validateBuy(self, move: BuyPrivateCompanyMove, kwargs: MutableGameState):
        """Ensures you can buy the Private company;
        Player order validations are out of scope"""
        private_companies: List[PrivateCompany] = kwargs.private_companies
        cost_of_private_company = move.private_company.actual_cost
        wrong_order = [pc.name for pc in private_companies
                       if pc.order < move.private_company_order and not pc.hasOwner()]

        return self.validate([
            err(
                move.private_company.hasNoOwner(),
                "Someone already owns this cheatingboi {} / {}",
                move.private_company.name, move.player.id
            ),

            err(
                len(wrong_order) == 0,
                "You can't buy this yet. {0} needs to be sold first.",
                ",".join(wrong_order)
            ),

            err(
                move.player.hasEnoughMoney(cost_of_private_company),
                "You cannot afford poorboi. {} (You have: {})",
                cost_of_private_company, move.player.cash
            ),

            err(
                not move.private_company.hasBids(),
                "You cannot buy something that has a bid on it."
            ),

        ])

    def validateBid(self, move: BuyPrivateCompanyMove, kwargs: MutableGameState):
        minimum_bid = max([move.private_company.actual_cost] +
                          [pb.bid_amount for pb in move.private_company.player_bids]) + 5

        earlier_unsold_private_companies = [pc.name for pc in kwargs.private_companies
                       if pc.order < move.private_company_order and not pc.hasOwner()]

        return self.validate([
            err(move.private_company.hasNoOwner(),
                "Someone already owns this cheatingboi {} {}",
                move.private_company.order,
                move.private_company.belongs_to,
                ),

            err(len(earlier_unsold_private_companies) > 0,
                "You can't bid on this, it's currently for sale"
            ),

            err(move.player.hasEnoughMoney(move.bid_amount),
                "You cannot afford poorboi. {} (You have: {})",
                move.bid_amount, move.player.cash
            ),

            err(move.bid_amount >= minimum_bid,
                "Your bid is too small weenieboi. {} (Minimum Bid: {})",
                move.bid_amount, minimum_bid
            ),
        ])

    def validatePass(self, move: BuyPrivateCompanyMove, kwargs: MutableGameState):
        actual_cost = move.private_company.actual_cost
        return self.validate([
            err(move.private_company.actual_cost > 0,
                "You must purchase the private company if its price has been reduced to zero. ({})",
                actual_cost),
        ])

    def run(self, move: BuyPrivateCompanyMove, kwargs: MutableGameState) -> bool:
        move.backfill(kwargs)

        if BidType.BUY == move.move_type:
            if self.validateBuy(move, kwargs):
                move.private_company.setBelongs(move.player)
                return True

        if BidType.BID == move.move_type:
            if self.validateBid(move, kwargs):
                move.private_company.bid(move.player, move.bid_amount)

                # From the perspective of costs going down, this counts as a pass.
                # Find the earliest unsold company and pass on it.
                earliest_unsold_private_companies = next(pc for pc in kwargs.private_companies
                                                    if pc.order < move.private_company_order and not pc.hasOwner())
                earliest_unsold_private_companies.passed(move.player)
                earliest_unsold_private_companies.reduce_price(kwargs.players)
                return True

        if BidType.PASS == move.move_type:
            if self.validatePass(move, kwargs):
                move.private_company.passed(move.player)
                move.private_company.reduce_price(kwargs.players)
                return True

        return False

    def next(self, kwargs: MutableGameState) -> str:
        private_companies: List[PrivateCompany] = kwargs.private_companies

        for pc in private_companies:
            if not pc.hasOwner() and not pc.hasBids():
                return "BuyPrivateCompany"

            if not pc.hasOwner() and pc.hasBids():
                return "BiddingForPrivateCompany"

        return "StockRound"
