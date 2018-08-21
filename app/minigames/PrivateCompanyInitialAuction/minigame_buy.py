import json
from enum import Enum
from typing import List

from app.base import Move, PrivateCompany, err
from app.base import MutableGameState
from app.minigames.PrivateCompanyInitialAuction.enums import BidType
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.minigames.base import Minigame


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
                if len(pc.player_bids) > 1:
                    return "BiddingForPrivateCompany"
                else:
                    pc.acceptHighestBid()

        return "StockRound"
