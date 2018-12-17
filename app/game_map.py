import logging
import string
from typing import List, Dict, Tuple, Set, Union
import matplotlib.pyplot as plt

import networkx as nx

from app.base import City, Track, PublicCompany, PrivateCompany, TrackType, Town, Position, Color

EMPTY_SQUARES = (
        ["a{}".format(x) for x in list(range(1, 15)) + list(range(21, 25))] +
        ["b{}".format(x) for x in range(1, 8)] +
        ["c{}".format(x) for x in range(1, 6)] +
        ["k{}".format(x) for x in range(1, 11)] +
        ["j{}".format(x) for x in range(16, 25)] +
        ["k{}".format(x) for x in range(17, 25)] +
        ["e1", "g1", "g21", "g23", "g25", "h20", "h22", "h24", "h26", "i21", "i23", "i25"]
)

GRAY_TILES = [
    # location, number of tokens, value, *in out pairs
    # ("d2", 1, 20, 1, 0, (4, "Lansing"), (5, "Lansing")),  # Lansing
    # ("a17", 0, 0, 0, 0, (5, 6)),
    # ("a19", 1, 40, 1, 0, (5, "Montreal"), (6, "Montreal")),
    # ("c15", 0, 10, 0, 1, (1, "Kingston"), (3, "Kingston")),
    # ("d14", 1, 20, 1, 0, (1, "Rochester"), (4, "Rochester"), (6, "Rochester")),
    # ("d24", 0, 0, 0, 0, (1, 6)),
    # ("e9", 0, 0, 0, 0, (2, 3)),
    # ("f24", 0, 10, 0, 1, (1, "Fall River"), (2, "Fall River")),
    # ("f6", 1, 30, 1, 0, (5, "Cleveland"), (6, "Cleveland")),
    # ("h12", 1, 10, 1, 0, (1, "Altoona"), (4, "Altoona"), (1, 4)),
    # ("i19", 0, 10, 0, 1, (1, "Atlantic City"), (2, "Atlantic City")),
    # ("k15", 1, 20, 1, 0, (2, "Richmond"))
    ("d2", 1, 20, 1, 0, (Position.RIGHT, Position.CITY_1), (Position.BOTTOM_RIGHT, Position.CITY_1)),  # Lansing
    ("a17", 0, 0, 0, 0, (Position.BOTTOM_RIGHT, Position.BOTTOM_LEFT)),
    ("a19", 1, 40, 1, 0, (Position.BOTTOM_RIGHT, Position.CITY_1), (Position.BOTTOM_LEFT, Position.CITY_1)),
    ("c15", 0, 10, 0, 1, (Position.LEFT, Position.CITY_1), (Position.TOP_RIGHT, Position.CITY_1)),
    ("d14", 1, 20, 1, 0, (Position.LEFT, Position.CITY_1), (Position.RIGHT, Position.CITY_1),
     (Position.BOTTOM_LEFT, Position.CITY_1)),
    ("d24", 0, 0, 0, 0, (Position.LEFT, Position.BOTTOM_LEFT)),
    ("e9", 0, 0, 0, 0, (2, Position.TOP_RIGHT)),
    ("f24", 0, 10, 0, 1, (Position.LEFT, Position.CITY_1), (Position.TOP_RIGHT, Position.CITY_1)),
    ("f6", 1, 30, 1, 0, (Position.BOTTOM_RIGHT, Position.CITY_1), (Position.BOTTOM_LEFT, Position.CITY_1)),
    ("h12", 1, 10, 1, 0, (Position.LEFT, Position.CITY_1), (Position.RIGHT, Position.CITY_1),
     (Position.LEFT, Position.RIGHT)),
    ("i19", 0, 10, 0, 1, (Position.LEFT, Position.CITY_1), (Position.TOP_RIGHT, Position.CITY_1)),
    ("k15", 1, 20, 1, 0, (Position.TOP_RIGHT, Position.CITY_1))

]

STARTER_YELLOW_TILES = [

]

WATER_TILES = [
    "c19", "b18", "j14", "d6", "f4"
]

