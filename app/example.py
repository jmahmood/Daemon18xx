"""Example client demonstrating how to drive the game engine.

This module is no longer the main interface for the daemon.  Instead it shows
how a client could interact with the engine purely through function calls.
"""

import json

from app.base import Move
from app.state import Game, apply_move
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove


def example() -> Game:
    """Run a tiny example game and return the final state."""
    players = ["Alice", "Bob"]
    game = Game.start(players)
    game.setPlayerOrder()
    game.setCurrentPlayer()

    msg = json.dumps(
        {
            "private_company_order": 0,
            "move_type": "BUY",
            "player_id": game.current_player.id,
            "bid_amount": 0,
        }
    )
    move = Move.fromMessage(msg)
    buy_move = BuyPrivateCompanyMove.fromMove(move)

    apply_move(game, buy_move)

    return game


if __name__ == "__main__":
    final_game = example()
    company = final_game.state.private_companies[0]
    owner = company.belongs_to.name if company.belongs_to else "None"
    print(f"{company.name} purchased by {owner}")
