"""Translate an upstream 1830 recording into this engine's public actions.

Usage: PYTHONPATH=. python tools/import_1830_fixture.py upstream-recording.json
The imported actions must finish with the independent recording's exact scores.
Source recordings and undo semantics: tobymao/18xx, MIT; see
app/engine1830/UPSTREAM_LICENSE. No Ruby is executed or needed.
"""

import json, sys
from pathlib import Path
from collections import Counter
from app.engine1830 import new_game, apply_action, RuleError
from app.engine1830 import board as B
from app.engine1830 import engine as E


def filtered(actions):
    out = [None] * len(actions)
    undos = []
    for i, a in enumerate(actions):
        if a["type"] == "undo":
            if "action_id" in a:
                at = next(
                    (j + 1 for j, b in enumerate(actions) if b["id"] == a["action_id"]),
                    0,
                )
            else:
                at = next((j for j in range(i - 1, -1, -1) if out[j]), 0)
            undos.append([(j, out[j]) for j in range(at, i) if out[j]])
            for j, _ in undos[-1]:
                out[j] = None
        elif a["type"] == "redo":
            for j, b in undos.pop():
                out[j] = b
        else:
            undos = []
            out[i] = a

    def expand(a):
        if not a["type"].startswith("program_"):
            yield a
        for b in a.get("auto_actions", []):
            yield from expand(b)

    return [b for a in out if a for b in expand(a)]


def convert_route(s, cid, r):
    adj = B.graph(s["board"])
    boundaries = set()
    for connection in r["connections"]:
        for a, z in zip(connection, connection[1:]):
            edge = next(e for e in range(6) if B.neighbor(a, e) == z)
            boundaries.add(
                tuple(sorted((a + ":e" + str(edge), z + ":e" + str((edge + 3) % 6))))
            )
    stops = set(
        n.rsplit("-", 1)[0] + ":n" + n.rsplit("-", 1)[1] for n in r.get("nodes", [])
    )
    starts = (
        list(stops)
        if stops
        else [
            h + ":n" + str(i)
            for h in r["hexes"]
            for i in range(len(s["board"][h]["nodes"]))
        ]
    )
    for start in starts:
        stack = [(start, [start], set())]
        while stack:
            cur, path, used = stack.pop()
            if cur != start and B.node_info(s["board"], cur) and used == boundaries:
                candidate = {"train": r["train"], "vertices": path}
                try:
                    value = B.validate_routes(s, cid, [candidate])
                    if value == r["revenue"]:
                        return candidate
                except RuleError:
                    pass
            for nxt in adj[cur]:
                if nxt in path:
                    continue
                seg = tuple(sorted((cur, nxt)))
                cross = cur.split(":")[0] != nxt.split(":")[0]
                if cross and seg not in boundaries:
                    continue
                if stops and B.node_info(s["board"], nxt) and nxt not in stops:
                    continue
                if (
                    len(path) > 1
                    and cur.split(":")[1].startswith("e")
                    and path[-2].split(":")[0] == cur.split(":")[0] == nxt.split(":")[0]
                ):
                    continue
                if (
                    B.node_info(s["board"], cur)
                    and cur != start
                    and (
                        B.blocked(s["board"], cur, cid)
                        or B.node_info(s["board"], cur)["kind"] == "offboard"
                    )
                ):
                    continue
                stack.append((nxt, path + [nxt], used | ({seg} if cross else set())))
    raise RuntimeError("Cannot reconstruct " + str(r))


