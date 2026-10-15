"""Deterministic 1889 rules controller.

Public functions accept/return plain JSON-compatible state. Every action is
validated on a deep copy, so rejection is atomic and independent games never
share mutable configuration. Money is conserved, including a negative bank
balance after bank exhaustion.
"""

from copy import deepcopy

from app.engine_validation import state_errors, validate_snapshot

from .errors import RuleError, require
from .data import (
    BOARD_DATA,
    CORPORATIONS,
    PRIVATES,
    PAR_PRICES,
    PAR_POSITIONS,
    CERT_LIMITS,
    TRAIN_TYPES,
    PHASES,
    RUSTS,
    MARKET,
)
from . import board as topology

SCHEMA_VERSION = 1


def new_game(names, player_ids=None):
    require(
        isinstance(names, list) and 2 <= len(names) <= 6, "1889 requires 2–6 players"
    )
    require(
        all(isinstance(n, str) and n.strip() for n in names)
        and len(set(n.strip() for n in names)) == len(names),
        "Player names must be nonempty strings",
    )
    ids = (
        list(player_ids)
        if player_ids is not None
        else ["p" + str(i + 1) for i in range(len(names))]
    )
    require(
        len(ids) == len(names)
        and all(
            isinstance(i, str)
            and i
            and i not in CORPORATIONS
            and i not in ("bank", "depot")
            for i in ids
        )
        and len(set(ids)) == len(ids),
        "Invalid or duplicate player IDs",
    )
    state = {
        "schema_version": SCHEMA_VERSION,
        "variant": "1889",
        "revision": 0,
        "players": {
            pid: {
                "id": pid,
                "name": name.strip(),
                "cash": 420 if len(names) <= 4 else 390,
                "bankrupt": False,
            }
            for pid, name in zip(ids, names)
        },
        "player_order": ids,
        "priority": ids[0],
        "current_player": ids[0],
        "bank": 7000 - len(names) * (420 if len(names) <= 4 else 390),
        "bank_broken": False,
        "end_after_set": False,
        "phase": "2",
        "round": "auction",
        "stock_round": 0,
        "or_number": 0,
        "or_total": 1,
        "or_order": [],
        "or_index": 0,
        "current_corporation": None,
        "operating_turn": None,
        "market_sequence": 0,
        "finished": False,
        "end_reason": None,
        "result": None,
        "log": [],
        "history": [],
        "board": topology.initial_board(),
        "tiles": {tid: spec["count"] for tid, spec in BOARD_DATA["tiles"].items()},
        "corporations": {},
        "privates": {},
        "trains": {},
        "pending_par": None,
        "pending_special": None,
        "auction": {
            "bids": {
                p: {}
                for p in PRIVATES
                if not (
                    (p == "SIR" and len(names) == 2) or (p == "UTF" and len(names) < 4)
                )
            },
            "active": None,
            "bidders": [],
            "passes": 0,
            "discount": 0,
            "resume": ids[0],
        },
        "stock_turn": None,
        "sold": {p: [] for p in ids},
        "stock_passes": 0,
        "last_deal": None,
        "pending_discards": [],
        "offers": [],
        "turn_started": False,
    }
    for cid, (name, home, tokens) in CORPORATIONS.items():
        state["corporations"][cid] = {
            "id": cid,
            "name": name,
            "home": home,
            "token_supply": tokens,
            "cash": 0,
            "ipo": 100,
            "pool": 0,
            "holdings": {p: 0 for p in ids},
            "president": None,
            "par": None,
            "position": None,
            "market_order": 0,
            "floated": False,
            "funded": False,
            "home_placed": False,
            "home_city": 0,
            "operated": False,
            "trains": [],
        }
    for pid, (name, value, revenue, hexes) in PRIVATES.items():
        if (pid == "SIR" and len(names) == 2) or (pid == "UTF" and len(names) < 4):
            continue
        state["privates"][pid] = {
            "id": pid,
            "name": name,
            "value": value,
            "revenue": revenue,
            "hexes": list(hexes),
            "owner": None,
            "closed": False,
            "used": False,
        }
    for kind, (count, price, distance) in TRAIN_TYPES.items():
        for i in range(count):
            tid = kind + "-" + str(i)
            state["trains"][tid] = {
                "id": tid,
                "type": kind,
                "price": price,
                "distance": distance,
                "owner": "depot",
                "rusted": False,
                "used": False,
            }
    validate_state(state)
    return state


@state_errors(RuleError)
def migrate_state(state):
    """Load JSON saves, recovering old turn bookkeeping from verified history."""
    require(isinstance(state, dict), "State must be an object")
    require(
        state.get("variant") == "1889"
        and type(state.get("schema_version")) is int
        and state.get("schema_version") == SCHEMA_VERSION,
        "Unsupported 1889 state schema",
    )
    result = deepcopy(state)
    if result.get("round") == "operating":
        turn = result.get("operating_turn")
        require(isinstance(turn, dict), "Missing operating turn")
        if "emergency_sales" not in turn:
            # Earlier schema-1 saves predate sale-block bookkeeping. A blank
            # default would permit a second sale of an already-used company.
            history = result.get("history")
            require(
                isinstance(history, list)
                and len(history) == result.get("revision")
                and all(isinstance(a, dict) for a in history),
                "Cannot restore emergency sales: incomplete saved history",
            )
            try:
                order = result["player_order"]
                rebuilt = replay(
                    [result["players"][p]["name"] for p in order], history, order
                )
            except (RuleError, KeyError, TypeError, ValueError) as error:
                raise RuleError(
                    "Cannot restore emergency sales: invalid saved history"
                ) from error
            restored_turn = rebuilt.get("operating_turn")
            require(
                rebuilt["round"] == "operating" and isinstance(restored_turn, dict),
                "Cannot restore emergency sales: inconsistent saved history",
            )
            turn["emergency_sales"] = list(restored_turn["emergency_sales"])
            require(
                result == rebuilt,
                "Cannot restore emergency sales: inconsistent saved history",
            )
    validate_state(result)
    return result


def _player(state, pid):
    require(pid in state["players"], "Unknown player")
    return state["players"][pid]


def _corp(state, cid):
    require(cid in state["corporations"], "Unknown corporation")
    return state["corporations"][cid]


def _private(state, pid):
    require(pid in state["privates"], "Unknown private company")
    return state["privates"][pid]


def _integer(value, name, minimum=0):
    require(
        type(value) is int and value >= minimum,
        name + " must be an integer >= " + str(minimum),
    )
    return value


