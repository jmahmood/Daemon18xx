# TODO: Create structure of how the Operating Round works
from typing import List, NamedTuple

from app.base import PrivateCompany, Move, GameBoard, Track, Token
from app.minigames.base import Minigame


class OperatingRoundMove(Move):
    def __init__(self):
        super().__init__()
        self.token: Token = None
        self.track: Track = None

    pass


class OperatingRound(Minigame):

    def next(self, **kwargs) -> str:
        pass

    def run(self, move: OperatingRoundMove, **kwargs) -> bool:
        move.backfill(**kwargs)

        return False

    def constructTrack(self, move: OperatingRoundMove, **kwargs):
        track = move.track
        board: GameBoard = kwargs.get("board")
        if self.isValidTrackPlacement(track):
            board.set(track)
            # TODO: Auto-add token if it is the company's home territory.


    def purchaseToken(self, move: OperatingRoundMove, **kwargs):
        token = move.token
        board: GameBoard = kwargs.get("board")
        if self.isValidTokenPlacement(token):
            board.setToken(token)
        pass

    def runTrains(self, move: OperatingRoundMove):
        pass

    def payDividends(self, move: OperatingRoundMove):
        pass

    def purchaseTrain(self, move: OperatingRoundMove):
        pass

    @staticmethod
    def onStart(**kwargs) -> None:
        private_companies: List[PrivateCompany] = kwargs.get("private_companies")
        for pc in private_companies:
            pc.distributeRevenue()

        # Find and set the public companies that have already been floated.

    def isValidTokenPlacement(self, token):
        return self.validate([
            ("There is no track there", False),
            ("There are no free spots to place a token", False),
            ("You cannot connect to the location to place a token", False),
            ("You cannot put two tokens for the same company a location", False),
            ("There are no remaining tokens for that company", False),
            ("You cannot place more than one token in one turn", False),
            ("You cannot place a token in Erie's home town before Erie", False)
        ])

    def isValidTrackPlacement(self, track):
        # TODO
        # Probably will have to implement a path finding algorithm for each company.
        # Dykstra's algo for tracks :o
        return self.validate([
            ("Your track needs to be on a location that exists", False),
            ("Someone has already set a tile there", False),
            ("Your track needs to connect to your track or it needs to be your originating city, "
             "except in special cases (the base cities of the NYC and Erie, "
             "and the hexagons containing the C&SL and D&H Private Companies)", False),
            ("You can only lay one tile", False),
            ("You need to have a yellow tile before laying a green tile", False),
            ("You need to have a green tile before laying an orange tile", False),
            ("A tile may not be placed so that a track runs off the grid", False),
            ("A tile may not terminate against the blank side of a grey hexagon", False),
            ("A tile may not terminate against a solid blue hexside in a lake or river", False),
            ("You don't have enough money to build tile there", False),
            ("That tile requires the company to own a Private Company ({})", False),
            ("That location requires you to use a tile that has one city", False),
            ("That location requires you to use a tile that has two city", False),
            ("That location requires you to use a tile that has one town", False),
            ("That location requires you to use a tile that has two towns", False),
            ("Replacement tiles must maintain all previously existing route connections", False),
            ("You cannot access that tile from your company", False)
        ])