MOUNTAIN_TILES = [
    "c21", "c17", "f16", "g15", "g13", "i11", "j10", "j12", "d22", "e21"
]

RED_TILES = [
    "a9", "a11", "f2", "a24", "i1", "j2", "k13"
]

RED_TILE_LOCATIONS = [(["a9", "a11"], "Canadian West", [30, 50]),
                      (["f2"], "Chicago", [40, 70]),
                      (["b24"], "Maritime Provinces", [20, 30]),
                      (["i1", "j2"], "Gulf of Mexico", [30, 60]),
                      (["k13"], "Deep South", [30, 40])]

PREEXISTING_EDGES = ["a17-5:a17-6", "a19-5:Montreal", "a19-6:Montreal", "c15-1:Kingston", "c15-3:Kingston",
                     "d2-4:Lansing", "d2-5:Lansing", "d14-1:Rochester", "d14-4:Rochester", "d14-6:Rochester",
                     "d24-6:d24-1", "e9-2:e9-3", "e23-3:Boston", "e23-5:Boston", "f24-1:Fall River", "f24-2:Fall River",
                     "f6-6:Cleveland", "f6-5:Cleveland", "g19-3:New York", "g19-6:Newark", "h12-4:Altoona",
                     "h12-1:Altoona", "h12-1:h12-4", "i15-6:Baltimore", "i15-4:Baltimore",
                     "i19-1:Atlantic City", "i19-2:Atlantic City", "k15-2:Richmond"]

BLOCKED_EDGES = [
    "c11-5:d12-2",
    "c13-6:d12-3",
    "b16-5:c17-2",
    "e7-5:f8-2",
]

RED_TILE_EDGES = [
    "e3-6:Chicago",
    "f4-1:Chicago",
    "g3-2:Chicago",
    "i3-1:Gulf of Mexico",
    "i3-6:Gulf of Mexico",
    "j4-1:Gulf of Mexico",
    "b10-2:Canadian West",
    "b10-3:Canadian West",
    "b12-2:Canadian West",
    "b22-4:Maritime Provinces",
    "c23-3:Maritime Provinces",
    "j12-5:Deep South",
    "j14-6:Deep South"
]


