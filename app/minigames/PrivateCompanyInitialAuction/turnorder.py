from app.base import Player
from app.state import MutableGameState
from app.turnorder import PlayerTurnOrder


class PrivateCompanyInitialAuctionTurnOrder(PlayerTurnOrder):
    """Only people who bid on an auction can participate durinng the actual auction; players can be removed as well."""
    def __init__(self, state: MutableGameState):
        super().__init__(state)
        current_private_company = next(c for c in self.state.private_companies if c.belongs_to is None)
        self.players = [x.player for x in current_private_company.player_bids]
        self.initial_player: Player = self.players[0]
        self.stacking_type = True
        self.overwrite_type = False
