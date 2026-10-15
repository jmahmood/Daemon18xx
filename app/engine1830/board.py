"""Hex topology, finite tiles, station reservations and route validation (§§18–20)."""

from collections import defaultdict, deque
from itertools import product

from .data import BOARD_DATA, CORPORATIONS, PHASES, UPGRADES
from .errors import require, RuleError

DELTAS = ((1, -1), (0, -2), (-1, -1), (-1, 1), (0, 2), (1, 1))


def neighbor(coord, edge):
    dr, dc = DELTAS[edge]
    return chr(ord(coord[0]) + dr) + str(int(coord[1:]) + dc)


def decode(code, color, rotation=0):
    nodes, paths, borders = [], [], []
    result = {
        "color": color,
        "nodes": nodes,
        "paths": paths,
        "borders": borders,
        "label": None,
        "cost": 0,
        "rotation": rotation,
        "tokens": [],
    }
    for part in code.split(";"):
        kind, _, raw = part.partition("=")
        params = dict(p.split(":", 1) for p in raw.split(",") if ":" in p)
        if kind in ("city", "town", "offboard"):
            revenue = params.get("revenue", "0")
            if "|" in revenue:
                low, high = [int(x.split("_")[1]) for x in revenue.split("|")]
            else:
                low = high = int(revenue)
            nodes.append(
                {
                    "kind": kind,
                    "revenue": [low, high],
                    "slots": int(params.get("slots", 1)),
                    "group": params.get("groups"),
                }
            )
        elif kind == "path":

            def endpoint(value):
                return (
                    "n" + value[1:]
                    if value.startswith("_")
                    else "e" + str((int(value) + rotation) % 6)
                )

            paths.append([endpoint(params["a"]), endpoint(params["b"])])
        elif kind == "border" and params.get("type") == "impassable":
            borders.append(int(params["edge"]))
        elif kind == "upgrade":
            result["cost"] = int(params.get("cost", 0))
        elif kind == "label":
            result["label"] = raw
    result["tokens"] = [[] for _ in nodes]
    return result


def initial_board():
    board = {}
    for coord, spec in BOARD_DATA["hexes"].items():
        board[coord] = decode(spec["code"], spec["color"])
        board[coord]["tile"] = None
    return board


def tile_for(tile_id, rotation):
    require(tile_id in BOARD_DATA["tiles"], "Unknown tile")
    require(type(rotation) is int and 0 <= rotation < 6, "Rotation must be 0..5")
    spec = BOARD_DATA["tiles"][tile_id]
    tile = decode(spec["code"], spec["color"], rotation)
    tile["tile"] = tile_id
    return tile


def graph(board):
    adjacency = defaultdict(set)
    for coord, tile in board.items():
        for a, b in tile["paths"]:
            a, b = coord + ":" + a, coord + ":" + b
            adjacency[a].add(b)
            adjacency[b].add(a)
        exits = {v for path in tile["paths"] for v in path if v.startswith("e")}
        for endpoint in exits:
            edge = int(endpoint[1:])
            other = neighbor(coord, edge)
            opposite = "e" + str((edge + 3) % 6)
            if other in board and any(opposite in p for p in board[other]["paths"]):
                a, b = coord + ":" + endpoint, other + ":" + opposite
                adjacency[a].add(b)
                adjacency[b].add(a)
    return adjacency


def node_info(board, vertex):
    coord, part = vertex.split(":")
    return board[coord]["nodes"][int(part[1:])] if part.startswith("n") else None


def blocked(board, vertex, corporation):
    coord, part = vertex.split(":")
    if not part.startswith("n"):
        return False
    index = int(part[1:])
    node = board[coord]["nodes"][index]
    tokens = board[coord]["tokens"][index]
    return (
        node["kind"] == "city"
        and corporation not in tokens
        and len(tokens) >= node["slots"]
    )


def token_vertices(board, corporation):
    return [
        coord + ":n" + str(i)
        for coord, tile in board.items()
        for i, tokens in enumerate(tile["tokens"])
        if corporation in tokens
    ]


