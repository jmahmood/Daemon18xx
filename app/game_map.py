from typing import List, Dict, Tuple, Set
import networkx as nx
from app.base import City, Track, PublicCompany, PrivateCompany, TrackType, Town, DATA_DIR


class MapHexConfig:
    """We use this to keep information about individual map hexes, and about cities within the hex."""

    def __init__(self):
        self.location: str = None  # A9 or whatever
        self.track: Track = None  # The current track laid down, or null if nothing.
        self.cities: List[City] = None  # Cities in that hex.
        self.towns: List[Town] = None  # Towns in that hex.
        self.stations: Dict[City, Set[PublicCompany]] = None
        self.cost: int = None  # Cost to upgrade track here.

        self.requires_private_company: PrivateCompany = None

        # TODO: Do we want to make self.edges into a set instead of list so we can use subset?
        self.edges: List[Tuple[str, str]] = None  # All edges created by the current tile that was laid down.

    def recalculateEdges(self):
        # Creates a new set of edges based on any track placements.
        pass


class GameMap:
    """Container for all map locations"""
    def __init__(self):
        self.map: Dict[str, MapHexConfig] = {}
        self.graph = nx.Graph()

    def initialize(self):
        """Loads all static map data."""
        pass


class GameTracks:
    """Contains logic that confirms whether or not a track is available, and allows you to place it / etc.."""
    def __init__(self):
        self.ALL_TRACK_TYPES: List[TrackType] = []
        self.ALL_TRACK: List[Track] = []
        self.available_track: List[Track] = []

    def initialize(self):
        """Loads all static data related to the game from data files"""
        self.ALL_TRACK_TYPES = TrackType.load()
        self.ALL_TRACK = Track.GenerateTracks(self.ALL_TRACK_TYPES)
        self.available_track = [t for t in self.ALL_TRACK]


class GameBoard(object):
    """Top-level class / public interface to the map and other parts of the underlying game board."""

    def __init__(self):
        self.game_map: GameMap = None
        self.game_tracks: GameTracks = None

    def hasExternalConnection(self, vertex_label):
        """Determines if it is facing off-board or to a gray tile (IE: violating rules of game)"""
        # TODO - Check if any connections exist to the vertex in teh graph.
        return False

    def isValidLocation(self, location: str) -> bool:
        return location in self.game_map.map.keys()

    def findPaths(self, cities: List[str], location: str) -> List:
        # TODO: Not implemented
        raise NotImplementedError("Add path finding to location")

    def canPlaceTrack(self, location: str, track: Track) -> bool:
        existing_track = self.game_map.map.get(location).track
        if existing_track:
            return existing_track.type.can_upgrade_to(track.type)
        return False

    def placeTrack(self, location: str, track: Track) -> Track:
        """We return the old track so it can be returned to the list of available track types."""
        config = self.game_map.map.get(location)
        pre_existing_track = config.track
        config.track = track
        config.recalculateEdges()
        return pre_existing_track

    def canSetStation(self, public_company: PublicCompany, city: City, location: str) -> bool:
        # TODO: Do we want to have this here or at the move level?
        pass
        # config = self.game_map.map[location]
        #
        #
        # current_stations = config.stations[city]
        # current_number_of_stations = len(config.stations[city])
        # max_number_of_stations = config.track.type.city_1_stations
        # return max_number_of_stations <= current_number_of_stations + 1

    def setStation(self, public_company: PublicCompany, city: City, location: str):
        config = self.game_map.map[location]
        config.stations.get(city).add(public_company)

    def calculateRoute(self, route) -> int:
        raise NotImplementedError()

    def updateRoutes(self):
        raise NotImplementedError()

    def getCost(self, location: str):
        try:
            return self.game_map.map.get(location).cost
        except KeyError:
            raise KeyError("Location {} does not exist in game map".format(location))

    def validatePlaceTrack(self, track: Track, location: str) -> bool:
        raise NotImplementedError

    def validatePlaceStation(self, company: PublicCompany, city: City, location: str) -> bool:
        config = self.map[location]
        if not config.cities or len(config.cities) == 0:
            return False

        if city not in config.cities:
            return False

        if len(config.stations.get(city)) >= city.stations:
            return False

        if company in config.stations.get(city):
            return False

    def findCompanyStationCities(self, company:PublicCompany) -> List[str]:
        """Returns a list of names of cities with a station of the company"""
        # TODO: Do we want to cache this information somewhere?  Possibly in the company itself?
        ret = []

        for loc in self.game_map.map.keys():
            map_hex = self.game_map.map.get(loc)
            cities = map_hex.cities
            for c in cities:
                companies = map_hex.stations.get(c)
                if company in companies:
                    ret.append(c.name)
        return ret

    def generateCompanyGraph(self, company: PublicCompany):
        pass

    def generatePath(self, company: PublicCompany, frm: City, to: City):
        # Generates all simple paths that will lead from one city to the other, within the graph for the company.
        # Then filters out all paths that are not acceptable for one reason or another.
        pass
