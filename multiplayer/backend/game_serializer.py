"""
Custom serialization for Daemon18xx Game objects

The Game object contains module references that can't be pickled.
This module provides safe serialization/deserialization.
"""
import pickle
import base64
from typing import Dict, Any
from pathlib import Path
import sys

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.state import Game
from app.config import load_config


def serialize_game(game: Game) -> str:
    """
    Serialize a Game object to a base64-encoded string.

    This custom serialization handles module objects that can't be pickled.

    Args:
        game: The Game object to serialize

    Returns:
        Base64-encoded string representation
    """
    # Extract serializable data
    serializable_data = {
        'variant': getattr(game, 'variant', '1889'),
        'state': game.state,
        'minigame_class': getattr(game, 'minigame_class', None),
        'minigame': getattr(game, 'minigame', None),
        'player_order_fn_list': getattr(game, 'player_order_fn_list', []),
        'operating_order': getattr(game, 'operating_order', []),
        'current_player': getattr(game, 'current_player', None),
        'errors_list': getattr(game, 'errors_list', []),
    }

    # Pickle the serializable data
    pickled = pickle.dumps(serializable_data)

    # Base64 encode
    return base64.b64encode(pickled).decode('utf-8')


def deserialize_game(serialized: str) -> Game:
    """
    Deserialize a Game object from a base64-encoded string.

    Args:
        serialized: Base64-encoded string representation

    Returns:
        Reconstructed Game object
    """
    # Base64 decode
    pickled = base64.b64decode(serialized)

    # Unpickle the data
    data = pickle.loads(pickled)

    # Reconstruct the Game object
    game = Game()

    # Restore variant and reload config
    variant = data.get('variant', '1889')
    game.variant = variant
    game.config = load_config(variant)

    # Restore other attributes
    game.state = data['state']
    game.minigame_class = data.get('minigame_class')
    game.minigame = data.get('minigame')
    game.player_order_fn_list = data.get('player_order_fn_list', [])
    game.operating_order = data.get('operating_order', [])
    game.current_player = data.get('current_player')
    game.errors_list = data.get('errors_list', [])

    return game


def serialize_game_state_only(game: Game) -> Dict[str, Any]:
    """
    Serialize only the game state for frontend display (not for saving/loading).

    Returns a plain dict that can be JSON serialized.
    """
    return {
        'variant': getattr(game, 'variant', '1889'),
        'phase': type(game.minigame).__name__ if hasattr(game, 'minigame') and game.minigame else 'unknown',
        'current_player': {
            'id': game.current_player.id,
            'name': game.current_player.name,
        } if hasattr(game, 'current_player') and game.current_player else None,
        'players': [
            {
                'id': p.id,
                'name': p.name,
                'cash': p.cash,
                'order': p.order,
            }
            for p in game.state.players
        ] if hasattr(game, 'state') and hasattr(game.state, 'players') else [],
        # Add more fields as needed for frontend
    }