class MapHexConfig:
    """We use this to keep information about individual map hexes, and about cities within the hex."""

    def __str__(self):
        return self.location

    def __hash__(self) -> int:
        return hash(self.location)

    def __eq__(self, o: "MapHexConfig") -> bool:
        return self.location == o.location

    def get_tile_edges(self) -> List[List[Tuple[str, str]]]:
        column = self.location[0]
        row = int(self.location[1:])
        citytown1 = self.cities[0] if len(self.cities) > 0 else None
        citytown2 = self.cities[2] if len(self.cities) > 1 else None

        if self.towns is not None and len(self.towns) > 0:
            citytown1 = self.towns[0] if len(self.towns) > 0 else None
            citytown2 = self.towns[1] if len(self.towns) > 1 else None

        translation = {
            Position.LEFT: "{}{}-{}".format(column, row, 1),
            Position.TOP_LEFT: "{}{}-{}".format(column, row, 2),
            Position.TOP_RIGHT: "{}{}-{}".format(column, row, 3),
            Position.RIGHT: "{}{}-{}".format(column, row, 4),
            Position.BOTTOM_RIGHT: "{}{}-{}".format(column, row, 5),
            Position.BOTTOM_LEFT: "{}{}-{}".format(column, row, 6),
            Position.CITY_1: citytown1.name if citytown1 else None,
            Position.CITY_2: citytown2.name if citytown2 else None
        }

        tile_edges = self.track.connections()
        ret = []
        for possible_connections in tile_edges:
            ret2 = []
            for connection in possible_connections:

                if translation[connection[0]] is None or translation[connection[1]] is None:
                    raise AttributeError()

                ret2.append(
                    (translation[connection[0]], translation[connection[1]])
                )
            ret.append(ret2)
        return ret

    def get_edges(self):
        """Returns all possible edges around the tile."""
        column = self.location[0]
        row = int(self.location[1:])

        edges = []

        if column > 'a':
            top_column = chr(ord(column) - 1)
            if row > 1:
                top_left_row = row - 1
                edges.append([(column, row, Position.TOP_LEFT), (top_column, top_left_row, Position.BOTTOM_RIGHT)])

            if row < 25:
                top_right_row = row + 1
                edges.append([(column, row, Position.TOP_RIGHT), (top_column, top_right_row, Position.BOTTOM_LEFT)])

        if row > 2:
            edges.append([(column, row, Position.LEFT), (column, row - 2, Position.RIGHT)])

        if row < 23:
            edges.append([(column, row, Position.RIGHT), (column, row + 2, Position.LEFT)])

        if column < 'k':
            bottom_column = chr(ord(column) + 1)
            if row > 1:
                bottom_left_row = row - 1
                edges.append(
                    [(column, row, Position.BOTTOM_LEFT), (bottom_column, bottom_left_row, Position.TOP_RIGHT)])

            if row < 25:
                bottom_right_row = row + 1
                edges.append(
                    [(column, row, Position.BOTTOM_RIGHT), (bottom_column, bottom_right_row, Position.TOP_LEFT)])

        return edges

    @staticmethod
    def load() -> Dict[str, "MapHexConfig"]:
        # TODO: P4: This is embarrassing.
        hex_configs = {}

        for i in range(0, 11):
            is_odd = i % 2 == 1
            letter = string.ascii_lowercase[i]
            start = 2 if is_odd else 1
            for x in range(start, 25, 2):
                label = "{}{}".format(letter, x)
                if label in EMPTY_SQUARES:
                    # Skip all points on the map that don't let you place anything.
                    continue
                hex_configs[label] = {
                    "location": label,
                    "red_tile": None,
                    "track": None,
                    "cities": [],
                    "towns": [],
                    "tokens": {},
                    "cost": None,
                    "requires_private_company": None,
                    "edges": None
                }

        # Now how about cities?

        all_cities = City.load()

        for x in all_cities:
            if hex_configs.get(x.map_hex_name):
                hex_configs[x.map_hex_name.lower()]["cities"].append(x)
            else:
                hex_configs[x.map_hex_name.lower()] = {
                    "location": x.map_hex_name.lower(),
                    "red_tile": None,
                    "track": None,
                    "cities": [x],
                    "towns": [],
                    "tokens": {},
                    "cost": x.value,
                    "requires_private_company": x.private_company_hq,
                    "edges": None
                }

        all_towns = Town.load()

        for x in all_towns:
            if hex_configs.get(x.map_hex_name.lower()):
                hex_configs[x.map_hex_name.lower()]["towns"].append(x)
                hex_configs[x.map_hex_name.lower()]["requires_private_company"] = x.private_company_hq
            else:
                hex_configs[x.map_hex_name.lower()] = {
                    "location": x.map_hex_name.lower(),
                    "red_tile": None,
                    "track": None,
                    "cities": [],
                    "towns": [x],
                    "tokens": {},
                    "cost": x.value,
                    "requires_private_company": x.private_company_hq,
                    "edges": None
                }

        for locations, name, values in RED_TILE_LOCATIONS:
            for x in locations:
                hex_configs[x] = {
                    "location": x,
                    "track": None,
                    "red_tile": name,
                    "cities": [],
                    "towns": [],
                    "tokens": {},
                    "cost": values,
                    "requires_private_company": None,
                    "edges": None
                }

        for x in MOUNTAIN_TILES:
            hex_configs[x]["cost"] = 120

        for x in WATER_TILES:
            hex_configs[x]["cost"] = 80

        all_private_companies = PrivateCompany.load()
        for h in hex_configs:
            hex_configs[h] = MapHexConfig.initialize(all_private_companies, **hex_configs[h])

        return hex_configs

    @classmethod
    def initialize(cls, all_private_companies: List[PrivateCompany], **kwargs):
        ret = cls()
        for k, v in kwargs.items():
            setattr(ret, k, v)
        if ret.requires_private_company is not None:
            ret.requires_private_company = next(pc for pc in all_private_companies
                                                if pc.short_name == ret.requires_private_company)
        return ret

    def __init__(self):
        self.location: str = None  # A9 or whatever
        self.track: Track = None  # The current track laid down, or null if nothing.
        self.red_tile: str = None  # If this is a red tile, the name should be in here.
        self.cities: List[City] = None  # Cities in that hex.
        self.towns: List[Town] = None  # Towns in that hex.
        self.tokens: Dict[City, Set[PublicCompany]] = {}
        self.cost: int = None  # Cost to upgrade track here.

        self.requires_private_company: PrivateCompany = None

        # TODO: P4: Do we want to make self.edges into a set instead of list so we can use subset?
        self.edges: List[Tuple[str, str]] = None  # All edges created by the current tile that was laid down.

    def getCities(self):
        return self.cities

    def getTowns(self):
        return self.towns

    def hasStation(self, city: City, pc: PublicCompany):
        return pc in self.getTokens(city)

    def getTokens(self, city: City):
        if city in self.cities:
            return self.tokens.get(city, [])

        # TODO: P4: How are we going to deal with these sorts of attempts at cheating / programming errors / etc?
        #   We don't want the app to crash, but I don't want to handle every Attribute error possible.
        raise AttributeError("That is not a city in this hex.")

    def maxTokens(self, city: City):
        if city in self.cities:
            if self.track:
                return self.track.type.city_1_stations
            return 1
        # TODO: P4: How are we going to deal with these sorts of attempts at cheating / programming errors / etc?
        #   We don't want the app to crash, but I don't want to handle every Attribute error possible.
        raise AttributeError("That is not a city in this hex.")

    def getCompanyTokens(self, company: PublicCompany):
        return [city for city in self.tokens.keys() if company in self.tokens[city]]

    def isFull(self, city: City):
        if city in self.cities:
            return self.maxTokens(city) <= len(self.getTokens(city))
        raise AttributeError("That is not a city in this hex.")

    def recalculateEdges(self):
        self.edges = self.get_tile_edges()



