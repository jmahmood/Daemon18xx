import json

from app.base import MutableGameState, Move
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove

class PrivateCompanyInitialAuctionMoves:
    @staticmethod
    def bid(player_name, privatecompany_shortname, amount, state:MutableGameState):
        company = next(
            company for company in state.private_companies if company.short_name == privatecompany_shortname
        )
        player = next(
            player for player in state.players if player_name == player.name
        )

        move_json = {
            "move_type": "BID",
            "private_company_order": company.order,  # Doesn't really matter at this point.
            "player_id": player.id,
            "bid_amount": amount
        }

        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)

    @staticmethod
    def buy(player_name, privatecompany_shortname, state:MutableGameState):
        company = next(
            company for company in state.private_companies if company.short_name == privatecompany_shortname
        )
        player = next(
            player for player in state.players if player_name == player.name
        )

        move_json = {
            "move_type": "BUY",
            "private_company_order": company.order,  # Doesn't really matter at this point.
            "player_id": player.id,
        }

        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)