def run(path):
    d = json.load(open(path))
    s = new_game(
        [p["name"] for p in d["players"]], [str(p["id"]) for p in d["players"]]
    )
    tile_ids = {}
    pool = set()
    last = None

    def act(kind, player=None, **kw):
        nonlocal s
        s = apply_action(s, dict(type=kind, player=player or s["current_player"], **kw))

    def finish():
        if s["round"] == "operating":
            if not s["operating_turn"]["dividend"]:
                act("dividend", payout=False)
            act("end_turn")
        elif s["round"] == "stock":
            act("end_turn")

    for index, a in enumerate(filtered(d["actions"])):
        try:
            typ = a["type"]
            entity = str(a["entity"])
            cid = entity if a["entity_type"] == "corporation" else None
            if cid is None and a["entity_type"] == "company":
                owner = s["privates"][entity]["owner"]
                cid = owner if owner in s["corporations"] else None
            actor = (
                s["corporations"][cid]["president"]
                if cid
                else (
                    s["privates"][entity]["owner"]
                    if a["entity_type"] == "company"
                    else entity
                )
            )
            if a["entity_type"] == "company" and entity == "MH":
                if s["round"] == "operating" and s["operating_turn"]["step"] == "train":
                    finish()
                act(
                    "exchange_private",
                    actor,
                    source="pool" if a["shares"][0] in pool else "ipo",
                )
                pool.difference_update(a["shares"])
                last = a
                continue
            if (
                not cid
                and s["round"] == "operating"
                and a["entity_type"] == "player"
                and not (
                    typ == "sell_shares"
                    and s["current_player"] == actor
                    and not s["corporations"][s["current_corporation"]]["trains"]
                )
            ):
                while s["round"] == "operating":
                    finish()
            if not s["pending_par"] and typ != "discard_train":
                while (
                    s["round"] == "operating"
                    and cid
                    and s["current_corporation"] != cid
                ):
                    finish()
                if s["round"] == "stock" and not cid:
                    if (
                        typ in ("buy_shares", "par")
                        and actor == s["current_player"]
                        and s["stock_turn"]["bought"]
                        and (
                            typ == "par"
                            or E._zone(
                                s["corporations"][a["shares"][0].rsplit("_", 1)[0]]
                            )
                            != "b"
                        )
                    ):
                        finish()
                    while s["round"] == "stock" and actor != s["current_player"]:
                        finish()
                if cid and s["round"] == "stock":
                    while s["round"] == "stock":
                        finish()
            if typ == "bid":
                act("bid", actor, company=a["company"], price=a["price"])
            elif typ == "pass":
                if s["round"] == "operating":
                    step = s["operating_turn"]["step"]
                    if step in ("track", "token"):
                        act("skip")
                    elif step != "train":
                        finish()
                else:
                    act("pass", actor)
            elif typ == "par":
                price = int(a["share_price"].split(",")[0])
                if s["pending_par"]:
                    act("par", actor, price=price)
                else:
                    act("buy_shares", actor, corporation=a["corporation"], price=price)
            elif typ == "buy_shares":
                c = a["shares"][0].rsplit("_", 1)[0]
                source = "pool" if a["shares"][0] in pool else "ipo"
                if s["corporations"][c][source] < a.get("percent", 10):
                    source = "pool" if source == "ipo" else "ipo"
                act(
                    "buy_shares",
                    actor,
                    corporation=c,
                    percent=a.get("percent", 10),
                    source=source,
                )
                pool.difference_update(a["shares"])
            elif typ == "sell_shares":
                if s["round"] == "operating" and not s["operating_turn"]["dividend"]:
                    act("dividend", payout=False)
                c = a["shares"][0].rsplit("_", 1)[0]
                act(
                    "sell_shares" if s["round"] == "stock" else "emergency_sell",
                    actor,
                    corporation=c,
                    percent=a["percent"],
                )
                pool.update(a["shares"])
            elif typ == "lay_tile":
                tile = a["tile"].split("-")[0]
                kw = {}
                if a["entity_type"] == "company":
                    kw["special"] = entity
                act(
                    "lay_tile",
                    actor,
                    hex=a["hex"],
                    tile=tile,
                    rotation=a["rotation"],
                    **kw,
                )
                tile_ids[a["tile"]] = a["hex"]
            elif typ == "place_token":
                tile, index = a["city"].rsplit("-", 1)
                h = tile_ids.get(tile)
                if not h:
                    h = tile.rsplit("-", 1)[0]
                    if h not in s["board"]:
                        raise RuntimeError("Unknown token city " + tile)
                home = not s["corporations"][cid]["home_placed"]
                act(
                    "home_token" if home else "place_token",
                    actor,
                    hex=h,
                    city=int(index),
                )
            elif typ == "run_routes":
                act(
                    "run_routes",
                    actor,
                    routes=[convert_route(s, cid, r) for r in a["routes"]],
                )
            elif typ == "dividend":
                act("dividend", actor, payout=a["kind"] == "payout")
            elif typ == "buy_train":
                if not s["operating_turn"]["dividend"]:
                    act("dividend", payout=False)
                seller = s["trains"][a["train"]]["owner"]
                if (
                    seller != "depot"
                    and s["corporations"][seller]["president"] != actor
                ):
                    act(
                        "offer",
                        s["corporations"][seller]["president"],
                        kind="train",
                        item=a["train"],
                        seller=seller,
                        buyer=cid,
                        price=a["price"],
                    )
                kw = {}
                if a.get("exchange"):
                    kw["trade_in"] = a["exchange"]
                act("buy_train", actor, train=a["train"], price=a["price"], **kw)
            elif typ == "buy_company":
                seller = s["privates"][a["company"]]["owner"]
                if seller != actor:
                    act(
                        "offer",
                        seller,
                        kind="private",
                        item=a["company"],
                        seller=seller,
                        buyer=cid or actor,
                        price=a["price"],
                    )
                act(
                    "buy_private",
                    actor,
                    company=a["company"],
                    buyer=cid or actor,
                    price=a["price"],
                )
            elif typ == "discard_train":
                act("discard_train", actor, corporation=cid, train=a["train"])
            elif typ == "bankrupt":
                if not s["operating_turn"]["dividend"]:
                    act("dividend", payout=False)
                act("bankrupt", actor)
            else:
                raise RuntimeError("Unhandled type " + typ)
            last = a
        except Exception:
            print(
                "ORDER",
                s["or_order"],
                s["or_index"],
                s["or_number"],
                [
                    (c["id"], c["position"], c["market_order"])
                    for c in s["corporations"].values()
                ],
            )
            print(
                "FAILED reference index",
                index,
                "action",
                a,
                "\nstate:",
                s["round"],
                s["current_player"],
                s["current_corporation"],
                s["phase"],
                s["operating_turn"],
                "\nprevious:",
                last,
            )
            raise
    if not s["finished"]:
        finish()
    print("Finished", s["finished"], s["result"], "expected", d["result"])
    if s["result"] != d["result"]:
        print("CASH", [(p, x["cash"]) for p, x in s["players"].items()])
        print(
            "STOCK",
            [(c["id"], E.price(c), c["holdings"]) for c in s["corporations"].values()],
        )
    if not s["finished"] or s["result"] != d["result"]:
        raise AssertionError("Recording did not reproduce its independent result")
    if s["finished"] and s["result"] == d["result"]:
        destination = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "unittests"
            / "fixtures"
            / Path(path).name
        )
        with destination.open("w") as f:
            json.dump(
                {
                    "source": "tobymao/18xx",
                    "revision": "46a592e40494368390c9a731978a577ac4ecb1e0",
                    "names": [p["name"] for p in d["players"]],
                    "player_ids": [str(p["id"]) for p in d["players"]],
                    "actions": s["history"],
                    "result": s["result"],
                    "end_reason": s["end_reason"],
                },
                f,
                separators=(",", ":"),
            )
            f.write("\n")
    return s


if __name__ == "__main__":
    run(sys.argv[1])