class GameMap:
    """Container for all map locations"""

    def __init__(self):
        self.mapHexConfig: Dict[str, MapHexConfig] = {}
        self.graph = nx.Graph()
        self.companyGraph: Dict[PublicCompany, nx.Graph] = {}

    @staticmethod
    def initialize(map_hex_config: Dict[str, MapHexConfig] = None, graph: nx.Graph = None, companyGraph=None):
        """Loads all static map data."""
        if not map_hex_config:
            map_hex_config = MapHexConfig.load()

        ret = GameMap()
        ret.mapHexConfig = map_hex_config

        if not graph:
            ret.generateGraph()
        else:
            ret.graph = graph

        if not companyGraph:
            ret.companyGraph = {}
        else:
            ret.companyGraph = companyGraph

        # TODO: P4: Move to own function.
        gray_tracks = Track.GenerateTracks([TrackType(
            type_id="gray-{}".format(i),
            connections=[list(gray_tile[5:])],
            copies=1,
            color=Color.GREY,
            cities=gray_tile[3],
            towns=gray_tile[4],
            upgrades=None,
            city_1_stations=gray_tile[1],
            city_2_stations=0,
            value=gray_tile[2],
            default_location=gray_tile[0])
            for i, gray_tile in enumerate(GRAY_TILES)])

        for t in gray_tracks:
            ret.placeTrack(t.type.default_location, t.rotate(0))

        return ret

    def placeTrack(self, location: str, track: Track) -> Track:
        config = self.mapHexConfig.get(location)
        pre_existing_track = config.track
        config.track = track
        config.recalculateEdges()
        self.updateGraph(config, self.graph)
        return pre_existing_track

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
            self.regenerateCompanyGraph(pc)
        return self.companyGraph.get(pc)

    def generateGraph(self):
        """Uses MapHexConfig to generate the nx.Graph"""
        # TODO: P2: Use the tile in MapHexConfig to configure the current values.
        self.graph = nx.Graph()

        for hex, val in self.mapHexConfig.items():
            if val.red_tile:
                continue

            for y in range(1, 7):  # Create each node for each tile
                label = "{}-{}".format(hex, y)
                self.graph.add_node(label, name=label, config=val, is_city=False, is_town=False)

            edges = val.get_edges()
            for point1, point2 in edges:
                edges = (
                    """{}{}-{}""".format(*point1),
                    """{}{}-{}""".format(*point2),
                )
                self.graph.add_edge(
                    *edges
                )

            if val.getCities() and len(val.getCities()) > 0:
                for city in val.getCities():
                    self.graph.add_node(city.name,
                                        name=city.name,
                                        config=val,
                                        is_city=True,
                                        is_town=False,
                                        weight=city.value,
                                        )

            if val.getTowns() and len(val.getTowns()) > 0:
                for town in val.getTowns():
                    self.graph.add_node(town.name,
                                        name=town.name,
                                        config=val,
                                        is_city=False,
                                        is_town=True,
                                        weight=town.value,
                                        )
            if val.red_tile:
                self.graph.add_node(val.red_tile,
                                    name=val.red_tile,
                                    config=val,
                                    is_city=False,
                                    is_town=False,
                                    weight=val.cost
                                    )

        for edge in PREEXISTING_EDGES + RED_TILE_EDGES:
            node1, node2 = edge.split(":")
            self.graph.add_edge(node1, node2)

        for edge in BLOCKED_EDGES:
            node1, node2 = edge.split(":")
            self.graph.remove_edge(node1, node2)

    def updateGraph(self, hex_config: MapHexConfig, g: nx.Graph = None):
        if g is None:
            g = self.graph

        for possible_connection in hex_config.edges:
            for vertex1, vertex2 in possible_connection:
                try:
                    g.add_edge(vertex1, vertex2)
                except AttributeError:
                    raise AttributeError("LOL")


    def regenerateCompanyGraph(self, pc: PublicCompany) -> nx.Graph:
        self.companyGraph[pc] = self.generateCompanyGraph(pc)
        return self.companyGraph[pc]

    def generateCompanyGraph(self, pc: PublicCompany) -> nx.Graph:
        """Takes the overall connectivity graph, and then generates one for the company,
        using its stations as root nodes."""

        company_graph = nx.create_empty_copy(self.graph)  # Creates a copy with all nodes, but no edges.

        nbunch = set([next(n for n in company_graph if n == city.name)
                      for location, city in self.getCompanyTokens(pc)])
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


    def get(self, location: str) -> MapHexConfig:
        return self.mapHexConfig.get(location)

    def getCompanyTokens(self, company: PublicCompany) -> [Tuple[str, str]]:
        """Returns location, city tuple for stations that belong to the company"""
        # TODO: P4: Cache this information instead of building it from scratch?
        ret = []
        for location in self.mapHexConfig.keys():
            stations = self.mapHexConfig[location].getCompanyTokens(company)
            if len(stations) > 0:
                for city in stations:
                    ret.append((location, city))

        return ret

    def locations(self):
        return self.mapHexConfig.keys()

    def _showGraph(self):
        nx.draw_networkx(self.graph,
                         node_size=15,
                         pos=nx.spring_layout(self.graph,
                                              iterations=2500))

        plt.show()