def reachable(board, corporation):
    adj = graph(board)
    starts = token_vertices(board, corporation)
    seen = set(starts)
    queue = deque((v, None) for v in starts)
    visited = set(queue)
    while queue:
        vertex, previous = queue.popleft()
        info = node_info(board, vertex)
        if vertex not in starts and (
            blocked(board, vertex, corporation) or (info and info["kind"] == "offboard")
        ):
            continue
        for nxt in adj[vertex]:
            if previous and vertex.split(":")[1].startswith("e"):
                # An edge cannot be used to reverse into another track on the same tile.
                if previous.split(":")[0] == vertex.split(":")[0] == nxt.split(":")[0]:
                    continue
            state = (nxt, vertex)
            if state not in visited:
                visited.add(state)
                seen.add(nxt)
                queue.append(state)
    return seen


def reserved_home(state, coord, index, corporation):
    for cid, corp in state["corporations"].items():
        if cid == corporation or corp["home_placed"]:
            continue
        if corp["home"] == coord and (cid == "ERIE" or index == 0):
            return True
    return False


def place_token(
    state, corporation, coord, index=0, home=False, free=False, teleport=False
):
    corp = state["corporations"][corporation]
    require(coord in state["board"], "Unknown hex")
    tile = state["board"][coord]
    require(type(index) is int and 0 <= index < len(tile["nodes"]), "Unknown city")
    node, tokens = tile["nodes"][index], tile["tokens"][index]
    require(node["kind"] == "city", "Tokens require a large city")
    require(
        not any(corporation in ts for ts in tile["tokens"]), "Already tokened this hex"
    )
    require(len(tokens) < node["slots"], "No vacant station position")
    if not home:
        require(
            not (
                corporation != "ERIE"
                and coord == "E11"
                and not state["corporations"]["ERIE"]["home_placed"]
            ),
            "Erie must establish its base before other tokens here",
        )
        available = node["slots"] - len(tokens)
        require(
            not (reserved_home(state, coord, index, corporation) and available <= 1),
            "The last position is reserved for a home token",
        )
        require(
            coord + ":n" + str(index) in reachable(state["board"], corporation)
            or free
            or teleport,
            "Station must be reachable from a railhead",
        )
    else:
        require(coord == corp["home"] and not corp["home_placed"], "Invalid home token")
        require(corporation == "ERIE" or index == 0, "Wrong home city")
    used = sum(corporation in ts for t in state["board"].values() for ts in t["tokens"])
    require(used < corp["token_supply"], "No station tokens remaining")
    cost = 0 if home or free else (40 if used == 1 else 100)
    require(corp["cash"] >= cost, "Insufficient treasury for token")
    corp["cash"] -= cost
    state["bank"] += cost
    tokens.append(corporation)
    if home:
        corp["home_placed"] = True
    return cost


def preserved_mapping(old, new):
    """Map old cities into new ones without removing track or station tokens."""
    old_nodes, new_nodes = old["nodes"], new["nodes"]
    if not old_nodes:
        mappings = [()]
    elif not new_nodes:
        return None
    else:
        mappings = product(range(len(new_nodes)), repeat=len(old_nodes))
    new_paths = {frozenset(p) for p in new["paths"]}
    for mapping in mappings:
        if any(
            old_nodes[i]["kind"] != new_nodes[j]["kind"] for i, j in enumerate(mapping)
        ):
            continue

        def remap(v):
            return "n" + str(mapping[int(v[1:])]) if v.startswith("n") else v

        if not all(
            frozenset((remap(a), remap(b))) in new_paths for a, b in old["paths"]
        ):
            continue
        transferred = [[] for _ in new_nodes]
        for i, j in enumerate(mapping):
            transferred[j].extend(old["tokens"][i])
        if any(
            len(tokens) > node["slots"] or len(tokens) != len(set(tokens))
            for node, tokens in zip(new_nodes, transferred)
        ):
            continue
        return list(mapping)
    return None


