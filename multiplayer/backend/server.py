"""
Multiplayer WebSocket server for Daemon18xx
FastAPI + Socket.IO implementation
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import socketio

from database import db
from game_serializer import serialize_game, deserialize_game, serialize_game_state_only
from app.state import Game
from app.minigames.PrivateCompanyInitialAuction.move import BuyPrivateCompanyMove
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.operating_round import OperatingRoundMove

# Initialize FastAPI
app = FastAPI(title="Daemon18xx Multiplayer Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local network, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Socket.IO
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Wrap with ASGI app
socket_app = socketio.ASGIApp(sio, app)

# In-memory game state cache (keyed by game_id)
game_states: Dict[int, Game] = {}

# Track connected clients (keyed by session_id)
connected_clients: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await db.initialize()
    print("✅ Database initialized")
    print(f"✅ Server starting on http://0.0.0.0:8000")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Daemon18xx Multiplayer Server"}


@app.post("/api/games/create")
async def create_game(max_players: int = 6):
    """Create a new game room"""
    try:
        game_info = await db.create_game(variant="1889", max_players=max_players)

        # Initialize game state
        game_id = game_info["game_id"]

        return {
            "success": True,
            "game_id": game_id,
            "room_code": game_info["room_code"],
            "creator_url": f"/game/{game_info['room_code']}/play?token={game_info['creator_token']}",
            "spectator_url": f"/game/{game_info['room_code']}/spectate?token={game_info['spectator_token']}",
            "player_urls": [
                f"/game/{game_info['room_code']}/play?token={token}"
                for token in game_info['player_tokens']
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/{room_code}")
async def get_game_info(room_code: str):
    """Get game information by room code"""
    game = await db.get_game_by_room_code(room_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = await db.get_players_in_game(game["id"])

    return {
        "game": game,
        "players": players
    }


# ============================================================================
# Socket.IO Event Handlers
# ============================================================================

@sio.event
async def connect(sid, environ):
    """Client connected"""
    print(f"🔌 Client connected: {sid}")
    connected_clients[sid] = {"authenticated": False}


@sio.event
async def disconnect(sid):
    """Client disconnected"""
    print(f"🔌 Client disconnected: {sid}")
    if sid in connected_clients:
        client = connected_clients[sid]
        if "player_token" in client:
            # Update last seen
            await db.update_player_last_seen(client["player_token"])
        del connected_clients[sid]


@sio.event
async def authenticate(sid, data):
    """
    Authenticate a client with their token
    Expected data: {"room_code": "ABC123", "token": "..."}
    """
    try:
        room_code = data.get("room_code")
        token = data.get("token")

        if not room_code or not token:
            await sio.emit("error", {"message": "Missing room_code or token"}, room=sid)
            return

        # Get game
        game = await db.get_game_by_room_code(room_code)
        if not game:
            await sio.emit("error", {"message": "Game not found"}, room=sid)
            return

        # Verify token
        auth_result = await db.verify_token(game["id"], token)

        if not auth_result["valid"]:
            await sio.emit("error", {"message": "Invalid token"}, room=sid)
            return

        # Store authentication info
        connected_clients[sid]["authenticated"] = True
        connected_clients[sid]["game_id"] = game["id"]
        connected_clients[sid]["room_code"] = room_code
        connected_clients[sid]["token"] = token
        connected_clients[sid]["auth_type"] = auth_result["type"]

        # Join room for broadcasts
        await sio.enter_room(sid, room_code)

        # If player, store player info
        if auth_result["type"] == "player":
            player = auth_result["player"]
            connected_clients[sid]["player_id"] = player["id"]
            connected_clients[sid]["player_name"] = player["player_name"]
            connected_clients[sid]["player_token"] = player["player_token"]
            await db.update_player_last_seen(player["player_token"])

        # Send authentication success
        auth_response = {
            "success": True,
            "auth_type": auth_result["type"],
            "game": game
        }

        # Include player info if player
        if auth_result["type"] == "player":
            player = auth_result["player"]
            auth_response["player"] = {
                "id": player["id"],
                "name": player["player_name"],
                "has_name": not player["player_name"].endswith("(pending)")
            }

        await sio.emit("authenticated", auth_response, room=sid)

        # Send current game state if exists
        if game["id"] in game_states:
            await send_game_state(sid, game["id"])

        # Notify room of new connection
        await sio.emit("player_connected", {
            "auth_type": auth_result["type"],
            "player_name": connected_clients[sid].get("player_name", "Spectator")
        }, room=room_code, skip_sid=sid)

        print(f"✅ Authenticated {auth_result['type']}: {sid}")

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def join_game(sid, data):
    """
    Set player name (players are pre-registered with tokens)
    Expected data: {"player_name": "Alice"}
    """
    try:
        if sid not in connected_clients or not connected_clients[sid].get("authenticated"):
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return

        client = connected_clients[sid]

        # Only players can set names (not creator or spectator)
        if client["auth_type"] != "player":
            await sio.emit("error", {"message": "Only players can set names"}, room=sid)
            return

        game_id = client["game_id"]
        player_name = data.get("player_name")
        token = client["token"]

        if not player_name or not player_name.strip():
            await sio.emit("error", {"message": "Player name required"}, room=sid)
            return

        # Check if name already set (not pending)
        player = await db.get_player_by_token(token)
        if player and not player["player_name"].endswith("(pending)"):
            # Name already set, just update it
            pass

        # Update player name in database
        await db.update_player_name(token, player_name.strip())

        # Update client info
        connected_clients[sid]["player_name"] = player_name.strip()

        # Refresh player info
        player = await db.get_player_by_token(token)
        if player:
            connected_clients[sid]["player_id"] = player["id"]

        # Get updated player list
        players = await db.get_players_in_game(game_id)

        # Broadcast to room
        await sio.emit("player_joined", {
            "player_name": player_name.strip(),
            "players": players
        }, room=client["room_code"])

        print(f"✅ Player set name: {player_name}")

    except Exception as e:
        print(f"❌ Join game error: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def start_game(sid, data):
    """
    Start the game (only creator can do this)
    Expected data: {"player_names": ["Alice", "Bob", "Carol"]}
    """
    try:
        if sid not in connected_clients or not connected_clients[sid].get("authenticated"):
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return

        client = connected_clients[sid]

        # Only creator can start
        if client["auth_type"] != "creator":
            await sio.emit("error", {"message": "Only creator can start game"}, room=sid)
            return

        game_id = client["game_id"]
        player_names = data.get("player_names", [])

        if not player_names or len(player_names) < 3:
            await sio.emit("error", {"message": "Need at least 3 players"}, room=sid)
            return

        # Initialize game with Daemon18xx engine
        game = Game.start(player_names, variant="1889")

        # Filter private companies based on player count (1889 rules)
        # 3 players=5 companies, 4 players=6 companies, 5-6 players=7 companies
        player_count = len(player_names)
        all_privates = game.state.private_companies
        sorted_privates = sorted(all_privates, key=lambda pc: pc.cost)

        if player_count == 3:
            game.state.private_companies = sorted_privates[:5]
        elif player_count == 4:
            game.state.private_companies = sorted_privates[:6]
        else:
            game.state.private_companies = sorted_privates

        # Initialize player order for the first phase
        game.setPlayerOrder()
        game.setCurrentPlayer()

        game_states[game_id] = game

        # Save initial state (using custom serialization)
        game_serialized = serialize_game(game)
        await db.save_game_state(game_id, game_serialized, 0)
        await db.update_game_status(game_id, "in_progress")

        # Broadcast to all in room
        await sio.emit("game_started", {
            "game_state": serialize_game_state(game),
            "players": player_names
        }, room=client["room_code"])

        print(f"✅ Game started: {game_id}")

    except Exception as e:
        print(f"❌ Start game error: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def make_move(sid, data):
    """
    Make a game move
    Expected data: {"move_type": "...", "move_data": {...}}
    """
    try:
        if sid not in connected_clients or not connected_clients[sid].get("authenticated"):
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return

        client = connected_clients[sid]

        # Spectators can't make moves
        if client["auth_type"] == "spectator":
            await sio.emit("error", {"message": "Spectators cannot make moves"}, room=sid)
            return

        game_id = client["game_id"]

        if game_id not in game_states:
            await sio.emit("error", {"message": "Game not started"}, room=sid)
            return

        game = game_states[game_id]
        move_type = data.get("move_type")
        move_data = data.get("move_data")

        # Construct move object based on type
        move = construct_move(move_type, move_data)

        if not move:
            await sio.emit("error", {"message": "Invalid move"}, room=sid)
            return

        # For BuyPrivateCompany phase, set current_player from priority_deal_player
        # since the player order system isn't used for this phase
        if game.minigame_class == "BuyPrivateCompany":
            if hasattr(game.state, 'priority_deal_player') and game.state.priority_deal_player:
                game.current_player = game.state.priority_deal_player

        # Apply move to game state
        from app.state import apply_move
        new_game = apply_move(game, move)

        # Update game state
        game_states[game_id] = new_game

        # Save to database (using custom serialization)
        move_number = getattr(new_game, 'move_count', 0)
        game_serialized = serialize_game(new_game)
        await db.save_game_state(game_id, game_serialized, move_number)

        # Broadcast updated state to all clients
        await sio.emit("game_state_update", {
            "game_state": serialize_game_state(new_game)
        }, room=client["room_code"])

        # Broadcast action to ticker
        await sio.emit("player_action", {
            "player_name": client.get("player_name", "Unknown"),
            "action": format_action(move_type, move_data),
            "timestamp": datetime.now().isoformat()
        }, room=client["room_code"])

        print(f"✅ Move applied: {move_type}")

    except Exception as e:
        print(f"❌ Make move error: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def request_game_state(sid):
    """Request current game state"""
    try:
        if sid not in connected_clients or not connected_clients[sid].get("authenticated"):
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return

        client = connected_clients[sid]
        game_id = client["game_id"]

        await send_game_state(sid, game_id)

    except Exception as e:
        print(f"❌ Request game state error: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# Helper Functions
# ============================================================================

async def send_game_state(sid: str, game_id: int):
    """Send current game state to a client"""
    if game_id in game_states:
        game = game_states[game_id]
        await sio.emit("game_state_update", {
            "game_state": serialize_game_state(game)
        }, room=sid)
    else:
        # Try to load from database
        state_record = await db.get_latest_game_state(game_id)
        if state_record:
            # Deserialize using custom deserialization
            game = deserialize_game(state_record["state_json"])

            # Ensure player order is initialized if missing
            if not game.player_order_fn_list:
                game.setPlayerOrder()
                if hasattr(game, 'state') and hasattr(game.state, 'priority_deal_player') and game.state.priority_deal_player:
                    game.current_player = game.state.priority_deal_player

            game_states[game_id] = game
            await sio.emit("game_state_update", {
                "game_state": serialize_game_state(game)
            }, room=sid)


def serialize_game_state(game: Game) -> Dict[str, Any]:
    """Serialize game state for transmission (wrapper for game_serializer)"""
    return serialize_game_state_only(game)


def construct_move(move_type: str, move_data: Dict[str, Any]):
    """Construct a Move object from type and data"""
    # Create base Move object with msg field
    from app.base import Move

    if move_type == "BuyPrivateCompanyMove":
        base_move = Move()
        base_move.msg = json.dumps(move_data)
        base_move.player_id = move_data.get('player_id')
        return BuyPrivateCompanyMove.fromMove(base_move)
    elif move_type == "StockRoundMove":
        base_move = Move()
        base_move.msg = json.dumps(move_data)
        base_move.player_id = move_data.get('player_id')
        return StockRoundMove.fromMove(base_move)
    elif move_type == "OperatingRoundMove":
        base_move = Move()
        base_move.msg = json.dumps(move_data)
        base_move.player_id = move_data.get('player_id')
        return OperatingRoundMove.fromMove(base_move)
    return None


def format_action(move_type: str, move_data: Dict[str, Any]) -> str:
    """Format a move as a human-readable action for the ticker"""
    # Simplified formatting
    if move_type == "buy_private":
        return f"Bought private company for ${move_data.get('amount', 0)}"
    elif move_type == "stock_round":
        action = move_data.get('action', 'unknown')
        return f"Stock action: {action}"
    return f"Made move: {move_type}"


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
