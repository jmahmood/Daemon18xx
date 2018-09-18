from typing import List

from app.base import Player, PublicCompany
from app.state import MutableGameState


class PlayerTurnOrder:
    def __init__(self, state: MutableGameState):
        self.state = state
        self.stacking_type = False  # Keeps the full player order stack and adds current generator on top of stack
        self.replacement_type = False  # Replaces the topmost player turn order generator with this one.
        self.overwrite_type = True  # Replace all player turn order generators.
        self.players: List[Player] = state.players
        self.initial_player: Player = self.players[0]
        self.iteration = 0

    def __iter__(self):
        return self

    def __next__(self) -> Player:
        player_position = self.iteration % len(self.players)
        self.iteration += 1
        return self.players[player_position]

    def isStacking(self):
        return self.stacking_type

    def isOverwrite(self):
        return self.overwrite_type

    def removePlayer(self, player:Player):
        self.players.remove(player)

    def removeCompany(self, company:PublicCompany):
        raise NotImplementedError


class NonRepeatingPlayerTurnOrder(PlayerTurnOrder):
    def __next__(self) -> Player:
        """TODO: Do we want to return the player or the company..??"""
        self.iteration += 1
        return self.players[self.iteration-1]

    def has_next(self) -> bool:
        # iteration starts at 0, the length starts at 1.
        return len(self.players) >= self.iteration + 2


