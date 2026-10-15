"""
Database models and operations for multiplayer 18xx game
"""

import aiosqlite
import os
import json
import secrets
import string
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

DB_PATH = Path(os.environ.get("DAEMON18XX_DATABASE", "data/games.sqlite3"))


def generate_token(length: int = 32) -> str:
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_room_code(length: int = 6) -> str:
    """Generate a room code (alphanumeric, uppercase)"""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Database:
    """Database manager for game persistence"""

    def __init__(self, db_path: Path = DB_PATH, lock_timeout: float = 5.0):
        self.db_path = db_path
        self.lock_timeout = lock_timeout

    async def initialize(self):
        """Create database tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            # Games table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT UNIQUE NOT NULL,
                    variant TEXT NOT NULL,
                    engine TEXT NOT NULL DEFAULT 'legacy',
                    status TEXT NOT NULL,
                    creator_token TEXT NOT NULL,
                    spectator_token TEXT NOT NULL,
                    max_players INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            columns = await (await db.execute("PRAGMA table_info(games)")).fetchall()
            if "engine" not in [column[1] for column in columns]:
                await db.execute(
                    "ALTER TABLE games ADD COLUMN engine TEXT NOT NULL DEFAULT 'legacy'"
                )

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
        self, variant: str = "1889", max_players: int = 6, engine: str = "python"
    ) -> Dict[str, Any]:
        """Allocate a room and globally distinct credentials atomically.

        Retry collisions five times. BEGIN IMMEDIATE also protects credential
        uniqueness across concurrent creators; failed slot inserts roll back the
        entire attempt. Exhaustion/busy errors expose no partial credentials.
        """
        for attempt in range(5):
            room_code = generate_room_code()
            credentials = [generate_token() for _ in range(max_players + 2)]
            if len(set(credentials)) != len(credentials):
                continue
            async with aiosqlite.connect(
                self.db_path, timeout=self.lock_timeout
            ) as connection:
                try:
                    await connection.execute("BEGIN IMMEDIATE")
                    marks = ",".join("?" for _ in credentials)
                    cursor = await connection.execute(
                        "SELECT 1 FROM games WHERE creator_token IN ("
                        + marks
                        + ") OR spectator_token IN ("
                        + marks
                        + ") UNION ALL "
                        "SELECT 1 FROM players WHERE player_token IN ("
                        + marks
                        + ") LIMIT 1",
                        credentials * 3,
                    )
                    if await cursor.fetchone():
                        await connection.rollback()
                        continue
                    creator_token, spectator_token = credentials[:2]
                    player_tokens = credentials[2:]
                    cursor = await connection.execute(
                        "INSERT INTO games (room_code, variant, status, creator_token, spectator_token, max_players, engine) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            room_code,
                            variant,
                            "waiting",
                            creator_token,
                            spectator_token,
                            max_players,
                            engine,
                        ),
                    )
                    game_id = cursor.lastrowid
                    for i, token in enumerate(player_tokens):
                        await connection.execute(
                            "INSERT INTO players (game_id, player_name, player_token, player_order, is_spectator) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (game_id, "Player %d (pending)" % (i + 1), token, i, 0),
                        )
                    await connection.commit()
                    return dict(
                        game_id=game_id,
                        room_code=room_code,
                        creator_token=creator_token,
                        spectator_token=spectator_token,
                        player_tokens=player_tokens,
                        variant=variant,
                        max_players=max_players,
                    )
                except aiosqlite.IntegrityError:
                    await connection.rollback()
                except aiosqlite.OperationalError as error:
                    await connection.rollback()
                    if "locked" in str(error).lower() or "busy" in str(error).lower():
                        raise ValueError(
                            "Database busy; retry after the writer completes"
                        ) from error
                    raise
        raise ValueError("Unable to allocate unique room credentials; retry creation")

    async def get_game_by_room_code(self, room_code: str) -> Optional[Dict[str, Any]]:
        """Get game info by room code"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM games WHERE room_code = ?
            """,
                (room_code,),
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def get_game_by_id(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get game info by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM games WHERE id = ?
            """,
                (game_id,),
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def get_player_by_token(self, player_token: str) -> Optional[Dict[str, Any]]:
        """Get player info by token"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM players WHERE player_token = ?
            """,
                (player_token,),
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def get_latest_game_state(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get the most recent game state"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM game_states
                WHERE game_id = ?
                ORDER BY move_number DESC
                LIMIT 1
            """,
                (game_id,),
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)
            return None

    async def save_rules_state(
        self, game_id: int, state: dict, expected_version: Optional[int]
    ):
        """Compare and append a JSON rules state in one SQLite transaction.

        BEGIN IMMEDIATE serializes writers across processes, not just coroutines.
        Rejected/stale actions never become snapshots or overwrite accepted moves.
        """
        try:
            async with aiosqlite.connect(
                self.db_path, timeout=self.lock_timeout
            ) as connection:
                await connection.execute("BEGIN IMMEDIATE")
                cursor = await connection.execute(
                    "SELECT move_number FROM game_states WHERE game_id = ? ORDER BY move_number DESC, id DESC LIMIT 1",
                    (game_id,),
                )
                latest = await cursor.fetchone()
                actual = latest[0] if latest else None
                if actual != expected_version:
                    await connection.rollback()
                    raise ValueError(
                        "State changed; reload before submitting another action"
                    )
                await connection.execute(
                    "INSERT INTO game_states (game_id,state_json,move_number) VALUES (?,?,?)",
                    (
                        game_id,
                        json.dumps(state, separators=(",", ":")),
                        state["revision"],
                    ),
                )
                await connection.execute(
                    "UPDATE games SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    ("completed" if state["finished"] else "in_progress", game_id),
                )
                await connection.commit()
        except aiosqlite.OperationalError as error:
            if "locked" in str(error).lower() or "busy" in str(error).lower():
                raise ValueError(
                    "Database busy; reload and retry after the writer completes"
                ) from error
            raise

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
