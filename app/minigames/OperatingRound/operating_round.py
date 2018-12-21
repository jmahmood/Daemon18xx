from typing import List

from app.base import Move, Track, Token, Route, PublicCompany, TrackType
from app.state import MutableGameState


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
        self.public_company_name: str = None
        self.public_company: PublicCompany = None
        self.token: Token = None
        self.token_placement_location: str = None
        self.token_placement_city: str = None  # If you have two cities in the same hex, you need this to tell where to place.
        self.track: Track = None
        self.track_type: TrackType = None
        self.track_placement_location: str = None
        self.track_type_id: str = None

    def backfill(self, state) -> None:
        """This can throw an error if you sent it something wrong.
        The token location should be a string in all lower characters
        The track type id should be a number.  (Not sure what to do about 'oo', thinking abotu it."""
        super().backfill(state)
        self._prepareCompany(state)
        self._prepareToken(state)
        self._prepareTrack(state)

    def _prepareCompany(self, game_state: MutableGameState):
        self.public_company = next(pc for pc in game_state.public_companies
                                   if pc.short_name == self.public_company_name)

    def _prepareToken(self, game_state: MutableGameState):
        hex = game_state.board.game_map.mapHexConfig.get(self.track_placement_location)
        if hex is None:
            self.token = Token(
                public_company=self.public_company,
                city=None,
                location=self.token_placement_city
            )

        else:
            self.token = Token(
                public_company=self.public_company,
                city=next(city for city in hex.cities if city.name == self.token_placement_city),
                location=self.token_placement_location
            )

    def _prepareTrack(self, game_state: MutableGameState):
        self.track_type = next(track for track in game_state.board.game_tracks.ALL_TRACK_TYPES if track.type_id == self.track_type_id)
        self.track = game_state.board.getAvailableTrack(self.track_type_id)


class RustedTrainMove(Move):
    pass