def _pay(state, payer, receiver, amount):
    _integer(amount, "Payment")

    def account(who):
        if who in state["players"]:
            return state["players"][who]
        return _corp(state, who)

    if payer == "bank":
        state["bank"] -= amount
    else:
        src = account(payer)
        require(src["cash"] >= amount, "Insufficient cash")
        src["cash"] -= amount
    if receiver == "bank":
        state["bank"] += amount
    else:
        account(receiver)["cash"] += amount
    _bank_check(state)


def _bank_check(state):
    if state["bank"] <= 0:
        state["bank_broken"] = True
        state["end_after_set"] = True


def _next_player(state, pid):
    order = state["player_order"]
    return order[(order.index(pid) + 1) % len(order)]


def _price(corp):
    return (
        MARKET[corp["position"][0]][corp["position"][1]]["price"]
        if corp["position"]
        else 0
    )


def _zone(corp):
    return (
        MARKET[corp["position"][0]][corp["position"][1]]["zone"]
        if corp["position"]
        else "white"
    )


def _market_move(state, corp, direction, count=1):
    if corp["position"] is None:
        return
    row, col = corp["position"]
    for _ in range(count):
        if direction == "right":
            r, c = (row, col + 1) if col + 1 < len(MARKET[row]) else (row - 1, col)
        elif direction == "left":
            r, c = (row, col - 1) if col and MARKET[row][col - 1] else (row + 1, col)
        elif direction == "up":
            r, c = row - 1, col
        else:
            r, c = row + 1, col
        if 0 <= r < len(MARKET) and 0 <= c < len(MARKET[r]) and MARKET[r][c]:
            row, col = r, c
        else:
            break
    if [row, col] != corp["position"]:
        state["market_sequence"] += 1
        corp["market_order"] = state["market_sequence"]
        corp["position"] = [row, col]


def _set_par(state, corp, price):
    require(
        type(price) is int and price in PAR_PRICES,
        "Par must be 65, 70, 75, 80, 90 or 100",
    )
    require(corp["par"] is None, "Corporation already has a par price")
    corp["par"] = price
    corp["position"] = list(PAR_POSITIONS[price])
    state["market_sequence"] += 1
    corp["market_order"] = state["market_sequence"]


def certificate_count(state, player):
    count = sum(
        1
        for p in state["privates"].values()
        if p["owner"] == player and not p["closed"]
    )
    for corp in state["corporations"].values():
        if _zone(corp) in ("y", "o", "b"):
            continue
        count += corp["holdings"][player] // 10 - int(corp["president"] == player)
    return count


def _holding_allowed(corp, player, percent):
    if _zone(corp) in ("o", "b"):
        return True
    return percent <= 60


def _check_president(state, corp):
    current = corp["president"]
    if current is None:
        return
    maximum = max(corp["holdings"].values())
    if maximum < 20 or corp["holdings"][current] == maximum:
        return
    candidates = [
        pid for pid in state["player_order"] if corp["holdings"][pid] == maximum
    ]
    order = state["player_order"]
    corp["president"] = min(
        candidates,
        key=lambda pid: (order.index(pid) - order.index(current)) % len(order),
    )


def _float(corp, state=None):
    if corp["par"] is not None and corp["ipo"] <= 50:
        corp["floated"] = True
        if state is not None and not corp["funded"]:
            _pay(state, "bank", corp["id"], corp["par"] * 10)
            corp["funded"] = True


def _next_auction_bidder(state, after):
    """§5.7: clockwise among challengers, skipping the standing high bidder."""
    auction = state["auction"]
    bids = auction["bids"][auction["active"]]
    bidders = auction["bidders"]
    highest = max(bidders, key=lambda p: bids[p])
    order = state["player_order"]
    return min(
        (p for p in bidders if p != highest),
        key=lambda p: (order.index(p) - order.index(after) - 1) % len(order),
    )


def _award_private(state, private_id, player, price):
    private = _private(state, private_id)
    bids = state["auction"]["bids"][private_id]
    for bidder, amount in bids.items():
        state["players"][bidder]["cash"] += amount
    bids.clear()
    _pay(state, player, "bank", price)
    private["owner"] = player
    state["log"].append(player + " buys " + private_id + " for $" + str(price))


def _private_revenue(state):
    for private in state["privates"].values():
        if not private["closed"] and private["owner"]:
            _pay(state, "bank", private["owner"], private["revenue"])


def _continue_auction(state):
    auction = state["auction"]
    auction["active"] = None
    auction["bidders"] = []
    for pid in PRIVATES:
        if pid not in state["privates"]:
            continue
        private = state["privates"][pid]
        if private["owner"]:
            continue
        bids = auction["bids"][pid]
        if not bids:
            state["current_player"] = auction["resume"]
            return
        if len(bids) == 1:
            player, price = next(iter(bids.items()))
            _award_private(state, pid, player, price)
            if state["pending_par"]:
                return
        else:
            auction["active"] = pid
            auction["bidders"] = sorted(bids, key=lambda p: bids[p])
            highest = max(bids, key=bids.get)
            state["current_player"] = _next_auction_bidder(state, highest)
            return
    if not state["pending_par"]:
        last = next(pid for pid in reversed(PRIVATES) if pid in state["privates"])
        final_private = state["privates"][last]
        state["priority"] = _next_player(state, final_private["owner"])
        _start_stock(state, first=True)


def _auction_action(state, action):
    actor, kind = action["player"], action["type"]
    auction = state["auction"]
    require(actor == state["current_player"], "Not your auction turn")
    unsold = [
        pid
        for pid in PRIVATES
        if pid in state["privates"] and state["privates"][pid]["owner"] is None
    ]
    require(unsold, "No private companies remain")
    offered = auction["active"] or unsold[0]
    if kind == "pass":
        if auction["active"]:
            require(len(auction["bidders"]) > 1, "Last bidder must buy")
            auction["bidders"].remove(actor)
        else:
            require(
                not (offered == "TR" and auction["discount"] >= 20),
                "You must accept Takamatsu E-Railroad for free",
            )
            auction["passes"] += 1
    elif kind == "bid":
        pid = action.get("company")
        private = _private(state, pid)
        require(private["owner"] is None, "Private company already sold")
        bids = auction["bids"][pid]
        price = _integer(action.get("price"), "Bid")
        if auction["active"]:
            require(
                pid == offered and actor in auction["bidders"],
                "Only original bidders may participate",
            )
            minimum = max(bids[p] for p in auction["bidders"]) + 5
        elif pid == offered:
            require(not bids, "Company with bids must be auctioned")
            minimum = private["value"] - (auction["discount"] if pid == "TR" else 0)
            require(
                price == minimum, "Offered private must be bought at its current price"
            )
        else:
            minimum = max([private["value"]] + list(bids.values())) + 5
        require(price >= minimum, "Bid is below the minimum")
        previous = bids.get(actor, 0)
        require(
            state["players"][actor]["cash"] + previous >= price,
            "Insufficient uncommitted cash",
        )
        if not auction["active"] and pid == offered:
            _award_private(state, pid, actor, price)
            auction["passes"] = 0
            auction["resume"] = _next_player(state, actor)
            if not state["pending_par"]:
                _continue_auction(state)
            return
        state["players"][actor]["cash"] -= price - previous
        bids[actor] = price
        if not auction["active"]:
            auction["passes"] = 0
    else:
        raise RuleError("Auction accepts bid or pass")
    if auction["active"]:
        bidders = auction["bidders"]
        if len(bidders) == 1:
            winner = bidders[0]
            _award_private(state, offered, winner, auction["bids"][offered][winner])
            auction["active"] = None
            if not state["pending_par"]:
                _continue_auction(state)
        else:
            state["current_player"] = _next_auction_bidder(state, actor)
    else:
        state["current_player"] = _next_player(state, actor)
        auction["resume"] = state["current_player"]
        if auction["passes"] >= len(state["players"]):
            auction["passes"] = 0
            state["priority"] = state["current_player"]
            if offered == "TR":
                auction["discount"] = min(20, auction["discount"] + 5)
                if auction["discount"] == 20:
                    buyer = state["current_player"]
                    _award_private(state, "TR", buyer, 0)
                    auction["resume"] = _next_player(state, buyer)
                    _continue_auction(state)
            else:
                _private_revenue(state)


