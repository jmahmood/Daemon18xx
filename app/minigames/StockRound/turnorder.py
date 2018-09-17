from app.base import Player
from app.state import MutableGameState
from app.turnorder import PlayerTurnOrder


class StockRoundTurnOrder(PlayerTurnOrder):
    """In the stock round, we start the round with the player after the last buyer."""
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        try:
            self.iteration = next(i for i, p in enumerate(self.players)
                 if p.id == self.state.stock_round_last_buyer_seller_id) + 1 % len(self.players)
        except StopIteration:
            self.iteration = 0


class StockRoundSellPrivateCompanyTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        """Create a pivot (is that what we call it?) around the owner so that players are asked in order from his left
        whether or not they want to buy his private company"""
        super().__init__(state)
        owner = state.auctioned_private_company.belongs_to
        idx = state.players.index(owner)

        self.players = state.players[idx + 1:len(state.players)] + state.players[0:idx]
        self.initial_player: Player = self.players[0]
        self.stacking_type = True
        self.overwrite_type = False


class StockRoundPrivateCompanyDecisionTurnOrder(PlayerTurnOrder):
    def __init__(self, state: MutableGameState):
        """Create a pivot (is that what we call it?) around the owner so that players are asked in order from his left
        whether or not they want to buy his private company"""
        super().__init__(state)
        self.players = [state.auctioned_private_company.belongs_to]
        self.stacking_type = False
        self.overwrite_type = False
        self.replacement_type = True