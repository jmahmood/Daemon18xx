import json
from typing import List, Tuple

from app.base import MutableGameState, Move, PublicCompany
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.minigames.StockRound.move import StockRoundMove


class StockRoundMoves:
    @staticmethod
    def buy_sell(player_name,
                 buy: str,
                 sell: List[Tuple[str, int]],
                 state: MutableGameState,
                 source: str = "IPO"):
        player = next(
            player for player in state.players if player_name == player.name
        )
        msg = {
            "move_type": "BUYSELL",
            "public_company_id": buy,
            "source": source,
            "player_id": player.id,
            "for_sale_raw": sell
        }

        move = Move.fromMessage(json.dumps(msg))
        return StockRoundMove.fromMove(move)

    @staticmethod
    def sell(player_name, sell: List[Tuple[str, int]], state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )
        msg = {
            "move_type": "BUYSELL",
            "source": "IPO",
            "player_id": player.id,
            "for_sale_raw": sell
        }

        move = Move.fromMessage(json.dumps(msg))
        return StockRoundMove.fromMove(move)

    @staticmethod
    def ipo_buy_sell(player_name,
                     buy: str,
                     sell: List[Tuple[str, int]],
                     ipo_price: int,
                     state: MutableGameState):

        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = {
            "move_type": "BUYSELL",
            "source": "IPO",
            "player_id": player.id,
            "public_company_id": buy,
            "ipo_price": ipo_price,
            "for_sale_raw": sell
        }

        move = Move.fromMessage(json.dumps(msg))
        return StockRoundMove.fromMove(move)

    @staticmethod
    def pass_round(player_name, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = {
            "move_type": "PASS",
            "player_id": player.id
        }

        move = Move.fromMessage(json.dumps(msg))
        return StockRoundMove.fromMove(move)

    @staticmethod
    def sell_private_company():
        pass

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

    @staticmethod
    def pass_on_bid(player_name, privatecompany_shortname, state:MutableGameState):
        company = next(
            company for company in state.private_companies if company.short_name == privatecompany_shortname
        )
        player = next(
            player for player in state.players if player_name == player.name
        )

        move_json = {
            "move_type": "PASS",
            "private_company_order": company.order,  # Doesn't really matter at this point.
            "player_id": player.id,
        }

        move = Move.fromMessage(json.dumps(move_json))
        return BuyPrivateCompanyMove.fromMove(move)