def _start_stock(state, first=False):
    state["round"] = "stock"
    state["stock_round"] += 1
    state["stock_passes"] = 0
    state["last_deal"] = None
    state["sold"] = {pid: [] for pid in state["player_order"]}
    state["current_player"] = state["priority"]
    state["current_corporation"] = None
    state["operating_turn"] = None
    state["stock_turn"] = {
        "bought": False,
        "dealt": False,
        "brown_company": None,
        "sales": [],
        "sales_before_buy": False,
    }
    state["turn_started"] = False


def _stock_deal(state):
    state["stock_passes"] = 0
    state["last_deal"] = state["current_player"]
    state["stock_turn"]["dealt"] = True


def _buy_shares(state, action, exchange=False):
    player = action["player"]
    corp = _corp(state, action.get("corporation", "IR" if exchange else None))
    source = action.get("source", "ipo")
    require(source in ("ipo", "pool"), "Share source must be ipo or pool")
    require(
        exchange or corp["id"] not in state["sold"][player],
        "Cannot buy stock sold this stock round",
    )
    first = corp["par"] is None and not exchange
    amount = _integer(
        action.get("percent", 20 if first else 10), "Stock percentage", 10
    )
    require(amount % 10 == 0, "Stock must be in 10% units")
    if first:
        require(
            source == "ipo" and corp["president"] is None and amount == 20,
            "First purchase must be the president certificate",
        )
        _set_par(state, corp, action.get("price", action.get("par")))
        corp["president"] = player
    else:
        require(
            exchange or corp["par"] is not None,
            "President certificate must be bought first",
        )
        require(
            amount == 10 or (not exchange and _zone(corp) == "b"),
            "Only one stock certificate may be bought",
        )
    if not exchange:
        turn = state["stock_turn"]
        require(
            not turn["bought"] or _zone(corp) == "b",
            "Already bought a certificate this turn",
        )
        if turn["bought"] and _zone(corp) == "b":
            require(
                turn["brown_company"] == corp["id"],
                "Multiple brown purchases must be in the same corporation",
            )
    require(corp[source] >= amount, "Insufficient shares in that source")
    # The president certificate must remain with a player; the IPO reserve may include its 20%.
    if corp["president"] is None:
        require(
            source == "pool" or corp["ipo"] - amount >= 20,
            "Cannot acquire the president certificate by exchange",
        )
    future = corp["holdings"][player] + amount
    corp[source] -= amount
    corp["holdings"][player] += amount
    _check_president(state, corp)
    require(
        _holding_allowed(corp, player, future),
        "Corporation certificate holding limit exceeded",
    )
    require(
        certificate_count(state, player) <= CERT_LIMITS[len(state["players"])],
        "Certificate limit exceeded",
    )
    if not exchange:
        state["stock_turn"]["sales_before_buy"] = bool(state["stock_turn"]["sales"])
        _pay(
            state,
            player,
            "bank",
            amount // 10 * (corp["par"] if source == "ipo" else _price(corp)),
        )
        state["stock_turn"]["bought"] = True
        state["stock_turn"]["brown_company"] = (
            corp["id"] if _zone(corp) == "b" else None
        )
        _stock_deal(state)
    _float(corp, state)


