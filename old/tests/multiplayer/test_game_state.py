"""
Test what data is available in a started game
"""
import sys
from pathlib import Path
import json

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.state import Game
from game_serializer import serialize_game_state_only


def test_game_state_content():
    """Check what data is in a started game"""
    print("🧪 Testing game state content...")

    # Create and start a game
    player_names = ["Alice", "Bob", "Carol"]
    game = Game.start(player_names, variant="1889")

    print(f"✅ Game started with {len(player_names)} players")
    print(f"   Variant: {game.variant}")
    print(f"   Minigame class: {game.minigame_class}")
    print(f"   Current player: {game.current_player.name if game.current_player else 'None'}")

    # Check state
    print(f"\n📊 Game State:")
    print(f"   Players: {len(game.state.players)}")
    print(f"   Private companies: {len(game.state.private_companies)}")
    print(f"   Public companies: {len(game.state.public_companies)}")

    # Check private companies
    print(f"\n🏢 Private Companies:")
    for pc in game.state.private_companies:
        print(f"   - {pc.name} ({pc.short_name}): ${pc.cost} (belongs_to: {pc.belongs_to.name if pc.belongs_to else 'None'})")

    # Check what minigame offers
    if game.minigame_class:
        minigame = game.getMinigame()
        print(f"\n🎮 Minigame ({type(minigame).__name__}):")
        print(f"   Minigame class: {game.minigame_class}")
        print(f"   Has get_valid_moves: {hasattr(minigame, 'get_valid_moves')}")
        print(f"   Has available_moves: {hasattr(minigame, 'available_moves')}")

    # Check what we're sending to frontend
    print(f"\n📤 Frontend State:")
    frontend_state = serialize_game_state_only(game)
    print(json.dumps(frontend_state, indent=2, default=str))

    print(f"\n📊 Frontend state now includes:")
    print(f"   ✅ Phase: {frontend_state.get('phase')}")
    print(f"   ✅ Players: {len(frontend_state.get('players', []))}")
    print(f"   ✅ Private companies: {len(frontend_state.get('private_companies', []))}")
    print(f"   ✅ Public companies: {len(frontend_state.get('public_companies', []))}")

    print(f"\n⚠️  Still missing (to be added as needed):")
    print(f"   - Available moves/actions for current player")
    print(f"   - Current auction bids/state")
    print(f"   - Stock market positions")
    print(f"   - Train roster")


if __name__ == "__main__":
    test_game_state_content()
