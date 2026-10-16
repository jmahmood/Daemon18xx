"""Public JSON Schemas for action payloads; game-state validation stays in the engines."""

from copy import deepcopy
from backend.errors import ERROR_CODES


def string(description, **constraints):
    return dict(type="string", description=description, **constraints)


def integer(description, minimum=0, **constraints):
    return dict(type="integer", description=description, minimum=minimum, **constraints)


def action_schema(variant):
    """Describe canonical actions and accepted aliases without changing execution."""
    corporation = string("Corporation ID from catalog.components.corporations")
    company = string("Private company ID from catalog.components.privates")
    price = integer("Whole currency units; legal price depends on current state")
    percent = integer("Share percentage", 10, maximum=100, multipleOf=10)
    train = string("Physical train ID from state.trains, e.g. 2-0")
    source = string("Share source", enum=["ipo", "pool"], default="ipo")
    route = {
        "type": "object",
        "required": ["train"],
        "properties": {
            "train": train,
            "vertices": {"type": "array", "items": {"type": "string"}},
            "paths": {
                "type": "array",
                "items": {
                    "type": "array",
                    "prefixItems": [
                        {"type": "string"},
                        {"type": "integer", "minimum": 0},
                    ],
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
        },
        "anyOf": [{"required": ["vertices"]}, {"required": ["paths"]}],
    }
    definitions = []

    def add(name, description, fields=None, required=(), aliases=(), example=None):
        definitions.append(
            {
                "title": name,
                "description": description,
                "type": "object",
                "required": ["type", *required],
                "properties": {
                    "type": {"type": "string", "enum": [name, *aliases]},
                    "player": string(
                        "Optional; bound to the authenticated seat by the server"
                    ),
                    **(fields or {}),
                },
                "additionalProperties": True,
                "examples": [dict(type=name, **(example or {}))],
            }
        )

    add(
        "buy_private",
        "Buy the offered auction private; outside auction, negotiated price and consent are required. Buyer defaults to the actor.",
        dict(
            company=company, price=price, buyer=string("Buying player/corporation ID")
        ),
        ("company",),
        example=dict(company="SV" if variant == "1830" else "TR"),
    )
    add(
        "bid",
        "Bid in the private auction; cash is escrowed.",
        dict(company=company, price=price),
        ("company", "price"),
        example=dict(
            company="CS" if variant == "1830" else "MF",
            price=45 if variant == "1830" else 35,
        ),
    )
    add("pass", "Pass/withdraw in auction or stock; decline an 1889 ER interrupt.")
    add(
        "buy_shares",
        "Buy once per stock turn. A new presidency needs a legal par price via price (or alias par).",
        dict(
            corporation=corporation,
            source=source,
            percent=percent,
            price=price,
            par=price,
        ),
        ("corporation",),
        example=dict(
            corporation="PRR" if variant == "1830" else "AR",
            price=67 if variant == "1830" else 65,
        ),
    )
    for name in ("sell_shares", "emergency_sell"):
        add(
            name,
            "Sell shares; emergency_sell is restricted to required train funding.",
            dict(corporation=corporation, percent=percent),
            ("corporation", "percent"),
            example=dict(corporation="PRR" if variant == "1830" else "AR", percent=10),
        )
    add("end_turn", "End a stock or operating turn after mandatory steps.")
    tile_fields = dict(
        hex=string("Map coordinate"),
        tile=string("Base tile ID"),
        rotation=integer(
            "Rotation adds to edge numbers modulo six", maximum=5, default=0
        ),
        special=string(
            "Optional private power",
            enum=["CS", "DH"] if variant == "1830" else ["MF", "ER"],
        ),
    )
    if variant == "1830":
        tile_fields["place_token"] = {
            "type": "boolean",
            "description": "DH free station option",
        }
    add(
        "lay_tile",
        "Lay/upgrade track or exercise the identified private power.",
        tile_fields,
        ("hex", "tile"),
        example=dict(hex="G7" if variant == "1830" else "I4", tile="7", rotation=0),
    )
    add(
        "place_token",
        "Place a station in a reachable city with an available slot.",
        dict(hex=string("Map coordinate"), city=integer("City node index", default=0)),
        ("hex",),
        example=dict(hex="F6" if variant == "1830" else "I2", city=0),
    )
    add(
        "skip",
        "Skip optional track/token placement; routes only when no train can run.",
    )
    add(
        "run_routes",
        "Submit legal routes. Revenue is computed by the engine; the player chooses routes.",
        {"routes": {"type": "array", "items": route}},
        ("routes",),
        example=dict(routes=[]),
    )
    add(
        "dividend",
        "Pay or withhold computed revenue. Prefer payout; kind is a compatibility alias.",
        {
            "payout": {"type": "boolean"},
            "kind": string("Compatibility alias", enum=["payout", "withhold"]),
        },
        example=dict(payout=True),
    )
    definitions[-1]["anyOf"] = [{"required": ["payout"]}, {"required": ["kind"]}]
    add(
        "buy_train",
        "Buy a depot or corporate train, subject to funding, phase and consent rules.",
        dict(train=train, price=price, trade_in=train),
        ("train",),
        example=dict(train="2-0"),
    )
    add(
        "discard_train",
        "Resolve an excess-train interrupt as the affected corporation's president.",
        dict(corporation=corporation, train=train),
        ("corporation", "train"),
        example=dict(corporation="PRR" if variant == "1830" else "AR", train="2-0"),
    )
    add(
        "bankrupt",
        "Declare bankruptcy only when required train funding is impossible.",
        aliases=("bankruptcy",),
    )
    exchange_source = dict(source) if variant == "1830" else dict(source, enum=["ipo"])
    add(
        "exchange_private",
        "Exchange M&H in 1830 or DR in 1889; permitted out-of-turn windows still require validation.",
        dict(source=exchange_source),
        aliases=("exchange_mh" if variant == "1830" else "exchange_dr",),
        example=dict(source="ipo"),
    )
    add(
        "offer",
        "Record consent from one transaction party; the other accepts with a matching purchase.",
        dict(
            kind=string("Item category", enum=["private", "train"]),
            item=string("Item ID"),
            seller=string("Owning player/corporation ID"),
            buyer=string("Buying player/corporation ID"),
            price=price,
        ),
        ("kind", "item", "seller", "buyer", "price"),
        example=dict(
            kind="train",
            item="2-0",
            seller="PRR" if variant == "1830" else "AR",
            buyer="NYC" if variant == "1830" else "IR",
            price=80,
        ),
    )
    if variant == "1830":
        add(
            "par",
            "Resolve the B&O gift recipient's required par choice.",
            dict(price=price),
            ("price",),
            example=dict(price=67),
        )
        add(
            "home_token",
            "Choose Erie's home city.",
            dict(city=integer("Home city node index", maximum=1, default=0)),
            example=dict(city=0),
        )
    else:
        add(
            "run_best_routes",
            "Existing exact automatic route allocation; potentially expensive. Manual run_routes remains available.",
        )
    return {
        "oneOf": definitions,
        "description": "Parameter schemas are independent of game state. Examples show structure, not necessarily currently legal moves. Discovery is advisory; the rules engine validates every action.",
    }


def action_contract(variant):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Daemon18xx " + variant + " action request",
        "x-contract-version": 1,
        "x-error-codes": dict(ERROR_CODES),
        "type": "object",
        "required": ["expected_action_id", "action"],
        "properties": {
            "expected_action_id": integer("Current state.revision"),
            "action": deepcopy(action_schema(variant)),
        },
    }
