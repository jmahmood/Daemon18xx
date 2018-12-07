import logging
from typing import List, Dict, Tuple, Set, Union
import networkx as nx
from app.base import City, Track, PublicCompany, PrivateCompany, TrackType, Town, DATA_DIR
from app.error_handling import ErrorListValidator


class MapHexConfig:
    """We use this to keep information about individual map hexes, and about cities within the hex."""
    def __str__(self):
        return self.location

    def __hash__(self) -> int:
        return hash(self.location)

    def __eq__(self, o: "MapHexConfig") -> bool:
        return self.location == o.location

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

    def getCities(self):
        return self.cities

    def getTowns(self):
        return self.towns

    def hasStation(self, city:City, pc: PublicCompany):
        return pc in self.getStations(city)

    def getStations(self, city: City):
        return self.stations.get(city)

    def getCompanyStations(self, company: PublicCompany):
        return [city for city in self.stations.keys() if company in self.stations[city]]

    def isFull(self, city:City):
        if city not in self.cities:
            raise NotImplemented("How to handle someone getting cheeky with the city they pass?")
        return city.stations < len(self.stations.get(city))


    def recalculateEdges(self):
        # Creates a new set of edges based on any track placements.
        pass


class GameMap:
    """Container for all map locations"""
    def __init__(self):
        self.map: Dict[str, MapHexConfig] = {}
        self.graph = nx.Graph()
        self.companyGraph: Dict[PublicCompany, nx.Graph] = {}

    def initialize(self):
        """Loads all static map data."""
        pass

    def getNodeConfig(self, node) -> MapHexConfig:
        raise NotImplemented()

    def getNodeCity(self, node) -> City:
        raise NotImplemented()

    def isCity(self, node) -> bool:
        return False

    def invalidateCompanyGraph(self, pc: PublicCompany):
        # When there is a new placement, the company graph may change so this needs to be invalidated.
        pass

    def getCompanyGraph(self, pc: PublicCompany):
        if pc not in self.companyGraph.keys():
            self.companyGraph[pc] = self.generateCompanyGraph(pc)
        return self.companyGraph.get(pc)

    def generateCompanyGraph(self, pc: PublicCompany):
        company_graph = nx.create_empty_copy(self.graph)  # Creates a copy with all nodes, but no edges.
        nbunch = set([city for location, city in self.getCompanyStations(pc)])
        explored = set()

        while len(nbunch.difference(explored)) > 0:
            to_explore = list(nbunch.difference(explored))
            explored = explored.union(nbunch)

            non_terminal_nodes = set([])

            for node in to_explore:
                if self.isCity(node):
                    city = self.getNodeCity(node)
                    city_config = self.getNodeConfig(node)
                    if city_config.isFull(city) and not city_config.hasStation(city, pc):
                        continue
                non_terminal_nodes.add(node)

            company_graph.add_edges_from(
                nx.edges(self.graph, non_terminal_nodes)
            )

            nbunch = set()
            for node in non_terminal_nodes:
                for neighbor in nx.neighbors(self.graph, node):
                    nbunch.add(neighbor)

        return company_graph

    # def getAdjacent(self, location) -> List[MapHexConfig]:
    #     # https://networkx.github.io/documentation/networkx-1.10/reference/generated/networkx.Graph.neighbors.html#networkx.Graph.neighbors
    #     return self.graph[location]

    def get(self, location: str) -> MapHexConfig:
        return self.map.get(location)

    def getCompanyStations(self, company: PublicCompany) -> [Tuple[str, str]]:
        """Returns location, city tuple for stations that belong to the company"""
        # TODO: P4: Cache this information instead of building it from scratch?
        ret = []
        for location in self.map.keys():
            stations = self.map[location].getCompanyStations(company)
            if len(stations) > 0:
                for city in stations:
                    ret.append((location, city))

        return ret

    def locations(self):
        return self.map.keys()


class GameTracks:
    """Contains logic that confirms whether or not a track is available, and allows you to place it / etc.."""
    # TODO: P2: Add a class function to check for a track being valid and available.  Add to GameBoard as well.
    def __init__(self):
        self.ALL_TRACK_TYPES: List[TrackType] = []
        self.ALL_TRACK: List[Track] = []
        self.available_track: List[Track] = []

    def initialize(self):
        """Loads all static data related to the game from data files"""
        self.ALL_TRACK_TYPES = TrackType.load()
        self.ALL_TRACK = Track.GenerateTracks(self.ALL_TRACK_TYPES)
        self.available_track = [t for t in self.ALL_TRACK]


class GameBoard(ErrorListValidator):
    """Top-level class / public interface to the map and other parts of the underlying game board."""

    def __init__(self):
        self.game_map: GameMap = None
        self.game_tracks: GameTracks = None
        self.error_list = []

    def doesRouteExist(self, pc: PublicCompany, start: str, end: str):
        company_graph = self.game_map.getCompanyGraph(pc)
        return nx.has_path(company_graph, start, end)

    def doesCityRouteExist(self, pc: PublicCompany, start: Union[City, Town], end: Union[City, Town]):
        return self.doesRouteExist(pc, start.name, end.name)

    def hasExternalConnection(self, vertex_label):
        """Determines if it is facing off-board or to a gray tile (IE: violating rules of game)."""
        # TODO: P4 - Check if any connections exist to the vertex in the graph.
        return False

    def isValidLocation(self, location: str) -> bool:
        return location in self.game_map.locations()

    def findPaths(self, cities: List[Union[City, Town]], location: str) -> List:
        # TODO: P1 - Not implemented
        raise NotImplementedError("Add path finding to location")

    def canPlaceTrack(self, location: str, track: Track) -> bool:
        existing_track = self.game_map.get(location).track
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
        # TODO: P1 - Do we want to have this here or at the move level?
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
            return self.game_map.get(location).cost
        except KeyError:
            raise KeyError("Location {} does not exist in game map".format(location))

    def validatePlaceTrack(self, track: Track, location: str) -> bool:
        raise NotImplementedError

    def validatePlaceStation(self, company: PublicCompany, city: City, location: str) -> bool:
        # TODO: P1: Should we be setting errors within a "Game Map" class?
        config = self.game_map.map[location]

        self.validator(
            (
                config.getCities() and len(config.getCities()) > 0,
                "Can't place a station if there are no cities"
            ),
            (
                city in config.cities,
                "Can't place a station if there are no cities"
            ),
            (
                len(config.stations.get(city)) < city.stations,
                "Can't place a station if the city is full"
            ),
            (
                company not in config.stations.get(city),
                "Can't place a station if you already placed one there."
            ),
        )
        if len(self.error_list) > 0:
            logging.warning(self.error_list)

        return len(self.error_list) == 0

    def findCompanyStationCities(self, company: PublicCompany) -> List[City]:
        """Returns a list of names of cities with a station of the company"""
        # TODO: P4: Do we want to cache this information somewhere?  Possibly in the company itself?
        return [city for location, city in self.game_map.getCompanyStations(company)]


    def generatePath(self, company: PublicCompany, frm: City, to: City):
        # Generates all simple paths that will lead from one city to the other, within the graph for the company.
        # Then filters out all paths that are not acceptable for one reason or another.
        pass
