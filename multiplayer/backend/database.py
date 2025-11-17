"""
Database models and operations for multiplayer 18xx game
"""
import aiosqlite
import json
import secrets
import string
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


DB_PATH = Path(__file__).parent / "game.db"


def generate_token(length: int = 32) -> str:
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_room_code(length: int = 6) -> str:
    """Generate a room code (alphanumeric, uppercase)"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Database:
    """Database manager for game persistence"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Create database tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            # Games table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT UNIQUE NOT NULL,
                    variant TEXT NOT NULL,
                    status TEXT NOT NULL,
                    creator_token TEXT NOT NULL,
                    spectator_token TEXT NOT NULL,
                    max_players INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Players table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    player_token TEXT UNIQUE NOT NULL,
                    player_order INTEGER,
                    is_spectator BOOLEAN DEFAULT 0,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )
            """)

            # Game states table (for move history and persistence)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    move_number INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )
            """)

            await db.commit()

    async def create_game(
        self,
        variant: str = "1889",
        max_players: int = 6
    ) -> Dict[str, Any]:
        """Create a new game and return game info with tokens"""
        room_code = generate_room_code()
        creator_token = generate_token()
        spectator_token = generate_token()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO games (room_code, variant, status, creator_token, spectator_token, max_players)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (room_code, variant, "waiting", creator_token, spectator_token, max_players))

            game_id = cursor.lastrowid

            # Generate and pre-register player tokens
            player_tokens = []
            for i in range(max_players):
                token = generate_token()
                player_tokens.append(token)

                # Pre-create player records with tokens (no name yet = pending)
                await db.execute("""
                    INSERT INTO players (game_id, player_name, player_token, player_order, is_spectator)
                    VALUES (?, ?, ?, ?, ?)
                """, (game_id, f"Player {i+1} (pending)", token, i, 0))

            await db.commit()

        return {
            "game_id": game_id,
            "room_code": room_code,
            "creator_token": creator_token,
            "spectator_token": spectator_token,
            "player_tokens": player_tokens,
            "variant": variant,
            "max_players": max_players
        }

    async def get_game_by_room_code(self, room_code: str) -> Optional[Dict[str, Any]]:
        """Get game info by room code"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM games WHERE room_code = ?
            """, (room_code,))
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def get_game_by_id(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get game info by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM games WHERE id = ?
            """, (game_id,))
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def update_player_name(
        self,
        player_token: str,
        player_name: str
    ) -> bool:
        """Update a player's name (when they join with a pre-registered token)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE players
                SET player_name = ?, last_seen_at = CURRENT_TIMESTAMP
                WHERE player_token = ?
            """, (player_name, player_token))
            await db.commit()
            return True

    async def add_player(
        self,
        game_id: int,
        player_name: str,
        player_token: str,
        is_spectator: bool = False
    ) -> int:
        """Add a player to a game (for spectators or additional players)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current player count to assign order
            cursor = await db.execute("""
                SELECT COUNT(*) FROM players
                WHERE game_id = ? AND is_spectator = 0
            """, (game_id,))
            count = (await cursor.fetchone())[0]

            player_order = None if is_spectator else count

            cursor = await db.execute("""
                INSERT INTO players (game_id, player_name, player_token, player_order, is_spectator)
                VALUES (?, ?, ?, ?, ?)
            """, (game_id, player_name, player_token, player_order, is_spectator))

            player_id = cursor.lastrowid
            await db.commit()
            return player_id

    async def get_player_by_token(self, player_token: str) -> Optional[Dict[str, Any]]:
        """Get player info by token"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM players WHERE player_token = ?
            """, (player_token,))
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def get_players_in_game(self, game_id: int) -> List[Dict[str, Any]]:
        """Get all players in a game"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM players
                WHERE game_id = ?
                ORDER BY is_spectator, player_order
            """, (game_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_player_last_seen(self, player_token: str):
        """Update player's last seen timestamp"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE players
                SET last_seen_at = CURRENT_TIMESTAMP
                WHERE player_token = ?
            """, (player_token,))
            await db.commit()

    async def save_game_state(self, game_id: int, state_json: str, move_number: int):
        """Save a game state snapshot"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO game_states (game_id, state_json, move_number)
                VALUES (?, ?, ?)
            """, (game_id, state_json, move_number))

            # Update game's updated_at timestamp
            await db.execute("""
                UPDATE games
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (game_id,))

            await db.commit()

    async def get_latest_game_state(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent game state"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM game_states
                WHERE game_id = ?
                ORDER BY move_number DESC
                LIMIT 1
            """, (game_id,))
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def update_game_status(self, game_id: int, status: str):
        """Update game status (waiting, in_progress, completed)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE games
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, game_id))
            await db.commit()

    async def verify_token(self, game_id: int, token: str) -> Dict[str, Any]:
        """Verify a token and return its type and associated info"""
        game = await self.get_game_by_id(game_id)

        if not game:
            return {"valid": False, "error": "Game not found"}

        # Check if it's creator token
        if token == game["creator_token"]:
            return {"valid": True, "type": "creator", "game": game}

        # Check if it's spectator token
        if token == game["spectator_token"]:
            return {"valid": True, "type": "spectator", "game": game}

        # Check if it's a player token
        player = await self.get_player_by_token(token)
        if player and player["game_id"] == game_id:
            return {"valid": True, "type": "player", "player": player, "game": game}

        return {"valid": False, "error": "Invalid token"}


# Global database instance
db = Database()
