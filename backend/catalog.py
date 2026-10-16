"""Add consistent client metadata without replacing the original catalog fields."""

from copy import deepcopy
from importlib import import_module


def catalog(variant):
    data = import_module("app.engine" + variant + ".data")
    board = import_module("app.engine" + variant + ".board")
    return dict(
        deepcopy(data.BOARD_DATA),
        variant=variant,
        contract_version=1,
        action_schema_url="/api/" + variant + "/schema",
        currency="USD" if variant == "1830" else "JPY",
        layout="pointy" if variant == "1830" else "flat",
        edge_deltas=deepcopy(board.DELTAS),
        market=deepcopy(data.MARKET),
        par_prices=list(data.PAR_PRICES),
        corporations=deepcopy(data.CORPORATIONS),
        privates=deepcopy(data.PRIVATES),
        certificate_limits=dict(data.CERT_LIMITS),
        train_types=deepcopy(data.TRAIN_TYPES),
        phases=deepcopy(data.PHASES),
        rusts=dict(data.RUSTS),
        upgrades=deepcopy(data.UPGRADES),
        board=board.initial_board(),
        tile_geometry={tid: board.tile_for(tid, 0) for tid in data.BOARD_DATA["tiles"]},
        components={
            "corporations": {
                cid: dict(name=values[0], home=values[1], token_supply=values[2])
                for cid, values in data.CORPORATIONS.items()
            },
            "privates": {
                pid: dict(
                    name=values[0],
                    value=values[1],
                    revenue=values[2],
                    blocked_hexes=list(values[3]),
                )
                for pid, values in data.PRIVATES.items()
            },
            "train_types": {
                kind: dict(
                    initial_count=values[0],
                    price=values[1],
                    stops=values[2],
                    unlimited=variant == "1889" and kind == "D",
                )
                for kind, values in data.TRAIN_TYPES.items()
            },
            "phases": {
                phase: dict(
                    train_limit=values[0],
                    tile_colors=list(values[1]),
                    operating_rounds=values[2],
                )
                for phase, values in data.PHASES.items()
            },
        },
    )
