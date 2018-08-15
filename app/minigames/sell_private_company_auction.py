"""During the stock round, or at other times, a player can choose to sell their private company.

To keep things simple, this will trigger an auction where the player can choose the winning bid."""
import json
from enum import Enum

from app.base import Move, MutableGameState, PrivateCompany, err, Player
from app.minigames.base import Minigame


class PrivateCompanyBidType(Enum):
    BID = 1
    PASS = 2


class AuctionBidMove(Move):
    def __init__(self) -> None:
        super().__init__()

        # Purchase fields
        self.private_company_id: str = None  # Used for purchase action only.
        self.private_company: PrivateCompany = None  # Used for purchase actions only.
        self.move_type: PrivateCompanyBidType = None
        self.amount: int = None

    def find_private_company(self, private_company_id: str, kwargs: MutableGameState):
        return next(pc for pc in kwargs.private_companies if pc.id == private_company_id)

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)
        self.private_company = self.find_private_company(self.private_company_id, kwargs)

    @staticmethod
    def fromMove(move: "Move") -> "AuctionBidMove":
        ret = AuctionBidMove()

        msg: dict = json.loads(move.msg)
        ret.private_company_id = msg.get('public_company_id')
        ret.player_id = msg.get("player_id")

        ret.move_type = PrivateCompanyBidType[msg.get('move_type')]
        ret.amount = msg.get("amount")

        return ret


class Auction(Minigame):
    """Auction Private Company"""

    def next(self, state: MutableGameState) -> str:
        if len(state.auction) == len(state.players) - 1:
            return "AuctionDecision"
        else:
            return "Auction"

    def run(self, move: AuctionBidMove, state: MutableGameState) -> bool:

        if move.move_type == PrivateCompanyBidType.PASS:
            if not self.validatePass(move, state):
                return False
            state.auction.add((move.player_id, 0))
            return True

        if move.move_type == PrivateCompanyBidType.BID:
            if not self.validateBid(move, state):
                return False
            state.auction.add((move.player_id, move.amount))
            return True

    def validatePass(self, move: AuctionBidMove, state: MutableGameState):
        return True

    def validateBid(self, move: AuctionBidMove, state: MutableGameState):
        # 1. You need enough money.
        # 2. You need to be bidding on the private company that is up for sale.

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
            )]
        )

class AuctionResponseType(Enum):
    ACCEPT = 1
    REJECT = 2


class AuctionResponseMove(Move):
    def __init__(self) -> None:
        super().__init__()

        # Purchase fields
        self.accepted_player: Player = None
        self.private_company_id: str = None  # Used for purchase action only.
        self.private_company: PrivateCompany = None  # Used for purchase actions only.
        self.move_type: AuctionResponseType = None
        self.accepted_player_id: str = None
        self.accepted_amount: int = None

    def find_private_company(self, private_company_id: str, kwargs: MutableGameState):
        return next(pc for pc in kwargs.private_companies if pc.id == private_company_id)

    def backfill(self, kwargs: MutableGameState) -> None:
        super().backfill(kwargs)
        self.private_company = self.find_private_company(self.private_company_id, kwargs)
        for player in kwargs.players:
            if player.id == self.accepted_player_id:
                self.accepted_player = player

    @staticmethod
    def fromMove(move: "Move") -> "AuctionResponseMove":
        ret = AuctionResponseMove()

        msg: dict = json.loads(move.msg)
        ret.private_company_id = msg.get('public_company_id')
        ret.player_id = msg.get("player_id")
        ret.accepted_player_id = msg.get("player_id")

        ret.move_type = PrivateCompanyBidType[msg.get('move_type')]
        ret.amount = msg.get("amount")

        return ret



class AuctionDecision(Minigame):
    """Auction Private Company"""

    def next(self, state: MutableGameState) -> str:
        return "StockRound"

    def run(self, move: AuctionResponseMove, state: MutableGameState) -> bool:

        if move.move_type == AuctionResponseType.ACCEPT:
            if not self.validateAccept(move, state):
                return False

            move.private_company.belongs_to = move.accepted_player
            move.accepted_player.cash -= move.accepted_amount
            move.player.cash += move.accepted_amount

            return True

        if move.move_type == AuctionResponseType.REJECT:
            # OK this means it's your turn again.
            if not self.validateReject(move, state):
                return False


    def validateAccept(self, move: AuctionResponseMove, state: MutableGameState):
        return True

    def validateReject(self, move: AuctionResponseMove, state: MutableGameState):
        return True
