from app.base import MutableGameState, err
from app.minigames.StockRoundSellPrivateCompany.enums import AuctionResponseType
from app.minigames.StockRoundSellPrivateCompany.move import AuctionDecisionMove
from app.minigames.base import Minigame


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

            old_owner = move.private_company.belongs_to
            move.private_company.belongs_to = move.accepted_player
            if old_owner and hasattr(old_owner, "private_companies"):
                old_owner.private_companies.discard(move.private_company)
            if hasattr(move.accepted_player, "private_companies"):
                move.accepted_player.private_companies.add(move.private_company)
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
                state.stock_round_count > 1,
                "You can't sell a private company in the first stock round."
            ),
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
                state.stock_round_count > 1,
                "You can't sell a private company in the first stock round."
            ),
            err(
                move.player == move.private_company.belongs_to,
                """You can't reject an auction if you do not own the company.""",
                move.accepted_player_id
            ),
        ])
