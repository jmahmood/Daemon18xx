import json
from typing import List, Tuple

from app.base import Move, PublicCompany
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.minigames.PrivateCompanyStockRoundAuction.move import AuctionDecisionMove, AuctionBidMove
from app.minigames.StockRound.move import StockRoundMove
from app.state import MutableGameState


class StockRoundPrivateCompanyAuctionDecisionMoves:
    @staticmethod
    def accept(player_name, accepted_player_name, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        accepted_player = next(
            player for player in state.players if accepted_player_name == player.name
        )

        msg = json.dumps({
            "player_id": player.id,
            "move_type": "ACCEPT",
            "accepted_player_id": accepted_player.id
        })
        move = Move.fromMessage(msg)
        return AuctionDecisionMove.fromMove(move)

    @staticmethod
    def reject(player_name, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = json.dumps({
            "player_id": player.id,
            "move_type": "REJECT",
        })
        move = Move.fromMessage(msg)
        return AuctionDecisionMove.fromMove(move)


class StockRoundPrivateCompanyAuctionMoves:
    @staticmethod
    def pass_on_bid(player_name, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = json.dumps({
            "player_id": player.id,
            "private_company_id": state.auctioned_private_company.order,
            "move_type": "PASS",
        })
        move = Move.fromMessage(msg)
        return AuctionBidMove.fromMove(move)

    @staticmethod
    def bid(player_name, amount, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = json.dumps({
            "player_id": player.id,
            "private_company_id": state.auctioned_private_company.order,
            "move_type": "BID",
            "amount": amount
        })
        move = Move.fromMessage(msg)
        return AuctionBidMove.fromMove(move)




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
    def sell_private_company(player_name, private_company_shortname, state: MutableGameState):
        player = next(
            player for player in state.players if player_name == player.name
        )

        msg = {
            "move_type": "SELL_PRIVATE_COMPANY",
            "player_id": player.id,
            "private_company_shortname": private_company_shortname
        }

        move = Move.fromMessage(json.dumps(msg))
        return StockRoundMove.fromMove(move)

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