def lay_tile(state, corporation, coord, tile_id, rotation, special=None):
    require(coord in state["board"], "Unknown hex")
    old = state["board"][coord]
    new = tile_for(tile_id, rotation)
    require(
        old["color"] not in ("red", "gray"), "Permanent board hex cannot be replaced"
    )
    require(
        new["color"] in PHASES[state["phase"]][1],
        "Tile color not available in this phase",
    )
    require(state["tiles"].get(tile_id, 0) > 0, "Tile supply exhausted")
    for private in state["privates"].values():
        require(
            private["closed"]
            or private["owner"] not in state["player_order"]
            or coord not in private["hexes"],
            "A player-owned private blocks this hex",
        )
    if old["tile"] is not None:
        require(tile_id in UPGRADES.get(old["tile"], []), "Not a Table 6 replacement")
    elif old["color"] == "white":
        require(new["color"] == "yellow", "Initial construction requires yellow tile")
        require(
            [n["kind"] for n in old["nodes"]] == [n["kind"] for n in new["nodes"]],
            "Tile must match printed cities/towns",
        )
    else:
        require(
            new["color"] == "green" and new["label"] == old["label"],
            "Special printed hex needs matching green tile",
        )
        if old["label"] == "OO":
            require(tile_id == "59", "Double cities require tile 59")
    require(new["label"] == old["label"], "Tile label must match the hex")
    mapping = preserved_mapping(old, new)
    require(
        mapping is not None, "Upgrade must preserve every existing track and station"
    )
    # Every exit must remain on the map and must not run into a blank gray side or lake.
    for endpoint in {v for p in new["paths"] for v in p if v.startswith("e")}:
        edge = int(endpoint[1:])
        other_coord = neighbor(coord, edge)
        require(other_coord in state["board"], "Track may not leave the board")
        other = state["board"][other_coord]
        require(
            edge not in old["borders"] and (edge + 3) % 6 not in other["borders"],
            "Track crosses impassable water",
        )
        if other["color"] == "gray":
            require(
                any("e" + str((edge + 3) % 6) in p for p in other["paths"]),
                "Track meets blank gray edge",
            )
    can_reach = reachable(state["board"], corporation)
    home_exception = (corporation == "NYC" and coord == "E19" and tile_id == "57") or (
        corporation == "ERIE" and coord == "E11" and tile_id == "59"
    )
    if not special and not home_exception:
        exits = [v for path in new["paths"] for v in path if v.startswith("e")]
        connected = any(
            neighbor(coord, int(v[1:])) + ":e" + str((int(v[1:]) + 3) % 6) in can_reach
            for v in exits
        )
        connected = connected or any(
            coord + ":n" + str(i) in can_reach for i in range(len(old["nodes"]))
        )
        require(connected, "Construction must extend an available railhead route")
    cost = old["cost"] if old["tile"] is None else 0
    corp = state["corporations"][corporation]
    require(corp["cash"] >= cost, "Insufficient treasury for construction")
    for i, j in enumerate(mapping):
        new["tokens"][j].extend(old["tokens"][i])
    new["borders"] = list(old["borders"])
    new["cost"] = 0
    state["board"][coord] = new
    state["tiles"][tile_id] -= 1
    if old["tile"] is not None:
        state["tiles"][old["tile"]] += 1
    corp["cash"] -= cost
    state["bank"] += cost
    return cost


def validate_routes(state, corporation, routes):
    require(isinstance(routes, list), "Routes must be a list")
    corp = state["corporations"][corporation]
    adj = graph(state["board"])
    used_segments, used_trains = set(), set()
    revenue = 0
    for route in routes:
        require(isinstance(route, dict), "Route must be an object")
        train_id = route.get("train")
        require(
            train_id in corp["trains"] and train_id not in used_trains,
            "Each route needs a distinct owned train",
        )
        used_trains.add(train_id)
        vertices = route.get("vertices", [])
        require(
            isinstance(vertices, list)
            and len(vertices) >= 2
            and all(isinstance(v, str) and v in adj for v in vertices),
            "Route needs existing track vertices",
        )
        require(
            len(vertices) == len(set(vertices)),
            "Route cannot revisit a station or reverse along track",
        )
        require(
            node_info(state["board"], vertices[0])
            and node_info(state["board"], vertices[-1]),
            "Routes must start and end at revenue centers",
        )
        segments = set()
        for i, (a, b) in enumerate(zip(vertices, vertices[1:])):
            require(b in adj[a], "Route track is disconnected")
            segment = tuple(sorted((a, b)))
            require(segment not in used_segments, "Trains cannot share track")
            segments.add(segment)
            if i and a.split(":")[1].startswith("e"):
                require(
                    not (
                        vertices[i - 1].split(":")[0]
                        == a.split(":")[0]
                        == b.split(":")[0]
                    ),
                    "Route cannot reverse at a junction or switch at a crossing",
                )
        stops = [
            (v, node_info(state["board"], v))
            for v in vertices
            if node_info(state["board"], v)
        ]
        require(len(stops) >= 2, "A route must serve at least two revenue centers")
        require(
            len(stops) <= state["trains"][train_id]["distance"],
            "Route exceeds train capacity",
        )
        require(
            any(v in token_vertices(state["board"], corporation) for v, _ in stops),
            "Every route needs its own railhead token",
        )
        groups = [node["group"] for _, node in stops if node["group"]]
        require(
            len(groups) == len(set(groups)),
            "Cannot visit the same offboard region twice",
        )
        for vertex, node in stops[1:-1]:
            require(node["kind"] != "offboard", "Offboard regions are termini only")
            require(
                not blocked(state["board"], vertex, corporation),
                "Route runs through a blocked city",
            )
        used_segments.update(segments)
        revenue += sum(
            node["revenue"][1 if state["phase"] in ("5", "6", "D") else 0]
            for _, node in stops
        )
    return revenue


