from typing import List, Dict, Tuple

from app.base import PrivateCompany, PublicCompany, Player, Track, Train
from app.game_map import GameBoard


class MutableGameState:
    """This is state that needs to be accessed or modified by the minigames.
    We are initially putting all of that into this one object, but this will be refactored once the
    minigames are ready (and we can distinguish between mutable & non-mutable game state)"""

    def __init__(self):
        """
        players: All the players who are playing the game, from "right to left" (ie: in relative order for the stock round)
        """
        self.board: GameBoard = None
        self.auction: List[Tuple[str, int]] = None  # All bids on current auction; (player_id, amount)
        self.auctioned_private_company: PrivateCompany = None
        self.sales: List[Dict[Player, List[PublicCompany]]] = []  # Full list of things you sell in each stock round.
        self.purchases: List[Dict[Player, List[PublicCompany]]] = []  # Full list of things you buy in each stock round.
        self.public_companies: List["PublicCompany"] = None
        self.private_companies: List["PrivateCompany"] = None
        self.stock_round_passed_in_a_row: int = 0  # If every player passes during the stock round, the round is over.
        self.stock_round_play: int = 0
        self.stock_round_count: int = 0
        self.stock_round_last_buyer_seller_id: str = None
        self.players: List[Player] = None

        self.trains: List[Train] = None  # A list of trains that are available
        self.rusted_trains: List[Train] = None # Trains that have rusted
        self.unavailable_trains: List[Train] = None # Trains that have not yet been made available

        # [Phase:[Turn, Turn, Turn], Phase: [Turn, Turn, Turn]]
        self.operating_round_turn: int = 0  # Turns within a single operating round.
        self.operating_round_phase: int = 1  # Turns within a single operating round.

        self.total_operating_round_phases: int = 1 # How many times the operating round needs to be repeated.
        self.total_operating_rounds: int = 1

    def isAnotherCompanyWaiting(self):
        """This is used to message the player order system to see if there is
        another company that is supposed to go this round."""
        return self.operating_round_turn < len([p for p in self.public_companies if p.isFloated()])

    def trackUsed(self, track: Track):
        # TODO: P1: Refresh the graph used in the game board
        pass

    def trackAvailable(self, track: Track):
        # TODO: P2:  Allow the track to be reused.
        pass