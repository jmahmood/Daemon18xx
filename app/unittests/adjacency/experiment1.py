from pprint import pprint

import networkx as nx
import json

from app.base import TrackType

"""Adjacency of tiles """
import string



class TilePlacement():
    """This is used to handle logic around tile placement"""
    def addTile(self, player, track):
        pass


class Routes():
    """Handles Route generation"""
    pass



def xy(letter, coordinate, edge):
    if ord(letter) >= ord("a") and ord(letter) <= ord("x"):
        return "{}{}-{}".format(letter, coordinate, edge)
    return None

def add_red_tiles(g: nx.Graph):
    red_zones = [
        (["A9", "A11"], "Canadian West"),
        (["F2"], "Chicago"),
        (["A24", "B24"], "Maritime Provinces"),
        (["I2", "J3"], "Gulf of Mexico"),
        (["K13"], "Deep South")
    ]


def add_red_tile_edges(g: nx.Graph):
    red_zones_edges = [
        "e3-5:Chicago",
        "f4-6:Chicago",
        "g3-1:Chicago",
        "i3-6:Gulf of Mexico",
        "i3-5:Gulf of Mexico",
        "j4-6:Gulf of Mexico",
        "b10-1:Canadian West",
        "b10-2:Canadian West",
        "b12-1:Canadian West",
        "b22-3:Maritime Provinces",
        "c23-2:Maritime Provinces",
        "j12-4:Deep South",
        "j14-5:Deep South"
    ]


def remove_blocked_edges(g: nx.Graph):
    """These are tiles that cannot connect to each other"""
    blocked_edges = [
        "c11-4:d12-1",
        "c13-5:d12-2",
        "b16-4:c17-1",
        "e7-4:f8-1",
    ]
    for edge in blocked_edges:
        for node1, node2 in edge.split(":"):
            g.remove_edge(node1, node2)


def city_nodes(g: nx.Graph):
    city_nodes = [
        ("a19", {"name": "Montreal", "company": "CP", "value": 40}),
        ("b10", {"name": "Barrie"}),
        ("b16", {"name": "Ottawa"}),
        ("d2",  {"name": "Lansing", }),
        ("d14", {"name": "Rochester", }),
        ("e19", {"name": "Albany", "company": "NYC"}),
        ("e23", {"name": "Boston", "special": "B", "company": "B&M", "value": 30}),
        ("f4",  {"name": "Toledo", }),
        ("f6",  {"name": "Cleveland", "company": "C&O", "value": 30}),
        ("f16", {"name": "Scranton", "private_company": "D&H", "cost": 120}),
        ("f22", {"name": "Providence", "cost": 80}),
        ("h4",  {"name": "Columbus", }),
        ("h10", {"name": "Pittsburgh", }),
        ("h12", {"name": "Altoona", "company": "PRR", "value": 10}),
        ("h16", {"name": "Lancaster"}),
        ("i15", {"name": "Baltimore", "company": "B&O"}),
        ("j14", {"name": "Washington", "cost": 80}),
        ("k15", {"name": "Richmond"}),
    ]

    double_city_nodes = [
        ("d10", {"cost": 80, "names": ["Toronto", "Hamilton"]}),
        ("e5",  {"cost": 80, "names": ["Detroit", "Windsor"]}),
        ("e11", {"special": "ER", "names": ["Buffalo", "Dunkirk"]}),
        ("g19", {"company": "NYNH", "special": "NY", "cost": 80, "names": ["New York", "Newark"]}),
        ("h18", {"private_company": "C&A", "names": ["Trenton", "Philidelphia"]})
    ]

    town_nodes = [
        ("b20", {"name": "Burlington", "private_company": "C&StL"}),
        ("d4", {"name": "Flint"}),
        ("e7", {"name": "London"}),
        ("f10", {"name": "Erie"}),
        ("c15", {"name": "Kingston"})
    ]

    double_town_nodes = [
        ("f20", {"names": ["Hartford", "New Haven"]}),
        ("g7", {"names": ["Akron", "Canton"]}),
        ("g17", {"names": ["Reading", "Allentown"]})
    ]

    for n, details in city_nodes:
        g.add_node(
            details["name"], location=n, is_city=True, **details
        )

    for n, details in town_nodes:
        g.add_node(
            details["name"], location=n, is_town=True, **details
        )

    for n, details in double_city_nodes:
        for name in details["names"]:
            g.add_node(
                n, name=name, location=n, is_city=True, **details
            )

    for n, details in double_town_nodes:
        for name in details["names"]:
            g.add_node(
                n, name=name, location=n, is_town=True, **details
            )


def preexisting_edges(g: nx.Graph):
    """You must run city_nodes before running this. """
    connections = ["a17-4:a17-5", "a19-3:Montreal", "a19-4:Montreal", "c15-6:Kingston", "c15-2:Kingston",
                   "d2-3:Lansing", "d2-4:Lansing", "d13-3:Rochester", "d13-5:Rochester", "d13-6:Rochester",
                   "d24-5:d24-6", "e9-1:e9-2", "e23-2:Boston", "e23-4:Boston", "f24-1:Fall River", "f24-6:Fall River",
                   "f6-4:Cleveland", "f6-5:Cleveland", "g19-2:New York", "g19-5:Newark", "h11-3:Altoona",
                   "h11-6:Altoona", "h11-3:h11-6", "h18-2:Trenton", "i15-3:Baltimore", "i15-5:Baltimore",
                   "i19-1:Atlantic City", "i19-6:Atlantic City", "k15-1:Richmond"]

    for c in connections:
        node1, node2 = c.split(":")
        G.add_edge(node1, node2)

def tile_nodes_and_natural_edges(g: nx.Graph):
    nodes = []
    edges = {}

    for i in range(0, 11):
        letter = string.ascii_lowercase[i]
        start = 2 if i % 2 == 1 else 1
        for x in range(start, 25, 2):
            for y in range(1,7): # Create each node for each tile
                label = xy(letter, str(x), str(y))
                # nodes.append(label)
                g.add_node(label)

            # Create each relationship for each tile
            UP_TILE = string.ascii_lowercase[i-2]
            UP_DIAGONAL_TILE = string.ascii_lowercase[i-1]
            BOTTOM_DIAGONAL_TILE = string.ascii_lowercase[i+1]
            BOTTOM_TILE = string.ascii_lowercase[i+2]

            # Create all natural edges between tiles.

            if i-2 > 0:
                G.add_edge(xy(letter, x, 1), xy(UP_TILE, x, 4))

            if x + 1 < 7:
                if i - 1 >= 0:
                    G.add_edge(xy(letter, x, 2), xy(UP_DIAGONAL_TILE, x + 1, 5))
                G.add_edge(xy(letter, x, 3), xy(BOTTOM_DIAGONAL_TILE, x + 1, 6))

            G.add_edge(xy(letter, x, 4), xy(BOTTOM_TILE, x, 1))

            if x - 1 > 0:
                G.add_edge(xy(letter, x, 5), xy(BOTTOM_DIAGONAL_TILE, x - 1, 2))
                if i - 1 >= 0:
                    G.add_edge(xy(letter, x, 6), xy(UP_DIAGONAL_TILE, x - 1, 3))
"""
G = nx.Graph()
tile_nodes_and_natural_edges(G)
city_nodes(G)
preexisting_edges(G)

pprint(repr(G.nodes))
pprint(G.has_node("Trenton"))
pprint(G.has_node("Newark"))

print(repr(list(nx.all_simple_paths(G, source="Trenton", target="Newark"))))
"""


print(repr([str(t) for t in TrackType.Load()]))