def route_candidates(state, corporation, train_id=None, limit=100):
    """Enumerate legal simple routes, useful for clients and mandatory train checks.

    ``limit`` limits returned routes, not validity of submitted route actions.
    """
    board = state["board"]
    adj = graph(board)
    tokens = set(token_vertices(board, corporation))
    if not tokens:
        return []
    capacity = state["trains"][train_id]["distance"] if train_id else 999
    results, signatures = [], set()
    connected = reachable(board, corporation)
    starts = sorted(
        (v for v in adj if node_info(board, v) and v in connected),
        key=lambda v: v not in tokens,
    )
    for start in starts:
        stack = [
            (start, [start], int(node_info(board, start) is not None), start in tokens)
        ]
        while stack:
            current, path, stops, has_token = stack.pop()
            info = node_info(board, current)
            if info and len(path) > 1:
                if has_token and stops >= 2:
                    sig = min(tuple(path), tuple(reversed(path)))
                    groups = [
                        node_info(board, v)["group"]
                        for v in path
                        if node_info(board, v) and node_info(board, v)["group"]
                    ]
                    if sig not in signatures and len(groups) == len(set(groups)):
                        signatures.add(sig)
                        results.append({"train": train_id, "vertices": path})
                        if len(results) >= limit:
                            return results
                if (
                    stops >= capacity
                    or blocked(board, current, corporation)
                    or info["kind"] == "offboard"
                ):
                    continue
            for nxt in adj[current]:
                if nxt in path:
                    continue
                if len(path) > 1 and current.split(":")[1].startswith("e"):
                    if (
                        path[-2].split(":")[0]
                        == current.split(":")[0]
                        == nxt.split(":")[0]
                    ):
                        continue
                count = stops + int(node_info(board, nxt) is not None)
                if count <= capacity:
                    stack.append((nxt, path + [nxt], count, has_token or nxt in tokens))
    return results


def route_from_paths(state, route):
    """Expand client-friendly [hex, path-index] segments into explicit vertices."""
    paths = route.get("paths")
    require(isinstance(paths, list) and paths, "Route paths must be a nonempty list")
    segments = []
    for entry in paths:
        require(
            isinstance(entry, list) and len(entry) == 2,
            "Each route path needs hex and path index",
        )
        coord, index = entry
        require(
            isinstance(coord, str)
            and coord in state["board"]
            and type(index) is int
            and 0 <= index < len(state["board"][coord]["paths"]),
            "Unknown track segment",
        )
        segments.append(
            [coord + ":" + v for v in state["board"][coord]["paths"][index]]
        )
    adj = graph(state["board"])
    for first in (segments[0], list(reversed(segments[0]))):
        vertices = list(first)
        for segment in segments[1:]:
            possibilities = [segment, list(reversed(segment))]
            matched = False
            for a, z in possibilities:
                if a == vertices[-1]:
                    vertices.append(z)
                    matched = True
                    break
                if (
                    a in adj[vertices[-1]]
                    and a.split(":")[0] != vertices[-1].split(":")[0]
                ):
                    vertices.extend((a, z))
                    matched = True
                    break
            if not matched:
                break
        else:
            if node_info(state["board"], vertices[0]) and node_info(
                state["board"], vertices[-1]
            ):
                return {"train": route.get("train"), "vertices": vertices}
    raise RuleError("Route segments do not form an oriented city-to-city path")


def route_revenue(state, corporation, routes):
    expanded = [
        route_from_paths(state, route) if "paths" in route else route
        for route in routes
    ]
    revenue = validate_routes(state, corporation, expanded)
    details = [
        {"stops": [v for v in route["vertices"] if node_info(state["board"], v)]}
        for route in expanded
    ]
    return revenue, details
