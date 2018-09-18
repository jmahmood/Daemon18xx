import json
from typing import List, Dict, Tuple, Set

import networkx as nx
from app.base import City, Town, Track, TrackType, Player, PublicCompany, PrivateCompany


class MapHexConfig:
    """We use this to keep information about individual map hexes, and about cities within the hex."""
    def __init__(self):
        self.location: str = None  # A9 or whatever
        self.track: Track = None  # The current track laid down, or null if nothing.
        self.cities: List[City] = None  # Cities currently that are there
        self.stations: Dict[City, Set[PublicCompany]] = None
        self.cost: int = None  # Cost to upgrade track here.

        self.requires_private_company: PrivateCompany = None

        #TODO: Do we want to make self.edges into a set instead of list so we can use subset?
        self.edges: List[Tuple[str, str]] = None  # All edges created by the current tile that was laid down.

    def recalculate_edges(self):
        # Creates a new set of edges based on any track placements.
        pass


class GameMap:
    def __init__(self):
        self.towns: List[Town] = None
        self.cities: List[City] = None
        self.track_types: Dict[str, TrackType] = None
        self.tracks: List[Track] = None
        self.map: Dict[str, MapHexConfig] = {}

    def validatePlaceTrack(self, track: Track, location: str) -> bool:
        raise NotImplementedError

    def placeTrack(self, location: str, track: Track) -> Track:
        config = self.map.get(location)
        pre_existing_track = config.track
        config.track = track
        config.recalculate_edges()

        return pre_existing_track

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

    def placeStation(self, company: PublicCompany, city: City, location: str):
        config = self.map[location]
        config.stations.get(city).add(company)

    def findCompanyStationCities(self, company:PublicCompany) -> List[str]:
        """Returns a list of names of cities with a station of hte company"""
        ret = []

        for loc in self.map.keys():
            map_hex = self.map.get(loc)
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


class GameBoard:
    """Interfaces with classes in the game_map file?  Or do we want to merge this with those?"""

    def __init__(self):
        self.game_map: "GameMap" = None
        self.board = {}
        self.graph = nx.Graph()
        self.all_track: List[Track] = []
        self.available_track: List[Track] = []
        self.initialize()

    def initialize(self):
        with open('/Users/jawaad/PycharmProjects/Daemon1830/app/data/public_companies') as f:
            tracks = json.load(fp=f)
            for t in tracks:
                self.all_track.append(
                    Track(
                        id=t["id"],
                        color=t["color"],
                        description=t["description"],
                        rotation=None
                    )
                )

    def hasExternalConnection(self, vertex_label):
        """Determines if it is facing off-board or to a gray tile (IE: violating rules of game)"""
        # TODO - Check if any connections exist to the vertex in teh graph.
        return False

    def isValidLocation(self, location: str) -> bool:
        return location in self.game_map.map.keys()

    def canPlaceTrack(self, location: str, track: Track) -> bool:
        existing_track = self.game_map.map.get(location).track
        if existing_track:
            return existing_track.type.can_upgrade_to(track.type)
        return False

    def findPaths(self, cities: List[str], location: str) -> List:
        # TODO: Not implemented
        raise NotImplementedError("Add path finding to location")

    def setTrack(self, location: str, track: Track) -> Track:
        return self.game_map.placeTrack(location, track)

    def setToken(self, public_company: PublicCompany, city: City, location: str):
        return self.game_map.placeStation(public_company, city, location)

    def calculateRoute(self, route) -> int:
        raise NotImplementedError()

    def updateRoutes(self):
        raise NotImplementedError()

    def getCost(self, location: str):
        try:
            return self.game_map.map.get(location).cost
        except KeyError:
            raise KeyError("Location {} does not exist in game map".format(location))
