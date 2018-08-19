import json
from enum import Enum
from typing import List

from app.base import Move, PrivateCompany, err
from app.base import MutableGameState
from app.minigames.PrivateCompanyInitialAuction.enums import BidType
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.minigames.base import Minigame


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
