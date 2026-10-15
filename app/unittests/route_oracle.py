"""Small exhaustive 1889 oracle, independent of engine traversal/allocation.

Only test code: builds geometry directly from the board, walks simple paths,
then exhaustively combines frozensets of edges. No engine route, reachability,
validation, bitmask, memoization or branch-and-bound functions are called.
"""

from itertools import product


def best_revenue(state, corporation):
    board = state["board"]
    graph, nodes, own = {}, {}, set()

    def edge(a, b):
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)

    for coord, tile in board.items():
        for i, node in enumerate(tile["nodes"]):
            v = coord + ":n%d" % i
            nodes[v] = node
            if corporation in tile["tokens"][i]:
                own.add(v)
        for a, b in tile["paths"]:
            edge(coord + ":" + a, coord + ":" + b)
    delta = ((0, 2), (-1, 1), (-1, -1), (0, -2), (1, -1), (1, 1))
    for coord, tile in board.items():
        for endpoint in {
            v for path in tile["paths"] for v in path if v.startswith("e")
        }:
            d = int(endpoint[1:])
            dr, dc = delta[d]
            neighbor = chr(ord(coord[0]) + dr) + str(int(coord[1:]) + dc)
            opposite = "e%d" % ((d + 3) % 6)
            if neighbor in board and any(
                opposite in path for path in board[neighbor]["paths"]
            ):
                edge(coord + ":" + endpoint, neighbor + ":" + opposite)
    blocked = set()
    for v, node in nodes.items():
        coord, index = v.split(":n")
        tokens = board[coord]["tokens"][int(index)]
        if (
            node["kind"] == "city"
            and len(tokens) >= node["slots"]
            and corporation not in tokens
        ):
            blocked.add(v)
    trains = list(state["corporations"][corporation]["trains"])
    if state.get("current_corporation") == corporation:
        new = (state.get("operating_turn") or {}).get("new_trains", [])
        trains = [t for t in trains if t not in new]
    choices = []
    for tid in trains:
        train = state["trains"][tid]
        distance = train["distance"]
        tier = 2 if train["type"] == "D" else int(state["phase"] in ("5", "6", "D"))
        routes = {frozenset(): 0}

        def visit(path, stops, edges):
            here = path[-1]
            if len(stops) > distance:
                return
            groups = [nodes[v]["group"] for v in stops if nodes[v]["group"]]
            if len(set(groups)) != len(groups):
                return
            if here in nodes and len(stops) >= 2 and own.intersection(stops):
                routes[frozenset(edges)] = sum(nodes[v]["revenue"][tier] for v in stops)
            if len(path) > 1 and (
                here in blocked or (here in nodes and nodes[here]["kind"] == "offboard")
            ):
                return
            for nxt in graph.get(here, ()):
                if nxt in path:
                    continue
                if len(path) > 1 and here.split(":")[1].startswith("e"):
                    if (
                        path[-2].split(":")[0]
                        == here.split(":")[0]
                        == nxt.split(":")[0]
                    ):
                        continue
                visit(
                    path + [nxt],
                    stops + ([nxt] if nxt in nodes else []),
                    edges + [frozenset((here, nxt))],
                )

        for start in nodes:
            if start in graph:
                visit([start], [start], [])
        choices.append(list(routes.items()))
    best = 0
    for allocation in product(*choices):
        occupied = set()
        revenue = 0
        for edges, value in allocation:
            if occupied.intersection(edges):
                break
            occupied.update(edges)
            revenue += value
        else:
            best = max(best, revenue)
    return best