def _sell_shares(state, player, cid, amount, emergency=False):
    corp = _corp(state, cid)
    _integer(amount, "Stock percentage", 10)
    require(amount % 10 == 0, "Stock must be in 10% units")
    require(
        state["stock_round"] > 1 or emergency, "No stock sales in the first stock round"
    )
    require(corp["par"] is not None, "Unpriced stock cannot be sold")
    require(corp["holdings"][player] >= amount, "You do not own these shares")
    require(corp["pool"] + amount <= 50, "Bank Pool cannot exceed 50%")
    if emergency:
        require(
            _zone(corp) == "o" or corp["holdings"][player] - amount <= 60,
            "Emergency sale must correct holdings above 60% outside orange",
        )
        sales = state["operating_turn"]["emergency_sales"]
        require(
            cid not in sales, "Sell this corporation in one emergency block per turn"
        )
        sales.append(cid)
    else:
        turn = state["stock_turn"]
        require(cid not in turn["sales"], "Sell this corporation in one block per turn")
        require(
            not (turn["bought"] and turn["sales_before_buy"]),
            "Cannot sell-buy-sell in one turn",
        )
        turn["sales"].append(cid)
    before = corp["president"]
    corp["holdings"][player] -= amount
    if before == player and corp["holdings"][player] < 20:
        require(
            any(pid != player and pct >= 20 for pid, pct in corp["holdings"].items()),
            "President certificate cannot enter the Bank Pool",
        )
    _check_president(state, corp)
    if emergency:
        require(
            corp["president"] == before,
            "Emergency sale cannot transfer any presidency",
        )
    price = _price(corp)
    corp["pool"] += amount
    _pay(state, "bank", player, price * amount // 10)
    _market_move(state, corp, "down", amount // 10)
    if cid not in state["sold"][player]:
        state["sold"][player].append(cid)
    if emergency and state["round"] == "operating":
        completed = state["or_order"][: state["or_index"] + 1]
        remaining = set(state["or_order"][state["or_index"] + 1 :])
        state["or_order"] = completed + [
            c for c in _operating_order(state) if c in remaining
        ]


def _stock_action(state, action):
    require(action["player"] == state["current_player"], "Not your stock turn")
    kind = action["type"]
    if kind == "buy_shares":
        _buy_shares(state, action)
    elif kind == "sell_shares":
        _sell_shares(
            state, action["player"], action.get("corporation"), action.get("percent")
        )
        _stock_deal(state)
    elif kind in ("pass", "end_turn"):
        require(
            certificate_count(state, action["player"])
            <= CERT_LIMITS[len(state["players"])],
            "Must sell excess certificates before ending your turn",
        )
        require(
            all(
                _holding_allowed(c, action["player"], c["holdings"][action["player"]])
                for c in state["corporations"].values()
            ),
            "Must correct corporation certificate holding limits before ending turn",
        )
        dealt = state["stock_turn"]["dealt"]
        state["stock_passes"] = 0 if dealt else state["stock_passes"] + 1
        state["current_player"] = _next_player(state, action["player"])
        state["stock_turn"] = {
            "bought": False,
            "dealt": False,
            "brown_company": None,
            "sales": [],
            "sales_before_buy": False,
        }
        state["turn_started"] = False
        if state["stock_passes"] == len(state["players"]):
            if state["last_deal"]:
                state["priority"] = _next_player(state, state["last_deal"])
            for cid in _operating_order(state):
                corp = state["corporations"][cid]
                if corp["ipo"] == 0 and corp["pool"] == 0:
                    _market_move(state, corp, "up")
            state["or_total"] = PHASES[state["phase"]][2]
            state["or_number"] = 1
            _start_operating(state)
    else:
        raise RuleError("Illegal stock-round action")


def _operating_order(state):
    corporations = [c for c in state["corporations"].values() if c["floated"]]
    corporations.sort(
        key=lambda c: (
            -_price(c),
            -c["position"][1],
            c["position"][0],
            c["market_order"],
        )
    )
    return [c["id"] for c in corporations]


def _start_operating(state):
    state["round"] = "operating"
    _private_revenue(state)
    state["or_order"] = _operating_order(state)
    state["or_index"] = 0
    # New corporations are funded at flotation (§5.6.4). Retain this fallback
    # for older saved games that deferred their capital until the first OR.
    for cid in state["or_order"]:
        corp = state["corporations"][cid]
        if not corp["funded"]:
            _pay(state, "bank", cid, corp["par"] * 10)
            corp["funded"] = True
        if not corp["home_placed"]:
            topology.place_token(state, cid, corp["home"], corp["home_city"], home=True)
    if not state["or_order"]:
        _finish_operating_set(state)
    else:
        _start_corporation(state)


def _start_corporation(state):
    cid = state["or_order"][state["or_index"]]
    corp = state["corporations"][cid]
    state["current_corporation"] = cid
    state["current_player"] = corp["president"]
    state["turn_started"] = False
    state["operating_turn"] = {
        "step": "track",
        "laid": False,
        "tokened": False,
        "routes": None,
        "revenue": 0,
        "dividend": False,
        "new_trains": [],
        "emergency_sales": [],
        "dh_free": False,
    }
    if not corp["home_placed"]:
        topology.place_token(
            state, cid, corp["home"], corp.get("home_city", 0), home=True
        )


def _finish_operating_set(state):
    if state["end_after_set"]:
        _end_game(state, "bank")
    else:
        _start_stock(state)


def _end_corporation(state):
    cid = state["current_corporation"]
    corp = state["corporations"][cid]
    require(corp["home_placed"], "Corporation must choose its home token position")
    require(
        state["operating_turn"]["dividend"],
        "Must resolve revenue and dividend decision",
    )
    if not corp["trains"]:
        require(
            not topology.route_candidates(state, cid, limit=1),
            "Corporation with a route must buy a train",
        )
    corp["operated"] = True
    state["or_index"] += 1
    if state["or_index"] < len(state["or_order"]):
        _start_corporation(state)
    elif state["or_number"] < state["or_total"]:
        state["or_number"] += 1
        _start_operating(state)
    else:
        _finish_operating_set(state)


def _skip_to(state, step):
    steps = ["track", "token", "routes", "dividend", "train"]
    turn = state["operating_turn"]
    require(
        steps.index(step) >= steps.index(turn["step"]),
        "Operating steps must be performed in order",
    )
    if steps.index(step) > steps.index("routes") and turn["routes"] is None:
        # Empty route sets are legal only if the corporation has no runnable train.
        cid = state["current_corporation"]
        require(
            not any(
                topology.route_candidates(state, cid, tid, limit=1)
                for tid in state["corporations"][cid]["trains"]
            ),
            "Run the available trains before dividends",
        )
        turn["routes"] = []
        turn["revenue"] = 0
    if step == "train":
        require(turn["dividend"], "Revenue must be resolved before buying trains")
    turn["step"] = step


def _dividend(state, payout):
    require(type(payout) is bool, "payout must be boolean")
    turn = state["operating_turn"]
    _skip_to(state, "dividend")
    require(not turn["dividend"], "Dividend decision already made")
    corp = _corp(state, state["current_corporation"])
    # MF/ER may change the board after a claim (§§11,15.2). Until payment
    # locks it (§8.3), score against the current board and recheck empty claims.
    if turn["routes"]:
        turn["revenue"] = topology.validate_routes(state, corp["id"], turn["routes"])
    else:
        require(
            not any(
                topology.route_candidates(state, corp["id"], tid, limit=1)
                for tid in corp["trains"]
            ),
            "Available trains must run",
        )
    revenue = turn["revenue"]
    if payout and revenue:
        for pid, percent in corp["holdings"].items():
            _pay(state, "bank", pid, revenue * percent // 100)
        _pay(state, "bank", corp["id"], revenue * corp["pool"] // 100)
        _market_move(state, corp, "right")
    else:
        _pay(state, "bank", corp["id"], revenue)
        _market_move(state, corp, "left")
    turn["dividend"] = True
    turn["step"] = "train"


def available_depot(state):
    new = [
        t
        for t in state["trains"].values()
        if t["owner"] == "depot" and not t["rusted"] and not t["used"]
    ]
    order = list(TRAIN_TYPES)
    regular = [t for t in new if t["type"] != "D"]
    smallest = min((order.index(t["type"]) for t in regular), default=99)
    return [
        t["id"]
        for t in state["trains"].values()
        if t["owner"] == "depot"
        and not t["rusted"]
        and (
            t["used"]
            or (t["type"] == "D" and state["phase"] in ("6", "D"))
            or (t["type"] != "D" and order.index(t["type"]) == smallest)
        )
    ]


def _phase_change(state, train_type):
    if list(PHASES).index(train_type) <= list(PHASES).index(state["phase"]):
        return
    state["phase"] = train_type
    state["log"].append("Phase " + train_type)
    if train_type == "5":
        for private in state["privates"].values():
            if private["id"] == "UTF" and private["owner"] in state["players"]:
                private["revenue"] = 50
            else:
                private["closed"] = True
    rust = RUSTS.get(train_type)
    if rust:
        for train in state["trains"].values():
            if train["type"] == rust:
                if train["owner"] in state["corporations"]:
                    state["corporations"][train["owner"]]["trains"].remove(train["id"])
                train["owner"], train["rusted"] = None, True
    limit = PHASES[state["phase"]][0]
    state["pending_discards"] = [
        cid for cid, c in state["corporations"].items() if len(c["trains"]) > limit
    ]


def _buy_train(state, action):
    cid = state["current_corporation"]
    corp = _corp(state, cid)
    _skip_to(state, "train")
    tid = action.get("train")
    require(tid in state["trains"], "Unknown train")
    train = state["trains"][tid]
    seller = train["owner"]
    require(not train["rusted"] and seller and seller != cid, "Train is not for sale")
    require(seller == "depot" or seller in state["corporations"], "Invalid train owner")
    trade_id = action.get("trade_in")
    if trade_id:
        require(
            seller == "depot" and train["type"] == "D" and trade_id in corp["trains"],
            "Invalid Diesel trade-in",
        )
        trade = state["trains"][trade_id]
        require(
            trade["type"] in ("4", "5", "6"), "Only a 4, 5 or 6 train can be traded in"
        )
    require(
        len(corp["trains"]) - int(bool(trade_id)) < PHASES[state["phase"]][0],
        "Train limit already reached",
    )
    price = (
        train["price"] - (300 if trade_id else 0)
        if seller == "depot"
        else action.get("price")
    )
    _integer(price, "Train price", 1)
    if seller == "depot":
        require(tid in available_depot(state), "Train not yet available from depot")
        require(
            action.get("price", price) == price,
            "Depot trains must be bought at the fixed price",
        )
    else:
        require(
            not state["operating_turn"]["emergency_sales"],
            "Emergency funding requires a depot train",
        )
        _agreement(state, action["player"], "train", tid, seller, cid, price)
    if corp["cash"] < price:
        require(
            not corp["trains"] and topology.route_candidates(state, cid, limit=1),
            "President may contribute only to a mandatory train purchase",
        )
        if seller == "depot":
            cheapest = min(state["trains"][t]["price"] for t in available_depot(state))
            require(
                price == cheapest,
                "Emergency purchase must use cheapest depot alternative",
            )
        else:
            raise RuleError("President cannot subsidize another corporation's train")
        _pay(state, corp["president"], cid, price - corp["cash"])
    _pay(state, cid, "bank" if seller == "depot" else seller, price)
    if seller != "depot":
        _corp(state, seller)["trains"].remove(tid)
    if trade_id:
        corp["trains"].remove(trade_id)
        trade["owner"], trade["used"] = "depot", True
    train["owner"] = cid
    corp["trains"].append(tid)
    state["operating_turn"]["new_trains"].append(tid)
    if seller == "depot":
        _phase_change(state, train["type"])
    if train["type"] == "D" and seller == "depot":
        # Keep one new Diesel available indefinitely; returned used trains coexist.
        index = (
            max(int(t.split("-")[1]) for t in state["trains"] if t.startswith("D-")) + 1
        )
        next_id = "D-" + str(index)
        state["trains"][next_id] = dict(train, id=next_id, owner="depot", used=False)


def _discard_train(state, action):
    cid = action.get("corporation")
    require(cid in state["pending_discards"], "Corporation does not need to discard")
    corp = _corp(state, cid)
    require(
        action["player"] == corp["president"],
        "Only its president may choose a discarded train",
    )
    tid = action.get("train")
    require(tid in corp["trains"], "Corporation does not own that train")
    corp["trains"].remove(tid)
    state["trains"][tid]["owner"], state["trains"][tid]["used"] = "depot", True
    if len(corp["trains"]) <= PHASES[state["phase"]][0]:
        state["pending_discards"].remove(cid)


def _exchange_private(state, action):
    private = state["privates"]["DR"]
    player = action["player"]
    require(
        private["owner"] == player and not private["closed"],
        "Must own open Dougo Railway",
    )
    require(
        state["round"] in ("stock", "operating"),
        "Exchange requires stock or operating round",
    )
    require(action.get("source", "ipo") == "ipo", "Dougo exchanges only for IPO shares")
    private["closed"] = True
    _buy_shares(
        state, dict(action, corporation="IR", percent=10, source="ipo"), exchange=True
    )
    if state["round"] == "stock":
        # An exchange acquires stock (§4.1.1); a port lay does not. An
        # out-of-turn exchange must not mark somebody else's turn as dealt.
        state["stock_passes"] = 0
        state["last_deal"] = player
        if state["current_player"] == player:
            state["stock_turn"]["dealt"] = True
    if state["round"] == "operating" and state["current_corporation"] == "IR":
        state["current_player"] = state["corporations"]["IR"]["president"]


def _controller(state, entity):
    if entity in state["players"]:
        return entity
    return _corp(state, entity)["president"]


def _offer(state, action):
    kind, item, seller, buyer = (
        action.get(k) for k in ("kind", "item", "seller", "buyer")
    )
    require(kind in ("private", "train"), "Offer kind must be private or train")
    if kind == "private":
        require(
            buyer in state["corporations"], "1889 privates sell only to corporations"
        )
        private = _private(state, item)
        require(
            not private["closed"]
            and private["owner"] == seller
            and seller in state["players"],
            "Seller must own open private",
        )
    else:
        require(
            item in state["trains"]
            and state["trains"][item]["owner"] == seller
            and seller in state["corporations"],
            "Seller must own train",
        )
        require(buyer in state["corporations"], "Only corporations buy trains")
    require(seller != buyer, "Buyer and seller must differ")
    controllers = [_controller(state, seller), _controller(state, buyer)]
    require(
        action["player"] in controllers, "Only a transaction party can make an offer"
    )
    price = _integer(action.get("price"), "Offer price", 1 if kind == "train" else 0)
    offer = {
        "kind": kind,
        "item": item,
        "seller": seller,
        "buyer": buyer,
        "price": price,
        "offered_by": action["player"],
    }
    if offer not in state["offers"]:
        state["offers"].append(offer)


def _agreement(state, actor, kind, item, seller, buyer, price):
    seller_player, buyer_player = _controller(state, seller), _controller(state, buyer)
    require(
        actor in (seller_player, buyer_player), "Only transaction parties may accept"
    )
    if seller_player == buyer_player:
        return
    other = seller_player if actor == buyer_player else buyer_player
    offer = {
        "kind": kind,
        "item": item,
        "seller": seller,
        "buyer": buyer,
        "price": price,
        "offered_by": other,
    }
    require(
        offer in state["offers"],
        "The other party must submit a matching authenticated offer",
    )
    state["offers"].remove(offer)


def _buy_private(state, action):
    private = _private(state, action.get("company"))
    require(
        not private["closed"] and private["owner"] in state["players"],
        "Private must be open and player-owned",
    )
    seller = private["owner"]
    buyer = action.get("buyer", action["player"])
    require(buyer != seller, "Buyer already owns private")
    price = _integer(action.get("price"), "Private price", 0)
    _agreement(state, action["player"], "private", private["id"], seller, buyer, price)
    require(
        buyer in state["corporations"], "1889 privates cannot be sold between players"
    )
    require(
        state["round"] == "operating" and buyer == state["current_corporation"],
        "Only the operating corporation can buy privates",
    )
    require(
        action["player"] == _corp(state, buyer)["president"], "Only president may buy"
    )
    require(state["phase"] in ("3", "4"), "Private purchases require phase 3 or 4")
    require(
        private["value"] <= price * 2 <= private["value"] * 4,
        "Price must be half to twice face value",
    )
    _pay(state, buyer, seller, price)
    private["owner"] = buyer
    if private["id"] == "ER" and not private["used"]:
        state["pending_special"] = {
            "company": "ER",
            "player": seller,
            "resume_player": state["current_player"],
        }
        state["current_player"] = seller


def _port_allowed(state, player):
    mf = state["privates"]["MF"]
    return (
        mf["owner"] == player
        and not mf["closed"]
        and not mf["used"]
        and not state["pending_discards"]
        and not state["pending_par"]
        and not state["pending_special"]
        and (
            state["round"] in ("auction", "stock")
            or (
                state["round"] == "operating"
                and (not state["turn_started"] or state["current_player"] == player)
            )
        )
    )


def _port_tile(state, action):
    player = action["player"]
    require(_port_allowed(state, player), "Mitsubishi Ferry unavailable at this time")
    coord = action.get("hex")
    require(
        coord in ("B11", "G10", "I12", "J9") and state["board"][coord]["tile"] is None,
        "Port needs an unbuilt coastal town",
    )
    require(action.get("tile") == "437", "Mitsubishi Ferry requires the port tile")
    cid = state["current_corporation"] or next(iter(state["corporations"]))
    topology.lay_tile(
        state,
        cid,
        coord,
        "437",
        action.get("rotation", 0),
        special="MF",
        spender=player,
    )
    state["privates"]["MF"]["used"] = True


def _resolve_special(state, action):
    pending = state["pending_special"]
    require(
        action["player"] == pending["player"],
        "The Ehime seller must resolve the special lay",
    )
    if action["type"] == "lay_tile":
        require(
            action.get("hex") == "C4"
            and action.get("tile") in ("12", "13", "14", "15", "205", "206"),
            "Ehime requires a green city tile at C4",
        )
        topology.lay_tile(
            state,
            state["privates"]["ER"]["owner"],
            "C4",
            action["tile"],
            action.get("rotation", 0),
            special="ER",
            spender=action["player"],
        )
    else:
        require(
            action["type"] in ("pass", "skip", "end_turn"),
            "Resolve the Ehime lay or pass",
        )
    state["privates"]["ER"]["used"] = True
    state["current_player"] = pending["resume_player"]
    state["pending_special"] = None


def _maximum_emergency_sale(state, player, cid):
    """Use the actual sale rules for funding estimates and liquidation alike."""
    corp = state["corporations"][cid]
    maximum = min(corp["holdings"][player], 50 - corp["pool"])
    for amount in range(maximum, 0, -10):
        trial = deepcopy(state)
        try:
            _sell_shares(trial, player, cid, amount, emergency=True)
        except RuleError:
            continue
        return amount
    return 0


def _bankrupt(state, action):
    cid = state["current_corporation"]
    corp = _corp(state, cid)
    require(
        not corp["trains"] and topology.route_candidates(state, cid, limit=1),
        "No mandatory train purchase",
    )
    depot = available_depot(state)
    require(depot, "No depot train available")
    cheapest = min(state["trains"][t]["price"] for t in depot)
    pid = corp["president"]
    potential = corp["cash"] + state["players"][pid]["cash"]
    for other in state["corporations"].values():
        if other["par"]:
            potential += (
                _maximum_emergency_sale(state, pid, other["id"]) // 10 * _price(other)
            )
    require(
        potential < cheapest,
        "Must use personal cash and legally saleable stock before bankruptcy",
    )
    state["players"][pid]["bankrupt"] = True
    # Liquidate each legally saleable bundle at its pre-sale market price.
    # This is part of the bankruptcy action, so presidencies and market falls
    # remain deterministic even when the player cannot afford any train.
    for other_id in CORPORATIONS:
        amount = _maximum_emergency_sale(state, pid, other_id)
        if amount:
            _sell_shares(state, pid, other_id, amount, emergency=True)
    _pay(state, pid, "bank", state["players"][pid]["cash"])
    _end_game(state, "bankruptcy")


def _operating_action(state, action):
    require(
        action["player"] == state["current_player"],
        "Only the operating president may act",
    )
    cid = state["current_corporation"]
    corp = _corp(state, cid)
    require(
        corp["president"] == action["player"], "Only president may operate corporation"
    )
    turn, kind = state["operating_turn"], action["type"]
    if kind == "lay_tile":
        require(
            not action.get("special"),
            "Use the private-company action for special construction",
        )
        _skip_to(state, "track")
        require(not turn["laid"], "Only one normal tile per turn")
        topology.lay_tile(
            state, cid, action.get("hex"), action.get("tile"), action.get("rotation", 0)
        )
        turn["laid"], turn["step"] = True, "token"
    elif kind == "place_token":
        _skip_to(state, "token")
        require(not turn["tokened"], "Only one additional station per turn")
        topology.place_token(state, cid, action.get("hex"), action.get("city", 0))
        turn["tokened"], turn["step"] = True, "routes"
    elif kind in ("run_routes", "run_best_routes"):
        if turn["step"] == "dividend" and not turn["dividend"]:
            # §8.3 permits correcting the claim until its dividend is resolved.
            turn["step"] = "routes"
        _skip_to(state, "routes")
        routes = (
            topology.best_routes(state, cid)["routes"]
            if kind == "run_best_routes"
            else action.get("routes")
        )
        require(isinstance(routes, list), "Routes must be a list")
        routes = [
            (
                topology.route_from_paths(state, route)
                if isinstance(route, dict) and "paths" in route
                else route
            )
            for route in routes
        ]
        revenue = topology.validate_routes(state, cid, routes)
        require(
            routes
            or not any(
                topology.route_candidates(state, cid, t, limit=1)
                for t in corp["trains"]
            ),
            "Available trains must run",
        )
        turn["routes"], turn["revenue"] = deepcopy(routes), revenue
        turn["step"] = "dividend"
    elif kind == "dividend":
        _dividend(
            state,
            action.get(
                "payout", {"payout": True, "withhold": False}.get(action.get("kind"))
            ),
        )
    elif kind == "buy_train":
        _buy_train(state, action)
    elif kind == "emergency_sell":
        _skip_to(state, "train")
        require(
            not corp["trains"] and topology.route_candidates(state, cid, limit=1),
            "No emergency train requirement",
        )
        depot = available_depot(state)
        require(
            depot
            and corp["cash"] + state["players"][corp["president"]]["cash"]
            < min(state["trains"][t]["price"] for t in depot),
            "Use available cash before forced share sales",
        )
        amount = _integer(action.get("percent"), "Stock percentage", 10)
        selling = _corp(state, action.get("corporation"))
        shortfall = (
            min(state["trains"][t]["price"] for t in depot)
            - corp["cash"]
            - state["players"][corp["president"]]["cash"]
        )
        correction = (
            max(0, selling["holdings"][action["player"]] - 60)
            if _zone(selling) != "o"
            else 0
        )
        require(
            amount <= correction or (amount // 10 - 1) * _price(selling) < shortfall,
            "Emergency sales may raise only the funds needed for the cheapest train",
        )
        _sell_shares(
            state,
            action["player"],
            action.get("corporation"),
            action.get("percent"),
            emergency=True,
        )
    elif kind == "bankrupt":
        _skip_to(state, "train")
        _bankrupt(state, action)
    elif kind in ("pass", "end_turn"):
        _end_corporation(state)
    elif kind == "skip":
        current = turn["step"]
        require(
            current in ("track", "token", "routes"),
            "Cannot skip required dividend or train resolution",
        )
        if current == "routes":
            require(
                not any(
                    topology.route_candidates(state, cid, t, limit=1)
                    for t in corp["trains"]
                ),
                "Available trains must run",
            )
            turn["routes"], turn["revenue"], turn["step"] = [], 0, "dividend"
        else:
            turn["step"] = "token" if current == "track" else "routes"
    else:
        raise RuleError("Illegal operating-round action")


def best_routes(state, corporation=None):
    """Return an exact maximum-revenue route allocation without changing state."""
    cid = state["current_corporation"] if corporation is None else corporation
    return topology.best_routes(state, cid)


def scores(state):
    result = {}
    for pid, player in state["players"].items():
        value = player["cash"]
        value += sum(
            c["holdings"][pid] // 10 * _price(c) for c in state["corporations"].values()
        )
        value += sum(
            p["value"]
            for p in state["privates"].values()
            if p["owner"] == pid and not p["closed"]
        )
        result[pid] = value
    return result


def _end_game(state, reason):
    state["finished"], state["end_reason"] = True, reason
    state["round"], state["current_player"], state["current_corporation"] = (
        "finished",
        None,
        None,
    )
    state["result"] = scores(state)


def apply_action(state, action, expected_revision=None):
    """Apply a validated action atomically, returning a new independent state.

    Caller-supplied ``player`` must be bound to the authenticated identity by the
    transport. Optional revision protects against stale concurrent submissions.
    """
    require(isinstance(action, dict), "Action must be an object")
    candidate = migrate_state(state)
    if expected_revision is not None:
        _integer(expected_revision, "Revision")
    if "expected_action_id" in action:
        _integer(action["expected_action_id"], "Action revision")
    require(not state["finished"], "Game has ended")
    require(
        expected_revision is None or expected_revision == state["revision"],
        "Stale state revision",
    )
    require(
        action.get("expected_action_id", state["revision"]) == state["revision"],
        "Stale action version",
    )
    require(isinstance(action.get("type"), str), "Action type required")
    for field in (
        "player",
        "corporation",
        "company",
        "train",
        "source",
        "buyer",
        "seller",
        "kind",
        "item",
        "special",
        "trade_in",
        "tile",
        "hex",
    ):
        require(
            field not in action or isinstance(action[field], str),
            field + " must be a string",
        )
    _player(state, action.get("player"))
    kind = action["type"]
    if kind in ("exchange_dr", "bankruptcy"):
        kind = {"exchange_dr": "exchange_private", "bankruptcy": "bankrupt"}[kind]
        action = dict(action, type=kind)
    if candidate["pending_special"]:
        _resolve_special(candidate, action)
    elif kind == "lay_tile" and action.get("special") == "MF":
        _port_tile(candidate, action)
    elif candidate["pending_discards"]:
        require(kind == "discard_train", "Resolve excess trains before continuing")
        _discard_train(candidate, action)
    elif kind == "exchange_private":
        _exchange_private(candidate, action)
    elif kind == "offer":
        _offer(candidate, action)
    elif kind == "buy_private" and candidate["round"] != "auction":
        _buy_private(candidate, action)
        candidate["turn_started"] = True
    elif candidate["round"] == "auction":
        if kind == "buy_private":
            private = _private(candidate, action.get("company"))
            price = private["value"] - (
                candidate["auction"]["discount"] if private["id"] == "TR" else 0
            )
            action = dict(action, type="bid", price=action.get("price", price))
        _auction_action(candidate, action)
    elif candidate["round"] == "stock":
        candidate["turn_started"] = True
        _stock_action(candidate, action)
    elif candidate["round"] == "operating":
        candidate["turn_started"] = True
        _operating_action(candidate, action)
    else:
        raise RuleError("Unknown round")
    _bank_check(candidate)
    candidate["revision"] += 1
    candidate["history"].append(deepcopy(action))
    validate_state(candidate)
    return candidate


@state_errors(RuleError)
def validate_state(state):
    """Validate accounting/component invariants after every successful action."""
    require(isinstance(state, dict), "State must be an object")
    require(
        type(state.get("schema_version")) is int
        and state["schema_version"] in (1, SCHEMA_VERSION),
        "Unsupported 1889 state schema",
    )
    require(state.get("variant") == "1889", "Wrong game variant")
    validate_snapshot(state, require, CORPORATIONS, BOARD_DATA, PHASES, MARKET)
    if state.get("round") == "operating":
        turn = state.get("operating_turn")
        require(isinstance(turn, dict), "Missing operating turn")
        sales = turn.get("emergency_sales")
        require(
            isinstance(sales, list)
            and all(
                isinstance(cid, str) and cid in state["corporations"] for cid in sales
            )
            and len(sales) == len(set(sales)),
            "Invalid emergency sale bookkeeping",
        )
    if state["schema_version"] == SCHEMA_VERSION:
        for corp in state["corporations"].values():
            city = corp.get("home_city")
            nodes = state["board"][corp["home"]]["nodes"]
            require(
                type(city) is int and 0 <= city < len(nodes),
                "Invalid home-city mapping",
            )
    escrow = sum(sum(bids.values()) for bids in state["auction"]["bids"].values())
    money = state["bank"] + escrow
    money += sum(p["cash"] for p in state["players"].values())
    money += sum(c["cash"] for c in state["corporations"].values())
    require(money == 7000, "Invariant: total money must remain ¥7,000")
    require(
        all(
            type(p["cash"]) is int and p["cash"] >= 0 for p in state["players"].values()
        ),
        "Invariant: player cash",
    )
    for cid, corp in state["corporations"].items():
        require(
            type(corp["cash"]) is int and corp["cash"] >= 0, "Invariant: corporate cash"
        )
        require(
            corp["ipo"] + corp["pool"] + sum(corp["holdings"].values()) == 100,
            "Invariant: shares sum to 100%",
        )
        require(
            0 <= corp["pool"] <= 50 and 0 <= corp["ipo"] <= 100,
            "Invariant: share supply",
        )
        require(
            all(
                type(n) is int and n >= 0 and n % 10 == 0
                for n in corp["holdings"].values()
            ),
            "Invariant: holdings",
        )
        require(
            corp["president"] is None or corp["holdings"][corp["president"]] >= 20,
            "Invariant: president certificate",
        )
        require(
            set(corp["trains"])
            == {t["id"] for t in state["trains"].values() if t["owner"] == cid},
            "Invariant: train ownership",
        )
    for tid, count in state["tiles"].items():
        laid = sum(tile["tile"] == tid for tile in state["board"].values())
        require(
            count >= 0 and count + laid == BOARD_DATA["tiles"][tid]["count"],
            "Invariant: finite tile supply",
        )
    require(
        state["current_player"] is None or state["current_player"] in state["players"],
        "Invariant: active player",
    )
    return True


def legal_actions(state, player=None):
    """Return action types and structured choices; apply_action is authoritative.

    Tile rotations, route paths and negotiated prices are supplied by clients.
    ``choices`` contains candidates and may require further rule validation.
    """
    if state["finished"]:
        return {"player": None, "types": [], "choices": {}}
    if state["pending_special"]:
        actor = state["pending_special"]["player"]
        return {
            "player": actor,
            "active_player": actor,
            "types": ["lay_tile", "pass"] if player in (None, actor) else [],
            "choices": {"hex": "C4", "tiles": ["12", "13", "14", "15", "205", "206"]},
        }
    actor = state["pending_par"] or state["current_player"]
    choices = {}
    if state["pending_par"]:
        types, choices = ["par"], {"prices": list(PAR_PRICES)}
    elif state["pending_discards"]:
        types = ["discard_train"]
        choices["corporations"] = {
            cid: list(state["corporations"][cid]["trains"])
            for cid in state["pending_discards"]
        }
        actors = [
            state["corporations"][cid]["president"] for cid in state["pending_discards"]
        ]
        actor = player if player in actors else actors[0]
    elif state["round"] == "auction":
        types = ["bid", "pass"]
        choices["companies"] = [
            p["id"] for p in state["privates"].values() if p["owner"] is None
        ]
    elif state["round"] == "stock":
        types = [
            "buy_shares",
            "sell_shares",
            "end_turn",
            "buy_private",
        ]
        choices["corporations"] = list(state["corporations"])
    else:
        step = state["operating_turn"]["step"]
        types = {
            "track": ["lay_tile", "place_token", "run_routes", "dividend", "skip"],
            "token": ["place_token", "run_routes", "dividend", "skip"],
            "routes": ["run_routes", "dividend"],
            "dividend": ["dividend"],
            "train": ["buy_train", "end_turn", "emergency_sell", "bankrupt"],
        }[step]
        types += ["buy_private"]
        if step in ("track", "token", "routes", "dividend"):
            types.append("run_best_routes")
        if step == "dividend":
            types.append("run_routes")
        cid = state["current_corporation"]
        choices["depot"] = available_depot(state)
    requested = player if player is not None else actor
    active = actor
    if requested != actor:
        types, choices = [], {}
    if (
        not state["pending_par"]
        and not state["pending_discards"]
        and requested in state["players"]
    ):
        if _port_allowed(state, requested):
            types.append("lay_tile")
            choices["port_hexes"] = [
                h
                for h in ("B11", "G10", "I12", "J9")
                if state["board"][h]["tile"] is None
            ]
        offers = _offer_choices(state, requested)
        if offers:
            types.append("offer")
            choices["offers"] = offers
        exchanges = []
        for source in ("ipo",):
            trial = deepcopy(state)
            try:
                _exchange_private(trial, {"player": requested, "source": source})
            except RuleError:
                continue
            exchanges.append(source)
        if exchanges:
            types.append("exchange_private")
            choices["exchange_sources"] = exchanges
        if types:
            actor = requested
    return {
        "player": actor,
        "active_player": active,
        "types": types,
        "choices": choices,
    }


def _offer_choices(state, player):
    """Transaction parties available to this player; prices are negotiated."""
    corporations = [cid for cid, c in state["corporations"].items() if c["president"]]
    offers = []
    items = [
        ("private", p["id"], p["owner"], corporations)
        for p in state["privates"].values()
        if not p["closed"] and p["owner"] in state["players"]
    ]
    items += [
        ("train", t["id"], t["owner"], corporations)
        for t in state["trains"].values()
        if t["owner"] in corporations and not t["rusted"]
    ]
    for kind, item, seller, buyers in items:
        for buyer in buyers:
            if buyer != seller and player in (
                _controller(state, seller),
                _controller(state, buyer),
            ):
                offers.append(
                    {"kind": kind, "item": item, "seller": seller, "buyer": buyer}
                )
    return offers


def replay(names, actions, player_ids=None):
    """Rebuild a state from authenticated accepted actions, without I/O."""
    state = new_game(names, player_ids)
    for action in actions:
        state = apply_action(state, action)
    return state


check_invariants = validate_state


def _position(state, corporation, position):
    """Place a marker at the bottom of a market stack."""
    state["market_sequence"] += 1
    corporation["position"] = list(position)
    corporation["market_order"] = state["market_sequence"]


price = _price
certificates = certificate_count
_presidency = _check_president
_start_or = _start_operating
_move_market = _market_move


def train_limit(state):
    return PHASES[state["phase"]][0]