class GameTracks:
    """Contains logic that confirms whether or not a track is available, and allows you to place it / etc.."""

    # TODO: P2: Add a class function to check for a track being valid and available.  Add to GameBoard as well.
    def __init__(self):
        self.ALL_TRACK_TYPES: List[TrackType] = []
        self.ALL_TRACK: List[Track] = []
        self.available_track: List[Track] = []

    @staticmethod
    def initialize():
        """Loads all static data related to the game from data files"""
        ret = GameTracks()
        ret.ALL_TRACK_TYPES = TrackType.load()
        ret.ALL_TRACK = Track.GenerateTracks(ret.ALL_TRACK_TYPES)
        ret.available_track = set([t for t in ret.ALL_TRACK])
        return ret


class GameBoard(object):
    """Top-level class / public interface to the map and other parts of the underlying game board."""

    def __init__(self):
        self.game_map: GameMap = None
        self.game_tracks: GameTracks = None

    @staticmethod
    def initialize():
        ret = GameBoard()
        ret.game_map = GameMap.initialize()
        ret.game_tracks = GameTracks.initialize()
        return ret

    def shortestPath(self, g: nx.Graph = None, start: str = None, end: str = None):
        if g is None:
            g = self.game_map.graph
        start_node = next(n for n in g if n == start)
        end_node = next(n for n in g if n == end)
        return nx.all_shortest_paths(g, start_node, end_node)

    def doesPathExist(self, g: nx.Graph = None, start: str = None, end: str = None):
        if g is None:
            g = self.game_map.graph
        # start and end need to be converted to nodes.
        start_node = next(n for n in g if n == start)
        end_node = next(n for n in g if n == end)

        return nx.has_path(g, start_node, end_node)

    def doesRouteExist(self, pc: PublicCompany, start: str, end: str):
        company_graph = self.game_map.getCompanyGraph(pc)
        return self.doesPathExist(company_graph, start, end)

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

    def hasTrack(self, location: str):
        config = self.game_map.mapHexConfig[location]
        return config.track is not None

    def canUpgradeTrack(self, location: str, track: Track) -> bool:
        """Simplifies process of determining if one track can be replaced with another"""
        existing_track = self.game_map.get(location).track
        if existing_track:
            return existing_track.type.can_upgrade_to(track.type)
        return False

    def getTrackType(self, track_type_id: str):
        for track_type in self.game_tracks.ALL_TRACK_TYPES:
            if track_type.type_id == track_type_id:
                return track_type
        return None

    def getAvailableTrack(self, track_type_id: str):
        for track in self.game_tracks.available_track:
            if track.type.type_id == track_type_id:
                return track
        return Track("Unavailable", self.getTrackType(track_type_id), 0)

    def placeTrack(self, location: str, track: Track) -> Track:
        """We return the old track so it can be returned to the list of available track types."""
        # TODO: P4: How are we dealing with rotation?  By cloning w/ a rotation, we are leaving some crap data in the
        #   game_tile object
        return self.game_map.placeTrack(location, track)

    def setToken(self, public_company: PublicCompany, city: City, location: str):
        config = self.game_map.mapHexConfig[location]
        all_tokens = config.tokens.get(city, set())
        all_tokens.add(public_company)
        config.tokens[city] = all_tokens

    def calculateRoute(self, route) -> int:
        # TODO: P2: Calculate the amount of cash someone would make from a route?
        # TODO: P4: Rename
        raise NotImplementedError()

    def updateRoutes(self):
        raise NotImplementedError()

    def getCost(self, location: str):
        try:
            return 0 if self.game_map.get(location).cost is None else self.game_map.get(location).cost
        except KeyError:
            return 0
            # raise KeyError("Location {} does not exist in game map".format(location))
        except AttributeError:
            # Location doesn't exist on the board.
            return 0
            #raise KeyError("Location {} does not exist in game map".format(location))

    def validatePlaceTrack(self, track: Track, location: str) -> bool:
        raise NotImplementedError

    def getTokens(self, city: City) -> Set[PublicCompany]:
        return self.game_map.mapHexConfig[city.map_hex_name].getTokens(city)

    def maxTokens(self, city: City) -> int:
        return self.game_map.mapHexConfig[city.map_hex_name].maxTokens(city)

    def findCompanyTokenCities(self, company: PublicCompany) -> List[City]:
        """Returns a list of names of cities with a station of the company"""
        # TODO: P4: Do we want to cache this information somewhere?  Possibly in the company itself?
        # TODO: P4: Do we want to call this findCompanyRailheads or is that too obtuse? (Title from the rules)
        return [city for location, city in self.game_map.getCompanyTokens(company)]
