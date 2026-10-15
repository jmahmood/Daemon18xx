"""
Test game serialization to catch pickle errors before they happen in production
"""
import sys
from pathlib import Path

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.state import Game
from game_serializer import serialize_game, deserialize_game, serialize_game_state_only


def test_custom_serialization():
    """Test that Game objects can be serialized/deserialized using custom approach"""
    print("🧪 Testing custom game serialization...")

    # Create a game
    player_names = ["Alice", "Bob", "Carol"]
    game = Game.start(player_names, variant="1889")

    print(f"✅ Game created with {len(player_names)} players")
    print(f"   Variant: {getattr(game, 'variant', 'unknown')}")
    print(f"   Config type: {type(game.config)}")

    # Try to serialize it
    try:
        serialized = serialize_game(game)
        print(f"✅ Game successfully serialized ({len(serialized)} bytes)")

        # Try to deserialize it
        restored_game = deserialize_game(serialized)
        print("✅ Game successfully deserialized")

        # Verify basic properties
        assert len(restored_game.state.players) == len(player_names), "Player count mismatch"
        print(f"✅ Restored game has correct number of players ({len(player_names)})")

        assert restored_game.variant == "1889", "Variant mismatch"
        print("✅ Restored game has correct variant")

        assert restored_game.config is not None, "Config not restored"
        print(f"✅ Config restored (type: {type(restored_game.config).__name__})")

        # Verify player names
        for i, player in enumerate(restored_game.state.players):
            assert player.name == player_names[i], f"Player name mismatch: {player.name} != {player_names[i]}"
        print("✅ All player names match")

        # Test state-only serialization for frontend
        state_dict = serialize_game_state_only(restored_game)
        print(f"✅ Frontend state dict created with {len(state_dict)} keys")
        assert 'players' in state_dict, "Missing players in state dict"
        assert len(state_dict['players']) == len(player_names), "Player count in state dict mismatch"
        print(f"✅ State dict has {len(state_dict['players'])} players")

        print("\n✅ All serialization tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Serialization failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_custom_serialization()
    sys.exit(0 if success else 1)
