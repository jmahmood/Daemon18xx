from typing import List

from app.base import Move, Track, Token, Route, PublicCompany, TrackType


class OperatingRoundMove(Move):
    def __init__(self):
        super().__init__()
        self.track_type_id: int = None
        self.track_type: TrackType = None
        self.purchase_token: bool = None  # Will you purchase a token?
        self.construct_track: bool = None  # Will you set a track?
        self.run_route: bool = None  # Will you run a route?
        self.buy_train: bool = None  # Will you buy a train?
        self.pay_dividend: bool = None  # Will you pay a dividend?
        self.routes: List[Route] = None
        self.public_company: PublicCompany = None
        self.token: Token = None
        self.track: Track = None  # Depreciated.
        self.track_placement_location: str = None


class RustedTrainMove(Move):
    pass
