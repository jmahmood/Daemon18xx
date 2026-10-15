"""Shared structural invariants for trusted, JSON-compatible engine snapshots.

Variant rules and accounting remain in their engines. This module rejects
malformed saves before dictionary lookups can escape as incidental exceptions.
"""

from functools import wraps


def state_errors(error_type):
    def decorate(function):
        @wraps(function)
        def checked(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except error_type:
                raise
            except (
                KeyError,
                TypeError,
                IndexError,
                AttributeError,
                ValueError,
            ) as error:
                raise error_type("Malformed saved game state") from error

        return checked

    return decorate


def validate_snapshot(state, require, corporations, board_data, phases, market):
    def integer(value, minimum=0):
        return type(value) is int and value >= minimum

    require(isinstance(state, dict), "State must be an object")
    players, corps, board = state["players"], state["corporations"], state["board"]
    order = state["player_order"]
    require(
        isinstance(order, list)
        and 2 <= len(order) <= 6
        and all(isinstance(p, str) for p in order)
        and len(set(order)) == len(order)
        and set(order) == set(players),
        "Invalid player order",
    )
    require(set(corps) == set(corporations), "Invalid corporation catalog")
    require(
        integer(state["revision"])
        and isinstance(state["history"], list)
        and len(state["history"]) == state["revision"]
        and all(isinstance(a, dict) for a in state["history"]),
        "Invalid revision/history",
    )
    require(state["phase"] in phases, "Unknown phase")
    require(
        state["round"] in ("auction", "stock", "operating", "finished"), "Unknown round"
    )
    require(
        type(state["finished"]) is bool
        and state["finished"] == (state["round"] == "finished"),
        "Invalid finished round",
    )
    require(
        state["finished"] or (state["end_reason"] is None and state["result"] is None),
        "Premature terminal result",
    )
    require(type(state["bank"]) is int, "Invariant: bank must use whole currency units")
    for bids in state["auction"]["bids"].values():
        require(
            isinstance(bids, dict)
            and set(bids).issubset(players)
            and all(integer(amount) for amount in bids.values()),
            "Invalid bid escrow",
        )
    for cid, corp in corps.items():
        require(
            corp["id"] == cid and set(corp["holdings"]) == set(players),
            "Invalid share holders",
        )
        require(
            all(integer(corp[key]) and corp[key] % 10 == 0 for key in ("ipo", "pool")),
            "Invariant: share supply must use 10% units",
        )
        require(
            corp["president"] is None or corp["president"] in players,
            "Invalid corporation president",
        )
        if corp["president"] is not None:
            require(
                corp["holdings"][corp["president"]] == max(corp["holdings"].values()),
                "Stale presidency in share ledger",
            )
        position = corp["position"]
        require(
            position is None
            or (
                isinstance(position, list)
                and len(position) == 2
                and all(integer(v) for v in position)
                and position[0] < len(market)
                and position[1] < len(market[position[0]])
                and market[position[0]][position[1]]
            ),
            "Invalid market position",
        )
        trains = corp["trains"]
        require(
            isinstance(trains, list)
            and all(isinstance(t, str) and t in state["trains"] for t in trains)
            and len(trains) == len(set(trains)),
            "Invariant: duplicate or unknown train",
        )
    for tid, train in state["trains"].items():
        require(
            train["id"] == tid and train["owner"] in (None, "depot", *corps),
            "Invariant: unknown train owner or ID",
        )
        require(
            type(train["rusted"]) is bool
            and (not train["rusted"] or train["owner"] is None),
            "Invariant: rusted train cannot be owned",
        )
    require(
        set(board) == set(board_data["hexes"])
        and set(state["tiles"]) == set(board_data["tiles"]),
        "Invariant: incomplete board/tile catalog",
    )
    require(
        all(integer(n) for n in state["tiles"].values()),
        "Invariant: invalid tile counts",
    )
    token_counts = {cid: 0 for cid in corps}
    for coord, tile in board.items():
        require(
            tile["tile"] is None or tile["tile"] in board_data["tiles"],
            "Unknown laid tile",
        )
        require(
            isinstance(tile["tokens"], list)
            and len(tile["tokens"]) == len(tile["nodes"]),
            "Invalid token/node arrays",
        )
        present = set()
        for node, tokens in zip(tile["nodes"], tile["tokens"]):
            require(
                isinstance(tokens, list)
                and all(isinstance(cid, str) and cid in corps for cid in tokens),
                "Unknown station token",
            )
            require(
                len(tokens) <= node["slots"] and (not tokens or node["kind"] == "city"),
                "Overfull or noncity station",
            )
            for cid in tokens:
                require(cid not in present, "Duplicate station in hex")
                present.add(cid)
                token_counts[cid] += 1
    for cid, corp in corps.items():
        require(token_counts[cid] <= corp["token_supply"], "Station supply exceeded")
        if "home_city" in corp and corp["home_placed"]:
            require(
                cid in board[corp["home"]]["tokens"][corp["home_city"]],
                "Missing placed home token",
            )
    if state["finished"]:
        require(
            state["current_player"] is None
            and state["current_corporation"] is None
            and state["end_reason"] in ("bank", "bankruptcy")
            and isinstance(state["result"], dict)
            and set(state["result"]) == set(players),
            "Invalid terminal state",
        )
    elif state["round"] == "operating":
        cid, turn = state["current_corporation"], state["operating_turn"]
        require(
            cid in corps and isinstance(turn, dict),
            "Missing operating corporation/turn",
        )
        operating_order, index = state["or_order"], state["or_index"]
        require(
            isinstance(operating_order, list)
            and all(isinstance(c, str) and c in corps for c in operating_order)
            and len(operating_order) == len(set(operating_order))
            and integer(index)
            and index < len(operating_order)
            and operating_order[index] == cid,
            "Invalid operating order/index",
        )
        require(
            turn["step"] in ("track", "token", "routes", "dividend", "train"),
            "Unknown operating step",
        )
        require(
            type(turn["dividend"]) is bool
            and turn["dividend"] == (turn["step"] == "train"),
            "Invalid dividend step",
        )
        pending = state.get("pending_special")
        require(
            pending is None
            or (
                isinstance(pending, dict)
                and pending.get("player") in players
                and pending.get("resume_player") == corps[cid]["president"]
            ),
            "Invalid special interrupt",
        )
        actor = pending["player"] if pending else corps[cid]["president"]
        require(
            state["current_player"] == actor and actor in players,
            "Stale operating president",
        )
    else:
        require(
            state["current_corporation"] is None and state["operating_turn"] is None,
            "Unexpected operating turn",
        )
        require(state["current_player"] in players, "Invalid active player")
        if state["round"] == "stock":
            require(isinstance(state["stock_turn"], dict), "Missing stock turn")
