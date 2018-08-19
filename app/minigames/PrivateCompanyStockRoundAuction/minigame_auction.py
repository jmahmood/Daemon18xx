from app.base import MutableGameState, err
from app.minigames.PrivateCompanyStockRoundAuction.enums import PrivateCompanyBidType
from app.minigames.PrivateCompanyStockRoundAuction.move import AuctionBidMove
from app.minigames.base import Minigame


class Auction(Minigame):
    """Auction Private Company"""

    def next(self, state: MutableGameState) -> str:
        if len(state.auction) == len(state.players) - 1:
            return "AuctionDecision"
        else:
            return "Auction"

    def run(self, move: AuctionBidMove, state: MutableGameState) -> bool:
        move.backfill(state)

        if move.move_type == PrivateCompanyBidType.PASS:
            if not self.validatePass(move, state):
                return False
            state.auction.append((move.player_id, 0))
            return True

        if move.move_type == PrivateCompanyBidType.BID:
            if not self.validateBid(move, state):
                return False
            state.auction.append((move.player_id, move.amount))
            return True

    def validatePass(self, move: AuctionBidMove, state: MutableGameState):
        return self.validate([
            err(
                move.player != state.auctioned_private_company.belongs_to,
                "You can't pass (or bid) on your own company.",
                move.private_company.name,
                state.auctioned_private_company.name
            ),
        ])

    def validateBid(self, move: AuctionBidMove, state: MutableGameState):
        return self.validate([
            err(
                move.player.hasEnoughMoney(move.amount),
                "You cannot afford poorboi. {} (You have: {})",
                move.amount, move.player.cash
            ), err(
                move.private_company == state.auctioned_private_company,
                "You are bidding on the wrong company numbnuts. {} vs. {}"
                " Probably something wrong with your UI system.",
                move.private_company.name,
                state.auctioned_private_company.name
            ), err(
                move.player != state.auctioned_private_company.belongs_to,
                "You can't bid on your own company.",
                move.private_company.name,
                state.auctioned_private_company.name
            ), err(
                move.amount >= int(state.auctioned_private_company.cost / 2),
                "You are paying too little.  Your bid must be 1/2 to 2 times the price of the company ({} to {}).",
                int(move.private_company.cost / 2),
                move.private_company.cost * 2
            ), err(
                move.amount <= int(state.auctioned_private_company.cost * 2),
                "You are paying too much.  Your bid must be 1/2 to 2 times the price of the company ({} to {}).",
                int(move.private_company.cost / 2),
                move.private_company.cost * 2
            ),

        ]
        )
