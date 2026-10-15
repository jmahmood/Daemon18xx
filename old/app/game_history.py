"""Game history tracking and export functionality.

This module provides tools for recording, exporting, and replaying game moves.
Useful for debugging, analysis, and implementing undo/redo functionality.

Usage:
    from app.game_history import GameHistory

    # Create history tracker
    history = GameHistory()

    # Record moves as they happen
    history.record_move(move, state, success=True)

    # Export to JSON
    history.export_json("game_history.json")

    # Replay moves (future enhancement)
    # replay_game(history.moves)
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict

from app.base import Move, MutableGameState, Player, PublicCompany, PrivateCompany


class GameHistory:
    """Tracks all moves in a game for export and replay."""

    def __init__(self):
        """Initialize empty game history."""
        self.moves: List[Dict[str, Any]] = []
        self.game_start_time: Optional[str] = None
        self.variant: Optional[str] = None
        self.players: List[str] = []

    def initialize(self, variant: str, players: List[str]) -> None:
        """Initialize history with game metadata.

        Args:
            variant: Game variant (e.g., "1830", "1846")
            players: List of player names
        """
        self.game_start_time = datetime.now().isoformat()
        self.variant = variant
        self.players = players

    def record_move(
        self,
        move: Move,
        state: MutableGameState,
        success: bool,
        errors: Optional[List[str]] = None,
        phase: Optional[str] = None
    ) -> None:
        """Record a move in the history.

        Args:
            move: The move that was attempted
            state: Game state after the move
            success: Whether the move succeeded
            errors: List of validation errors (if move failed)
            phase: Current game phase (e.g., "StockRound", "OperatingRound")
        """
        move_record = {
            'sequence': len(self.moves) + 1,
            'timestamp': datetime.now().isoformat(),
            'player_id': move.player_id if hasattr(move, 'player_id') else None,
            'move_type': move.__class__.__name__,
            'phase': phase,
            'success': success,
            'errors': errors if errors else [],
            'move_data': self._serialize_move(move),
            'state_snapshot': self._serialize_state(state) if success else None
        }

        self.moves.append(move_record)

    def _serialize_move(self, move: Move) -> Dict[str, Any]:
        """Serialize a move object to dict.

        Args:
            move: Move object to serialize

        Returns:
            Dictionary representation of the move
        """
        # Get all attributes of the move
        move_dict = {}
        for attr in dir(move):
            if not attr.startswith('_') and not callable(getattr(move, attr)):
                value = getattr(move, attr)
                # Convert complex objects to simple types
                if hasattr(value, '__dict__'):
                    move_dict[attr] = str(value)
                else:
                    move_dict[attr] = value

        return move_dict

    def _serialize_state(self, state: MutableGameState) -> Dict[str, Any]:
        """Serialize game state to dict (lightweight version).

        Args:
            state: Game state to serialize

        Returns:
            Dictionary with key state information
        """
        return {
            'stock_round_count': state.stock_round_count,
            'stock_round_play': state.stock_round_play,
            'stock_round_passed': state.stock_round_passed,
            'players': [
                {
                    'id': p.id,
                    'name': p.name,
                    'cash': p.cash,
                    'order': p.order
                }
                for p in (state.players or [])
            ],
            'public_companies': [
                {
                    'id': c.id,
                    'name': c.name,
                    'cash': c.cash,
                    'president': c.president.id if c.president else None,
                    'floated': c.isFloated(),
                    'stock_price': c.get_current_price() if hasattr(c, 'get_current_price') else 0
                }
                for c in (state.public_companies or [])
            ],
            'private_companies': [
                {
                    'name': pc.name,
                    'owner': pc.belongs_to.id if pc.belongs_to else None,
                    'company_owner': pc.belongs_to_company.id if pc.belongs_to_company else None
                }
                for pc in (state.private_companies or [])
            ]
        }

    def export_json(self, filepath: str, pretty: bool = True) -> None:
        """Export game history to JSON file.

        Args:
            filepath: Path to write JSON file
            pretty: Whether to pretty-print JSON (default True)
        """
        history_data = {
            'metadata': {
                'game_start_time': self.game_start_time,
                'variant': self.variant,
                'players': self.players,
                'total_moves': len(self.moves)
            },
            'moves': self.moves
        }

        with open(filepath, 'w') as f:
            if pretty:
                json.dump(history_data, f, indent=2)
            else:
                json.dump(history_data, f)

    def export_dict(self) -> Dict[str, Any]:
        """Export game history as dictionary.

        Returns:
            Dictionary containing full game history
        """
        return {
            'metadata': {
                'game_start_time': self.game_start_time,
                'variant': self.variant,
                'players': self.players,
                'total_moves': len(self.moves)
            },
            'moves': self.moves
        }

    def get_move_count(self) -> int:
        """Get total number of moves recorded."""
        return len(self.moves)

    def get_moves_by_player(self, player_id: str) -> List[Dict[str, Any]]:
        """Get all moves by a specific player.

        Args:
            player_id: ID of the player

        Returns:
            List of moves made by that player
        """
        return [m for m in self.moves if m.get('player_id') == player_id]

    def get_moves_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Get all moves in a specific game phase.

        Args:
            phase: Phase name (e.g., "StockRound")

        Returns:
            List of moves in that phase
        """
        return [m for m in self.moves if m.get('phase') == phase]

    def get_failed_moves(self) -> List[Dict[str, Any]]:
        """Get all moves that failed validation.

        Returns:
            List of failed moves
        """
        return [m for m in self.moves if not m.get('success', True)]


def load_history_from_json(filepath: str) -> GameHistory:
    """Load game history from JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        GameHistory object populated from file
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    history = GameHistory()
    history.game_start_time = data['metadata']['game_start_time']
    history.variant = data['metadata']['variant']
    history.players = data['metadata']['players']
    history.moves = data['moves']

    return history


# Future: Game replay functionality
# def replay_game(moves: List[Dict[str, Any]], variant: str, players: List[str]) -> Game:
#     """Replay a game from move history."""
#     # This would create a new game and replay all moves
#     # Useful for debugging and testing
#     pass
