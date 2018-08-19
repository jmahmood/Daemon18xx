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
    # TODO: Do we really want the move itself to include the private company id of the company being auctioned?
    # I left it in because we may want to ease the life of the UI developer by letting him know when he does
    # something stupid like showing the wrong private company as up for auction.  However, that seems to just
    # complicate the code.  Moving it completely to being a state variable may make more sense.

    # I personally like the idea of including all of the variables, just to make sure internal state and external
    # state are the same.  Maybe that is not a good idea.

    def __init__(self) -> None:
        super().__init__()

        # Purchase fields
        self.private_company_id: str = None  # Used for purchase action only.
        self.private_company: PrivateCompany = None  # Used for purchase actions only.
        self.move_type: PrivateCompanyBidType = None
        self.amount: int = None

    def find_private_company(self, private_company_id: str, state: MutableGameState):
        return next(pc for pc in state.private_companies if pc.order == private_company_id)

    def backfill(self, state: MutableGameState) -> None:
        super().backfill(state)
        self.private_company = self.find_private_company(self.private_company_id, state)

    @staticmethod
    def fromMove(move: "Move") -> "AuctionBidMove":
        ret = AuctionBidMove()

        msg: dict = json.loads(move.msg)
        ret.private_company_id = int(msg.get('private_company_id'))
        ret.player_id = msg.get("player_id")

        ret.move_type = PrivateCompanyBidType[msg.get('move_type')]
        if ret.move_type != PrivateCompanyBidType.PASS:
            ret.amount = int(msg.get("amount"))

        return ret


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

class AuctionResponseType(Enum):
    ACCEPT = 1
    REJECT = 2


class AuctionDecisionMove(Move):

    def __init__(self) -> None:
        super().__init__()

        # Purchase fields
        self.accepted_player: Player = None
        self.move_type: AuctionResponseType = None
        self.accepted_player_id: str = None
        self.accepted_amount: int = 0
        self.private_company: PrivateCompany = None

    def find_private_company(self, private_company_id: str, state: MutableGameState):
        return next(pc for pc in state.private_companies if pc.order == int(private_company_id))

    def backfill(self, state: MutableGameState) -> None:
        super().backfill(state)
        self.private_company = state.auctioned_private_company
        for player in state.players:
            if player.id == self.accepted_player_id:
                self.accepted_player = player
        for player_id, amount in state.auction:
            if player_id == self.accepted_player_id:
                self.accepted_amount = amount

    @staticmethod
    def fromMove(move: "Move") -> "AuctionDecisionMove":
        ret = AuctionDecisionMove()

        msg: dict = json.loads(move.msg)
        ret.private_company_id = msg.get('private_company_id')
        ret.player_id = msg.get("player_id")
        ret.accepted_player_id = msg.get("accepted_player_id")

        ret.move_type = AuctionResponseType[msg.get('move_type')]
        ret.amount = msg.get("amount")

        return ret


class AuctionDecision(Minigame):
    """We don't do all the checks to make sure a player CAN make the move in the auction state array; that should have been
    done in the Auction itself."""

    def next(self, state: MutableGameState) -> str:
        return "StockRound"

    def run(self, move: AuctionDecisionMove, state: MutableGameState) -> bool:
        move.backfill(state)

        if move.move_type == AuctionResponseType.ACCEPT:
            if not self.validateAccept(move, state):
                return False

            move.private_company.belongs_to = move.accepted_player
            move.accepted_player.cash -= move.accepted_amount
            move.player.cash += move.accepted_amount
            state.stock_round_play += 1

            return True

        if move.move_type == AuctionResponseType.REJECT:
            if not self.validateReject(move, state):
                return False
            return True

        return False

    def validateAccept(self, move: AuctionDecisionMove, state: MutableGameState):
        """
        1. Are you accepting a bid from someone who actually made a bid?
        :param move:
        :param state:
        :return:
        """
        return self.validate([
            err(
                move.accepted_player_id in [player_id for player_id, amount in state.auction],
                """You are accepting a bid from a player who didn't make a bid. (ID: "{}")""",
                move.accepted_player_id
            ),
            err(
                move.player == move.private_company.belongs_to,
                """You can't accept an auction if you do not own the company.""",
            ),
            err(
                move.accepted_amount > 0,
                """You cannot accept invalid bids.""",
            ),
        ])

    def validateReject(self, move: AuctionDecisionMove, state: MutableGameState):
        return self.validate([
            err(
                move.player == move.private_company.belongs_to,
                """You can't reject an auction if you do not own the company.""",
                move.accepted_player_id
            ),
        ])
