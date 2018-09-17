import json

from app.base import Move, PrivateCompany, Player
from app.minigames.PrivateCompanyStockRoundAuction.enums import PrivateCompanyBidType, AuctionResponseType
from app.state import MutableGameState


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
        return next(pc for pc in state.private_companies if int(pc.order) == private_company_id)

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

