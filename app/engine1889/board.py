"""Flat-layout Shikoku topology, finite tiles, station reservations and routes."""

from collections import defaultdict, deque
from itertools import permutations, product
from functools import lru_cache

from .data import BOARD_DATA, CORPORATIONS, PHASES, UPGRADES
from .errors import require, RuleError

DELTAS = ((0, 2), (-1, 1), (-1, -1), (0, -2), (1, -1), (1, 1))


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
        "terrain": [],
        "port": False,
        "rotation": rotation,
        "tokens": [],
    }
    for part in code.split(";"):
        kind, _, raw = part.partition("=")
        params = dict(p.split(":", 1) for p in raw.split(",") if ":" in p)
        if kind in ("city", "town", "offboard"):
            revenue = params.get("revenue", "0")
            if "|" in revenue:
                tiers = {
                    part.split("_")[0]: int(part.split("_")[1])
                    for part in revenue.split("|")
                }
                low, high = tiers["yellow"], tiers.get("brown", tiers["yellow"])
                diesel = tiers.get("diesel", high)
            else:
                low = high = diesel = int(revenue)
            nodes.append(
                {
                    "kind": kind,
                    "revenue": [low, high, diesel],
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
            result["terrain"] = (
                params.get("terrain", "").split("|") if params.get("terrain") else []
            )
        elif kind == "icon" and params.get("blocks_lay") == "1":
            result["port"] = True
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


def _network(board, corporation):
    """Vertices reachable by a legal simple path from any company station.

    A directed-edge visit alone is insufficient: a loop can return to a junction
    and falsely unlock another branch by repeating track. Keep the visited path
    as a bit mask. At the same directed edge, a path using a subset of another
    path's vertices dominates it, since it leaves every continuation available.
    """
    adj = graph(board)
    starts = token_vertices(board, corporation)
    bits = {v: 1 << i for i, v in enumerate(set(adj).union(starts))}
    seen = set(starts)
    connected_paths = set()
    queue = deque((v, None, bits[v]) for v in starts)
    visited = {(v, None): [bits[v]] for v in starts}
    while queue:
        vertex, previous, path = queue.popleft()
        if path not in visited[(vertex, previous)]:
            continue
        info = node_info(board, vertex)
        if vertex not in starts and (
            blocked(board, vertex, corporation) or (info and info["kind"] == "offboard")
        ):
            continue
        for nxt in adj[vertex]:
            if path & bits[nxt]:
                continue
            if previous and vertex.split(":")[1].startswith("e"):
                if previous.split(":")[0] == vertex.split(":")[0] == nxt.split(":")[0]:
                    continue
            next_path = path | bits[nxt]
            connected_paths.add(frozenset((vertex, nxt)))
            key = (nxt, vertex)
            alternatives = visited.get(key, [])
            if any(old & next_path == old for old in alternatives):
                continue
            visited[key] = [old for old in alternatives if old & next_path != next_path]
            visited[key].append(next_path)
            seen.add(nxt)
            queue.append((nxt, vertex, next_path))
    return seen, connected_paths


def reachable(board, corporation):
    return _network(board, corporation)[0]


def reserved_home(state, coord, index, corporation):
    for cid, corp in state["corporations"].items():
        if cid == corporation or corp["home_placed"]:
            continue
        if corp["home"] == coord and (index == corp.get("home_city", 0)):
            return True
    return False


def place_token(
    state, corporation, coord, index=0, home=False, free=False, teleport=False
):
    corp = state["corporations"][corporation]
    require(isinstance(coord, str) and coord in state["board"], "Unknown hex")
    tile = state["board"][coord]
    require(type(index) is int and 0 <= index < len(tile["nodes"]), "Unknown city")
    node, tokens = tile["nodes"][index], tile["tokens"][index]
    require(node["kind"] == "city", "Tokens require a large city")
    require(
        not any(corporation in ts for ts in tile["tokens"]), "Already tokened this hex"
    )
    require(len(tokens) < node["slots"], "No vacant station position")
    if not home:
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
        require(
            index == corp.get("home_city", 0),
            "Wrong home city",
        )
    used = sum(corporation in ts for t in state["board"].values() for ts in t["tokens"])
    require(used < corp["token_supply"], "No station tokens remaining")
    cost = 0 if home or free else 40
    require(corp["cash"] >= cost, "Insufficient treasury for token")
    corp["cash"] -= cost
    state["bank"] += cost
    tokens.append(corporation)
    if home:
        corp["home_placed"] = True
        corp["home_city"] = index
    return cost


def preserved_mapping(old, new):
    """Map old cities into new ones without removing track or station tokens."""
    old_nodes, new_nodes = old["nodes"], new["nodes"]
    if not old_nodes:
        mappings = [()]
    elif not new_nodes:
        return None
    elif len(old_nodes) == len(new_nodes):
        # Printed blank double cities retain their chosen station identities.
        mappings = (
            [tuple(range(len(old_nodes)))]
            if not old["paths"]
            else permutations(range(len(new_nodes)))
        )
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


def lay_tile(state, corporation, coord, tile_id, rotation, special=None, spender=None):
    require(isinstance(coord, str) and coord in state["board"], "Unknown hex")
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
    require(not old["port"], "Port tile is permanent")
    require(tile_id != "437" or special == "MF", "Port tile requires Mitsubishi Ferry")
    colors = ["white", "yellow", "green", "brown"]
    require(
        colors.index(new["color"]) == colors.index(old["color"]) + 1,
        "Tile must advance exactly one color",
    )
    require(
        [n["kind"] for n in old["nodes"]] == [n["kind"] for n in new["nodes"]],
        "Tile must preserve printed cities and towns",
    )
    require(new["label"] == old["label"], "Tile label must match")
    mapping = preserved_mapping(old, new)
    require(
        mapping is not None, "Upgrade must preserve every existing track and station"
    )
    for i, j in enumerate(mapping):
        new["tokens"][j].extend(old["tokens"][i])
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
    if not special:
        exits = [v for path in new["paths"] for v in path if v.startswith("e")]
        connected = any(
            neighbor(coord, int(v[1:])) + ":e" + str((int(v[1:]) + 3) % 6) in can_reach
            for v in exits
        )
        connected = connected or any(
            coord + ":n" + str(i) in can_reach for i in range(len(old["nodes"]))
        )
        require(connected, "Construction must extend an available railhead route")
        if old["paths"]:
            candidate = dict(state["board"])
            candidate[coord] = new
            vertices, connected_paths = _network(candidate, corporation)

            def remap(vertex):
                return (
                    "n" + str(mapping[int(vertex[1:])])
                    if vertex.startswith("n")
                    else vertex
                )

            old_paths = {frozenset(remap(v) for v in path) for path in old["paths"]}
            used_new_track = any(
                frozenset(path) not in old_paths
                and frozenset(coord + ":" + v for v in path) in connected_paths
                for path in new["paths"]
            )
            changed_city = any(
                coord + ":n" + str(j) in vertices
                and max(old["nodes"][i]["revenue"]) != max(new["nodes"][j]["revenue"])
                for i, j in enumerate(mapping)
            )
            require(
                used_new_track or changed_city,
                "Upgrade must use new track or change a reachable city value",
            )
    cost = old["cost"]
    smr = state["privates"]["SMR"]
    if (
        smr["owner"] == corporation
        and not smr["closed"]
        and old["terrain"] == ["mountain"]
    ):
        cost = 0
    account = (
        state["corporations"][corporation]
        if spender is None
        else state["players"][spender]
    )
    require(account["cash"] >= cost, "Insufficient construction funds")
    for home_corp in state["corporations"].values():
        if home_corp["home"] == coord:
            home_corp["home_city"] = mapping[home_corp.get("home_city", 0)]
    new["borders"] = list(old["borders"])
    state["board"][coord] = new
    state["tiles"][tile_id] -= 1
    if old["tile"] is not None:
        state["tiles"][old["tile"]] += 1
    account["cash"] -= cost
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
            node["revenue"][
                (
                    2
                    if state["trains"][train_id]["type"] == "D"
                    else (1 if state["phase"] in ("5", "6", "D") else 0)
                )
            ]
            for _, node in stops
        )
    return revenue


def route_candidates(state, corporation, train_id=None, limit=100):
    """Enumerate legal simple routes, useful for clients and mandatory train checks.

    ``limit`` limits returned routes, not validity of submitted route actions.
    """
    require(
        isinstance(corporation, str) and corporation in state["corporations"],
        "Unknown corporation",
    )
    require(
        limit is None or (type(limit) is int and limit >= 0),
        "Route limit must be a nonnegative integer or None",
    )
    require(
        train_id is None or (isinstance(train_id, str) and train_id in state["trains"]),
        "Unknown train",
    )
    if limit == 0:
        return []
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
                        if limit is not None and len(results) >= limit:
                            return results
                if (
                    stops >= capacity
                    or blocked(board, current, corporation)
                    or info["kind"] == "offboard"
                ):
                    continue
            for nxt in sorted(adj[current], reverse=True):
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


def best_routes(state, corporation):
    """Find the maximum combined revenue over all legal, track-disjoint routes.

    Unlike client suggestions, this search has no route-count cutoff. Enumeration
    is finite over simple paths; allocation considers all trains together rather
    than choosing each train's best route independently. Complex late-game boards
    can require substantial computation.
    """
    require(
        isinstance(corporation, str) and corporation in state["corporations"],
        "Unknown corporation",
    )
    trains = list(state["corporations"][corporation]["trains"])
    if state.get("current_corporation") == corporation and state.get("operating_turn"):
        new_trains = state["operating_turn"]["new_trains"]
        trains = [t for t in trains if t not in new_trains]
    edges = sorted(
        {
            tuple(sorted((a, b)))
            for a, neighbors in graph(state["board"]).items()
            for b in neighbors
        }
    )
    bits = {edge: 1 << i for i, edge in enumerate(edges)}
    cached, options = {}, []
    for tid in trains:
        train = state["trains"][tid]
        key = train["distance"], train["type"] == "D"
        if key not in cached:
            distinct = {}
            for route in route_candidates(state, corporation, tid, limit=None):
                forward = tuple(route["vertices"])
                vertices = min(forward, tuple(reversed(forward)))
                mask = 0
                for a, b in zip(vertices, vertices[1:]):
                    mask |= bits[tuple(sorted((a, b)))]
                revenue = validate_routes(state, corporation, [route])
                if mask not in distinct or revenue > distinct[mask][0]:
                    distinct[mask] = revenue, vertices
            cached[key] = sorted(
                (
                    (value, mask, vertices)
                    for mask, (value, vertices) in distinct.items()
                ),
                reverse=True,
            )
        options.append(cached[key])
    upper = [0] * (len(trains) + 1)
    for i in range(len(trains) - 1, -1, -1):
        upper[i] = upper[i + 1] + (options[i][0][0] if options[i] else 0)

    @lru_cache(maxsize=None)
    def allocate(index, used):
        if index == len(trains):
            return 0, ()
        best_value, selected = 0, ()
        for value, mask, vertices in options[index]:
            if mask & used or value + upper[index + 1] <= best_value:
                continue
            rest, tail = allocate(index + 1, used | mask)
            if value + rest > best_value:
                best_value = value + rest
                selected = ((trains[index], vertices),) + tail
            if best_value == upper[index]:
                break
        if best_value < upper[index + 1]:
            rest, tail = allocate(index + 1, used)
            if rest > best_value:
                best_value, selected = rest, tail
        return best_value, selected

    revenue, selected = allocate(0, 0)
    if not selected:
        for tid, choices in zip(trains, options):
            if choices:
                selected = ((tid, choices[0][2]),)
                break
    routes = [{"train": tid, "vertices": list(vertices)} for tid, vertices in selected]
    require(
        validate_routes(state, corporation, routes) == revenue,
        "Invalid optimal route allocation",
    )
    return {"routes": routes, "revenue": revenue}


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
    require(
        isinstance(corporation, str) and corporation in state["corporations"],
        "Unknown corporation",
    )
    require(
        isinstance(routes, list) and all(isinstance(route, dict) for route in routes),
        "Routes must be a list of objects",
    )
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
