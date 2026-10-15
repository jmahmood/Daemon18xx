"""Authenticated HTTP adapter for the pure Python 1889 engine.

The server owns credentials and persistence. Engine states contain neither.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.engine1889 import (
    new_game,
    apply_action,
    migrate_state,
    legal_actions,
    RuleError,
)
from app.engine1889.board_data import DATA
from app.engine1889.engine import available_depot, certificate_count, _price
from app.engine1889.data import (
    PHASES,
    MARKET,
    PAR_PRICES,
    CORPORATIONS,
    PRIVATES,
    CERT_LIMITS,
    TRAIN_TYPES,
)
from database import db

router = APIRouter(prefix="/api/1889", tags=["1889"])


class CreateRoom(BaseModel):
    max_players: int = Field(default=3, ge=2, le=6)


class StartGame(BaseModel):
    player_names: List[str]


class SubmitAction(BaseModel):
    expected_action_id: int = Field(ge=0)
    action: Dict[str, Any]


async def authenticate(room_code, authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    game = await db.get_game_by_room_code(room_code)
    if not game or game["variant"] != "1889" or game.get("engine") != "python":
        raise HTTPException(404, "1889 room not found")
    auth = await db.verify_token(game["id"], authorization[7:])
    if not auth["valid"]:
        raise HTTPException(403, "Invalid room token")
    return game, auth


async def load_state(game):
    record = await db.get_latest_game_state(game["id"])
    if not record:
        raise HTTPException(409, "Game has not started")
    try:
        return migrate_state(json.loads(record["state_json"]))
    except RuleError as error:
        raise HTTPException(
            409, "Saved game migration failed: " + str(error)
        ) from error


def view(state, player=None):
    """Return the board, state, and derived prices; credentials never enter state."""
    return {
        "state": state,
        "currency": "JPY",
        "legal_actions": legal_actions(state, player),
        "prices": {cid: _price(c) for cid, c in state["corporations"].items()},
        "certificates": {p: certificate_count(state, p) for p in state["players"]},
        "available_depot_trains": available_depot(state),
        "train_limit": PHASES[state["phase"]][0],
    }


@router.post("/games")
async def create_room(request: CreateRoom):
    info = await db.create_game(
        variant="1889", max_players=request.max_players, engine="python"
    )
    return {
        k: info[k]
        for k in ("room_code", "creator_token", "spectator_token", "player_tokens")
    }


@router.post("/games/{room_code}/start")
async def start(
    room_code: str,
    request: StartGame,
    authorization: Optional[str] = Header(default=None),
):
    game, auth = await authenticate(room_code, authorization)
    if auth["type"] != "creator":
        raise HTTPException(403, "Only the creator may start a game")
    if len(request.player_names) != game["max_players"]:
        raise HTTPException(422, "Provide one name per registered player slot")
    try:
        state = new_game(request.player_names)
        await db.save_rules_state(game["id"], state, None)
    except RuleError as error:
        raise HTTPException(422, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return view(state)


@router.get("/games/{room_code}")
async def get_state(
    room_code: str, authorization: Optional[str] = Header(default=None)
):
    game, auth = await authenticate(room_code, authorization)
    player = (
        "p" + str(auth["player"]["player_order"] + 1)
        if auth["type"] == "player"
        else None
    )
    return view(await load_state(game), player)


@router.post("/games/{room_code}/actions")
async def submit(
    room_code: str,
    request: SubmitAction,
    authorization: Optional[str] = Header(default=None),
):
    game, auth = await authenticate(room_code, authorization)
    if auth["type"] != "player":
        raise HTTPException(403, "Only a player may submit actions")
    actor = "p" + str(auth["player"]["player_order"] + 1)
    action = dict(request.action)
    if "player" in action and action["player"] != actor:
        raise HTTPException(403, "Cannot act as another player")
    action.update(player=actor, expected_action_id=request.expected_action_id)
    state = await load_state(game)
    if request.expected_action_id != state["revision"]:
        raise HTTPException(409, "Stale action version; reload the current state")
    try:
        result = apply_action(state, action)
        await db.save_rules_state(game["id"], result, state["revision"])
    except RuleError as error:
        raise HTTPException(422, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return view(result, actor)


@router.get("/catalog")
async def catalog():
    return dict(
        DATA,
        currency="JPY",
        market=MARKET,
        par_prices=PAR_PRICES,
        corporations=CORPORATIONS,
        privates=PRIVATES,
        certificate_limits=CERT_LIMITS,
        train_types=TRAIN_TYPES,
        phases=PHASES,
    )
