"""
Integration test for the full game start flow
This simulates what happens when a creator starts a game
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.state import Game
from game_serializer import serialize_game, deserialize_game, serialize_game_state_only
from database import db


async def test_game_start_flow():
    """Test the complete flow of creating, saving, and loading a game"""
    print("🧪 Testing game start flow (integration test)...")

    # Initialize database
    await db.initialize()
    print("✅ Database initialized")

    # Step 1: Create a game in the database
    game_info = await db.create_game(variant="1889", max_players=3)
    game_id = game_info["game_id"]
    print(f"✅ Game created in database (ID: {game_id})")

    # Step 2: Start the Daemon18xx engine (what happens when creator clicks "Start Game")
    player_names = ["Alice", "Bob", "Carol"]
    game = Game.start(player_names, variant="1889")
    print(f"✅ Game engine started with {len(player_names)} players")

    # Step 3: Serialize and save to database
    try:
        game_serialized = serialize_game(game)
        print(f"✅ Game serialized ({len(game_serialized)} bytes)")
    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        return False

    try:
        await db.save_game_state(game_id, game_serialized, 0)
        print("✅ Game state saved to database")
    except Exception as e:
        print(f"❌ Database save failed: {e}")
        return False

    # Step 4: Update game status
    await db.update_game_status(game_id, "in_progress")
    print("✅ Game status updated to in_progress")

    # Step 5: Load game from database (simulating reconnection)
    state_record = await db.get_latest_game_state(game_id)
    if not state_record:
        print("❌ Failed to retrieve game state from database")
        return False
    print("✅ Game state retrieved from database")

    # Step 6: Deserialize
    try:
        restored_game = deserialize_game(state_record["state_json"])
        print("✅ Game successfully deserialized")
    except Exception as e:
        print(f"❌ Deserialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 7: Verify the restored game
    if len(restored_game.state.players) != len(player_names):
        print(f"❌ Player count mismatch: {len(restored_game.state.players)} != {len(player_names)}")
        return False
    print(f"✅ Restored game has correct player count ({len(player_names)})")

    for i, player in enumerate(restored_game.state.players):
        if player.name != player_names[i]:
            print(f"❌ Player name mismatch: {player.name} != {player_names[i]}")
            return False
    print("✅ All player names match")

    # Step 8: Generate frontend state
    try:
        frontend_state = serialize_game_state_only(restored_game)
        print(f"✅ Frontend state generated: {list(frontend_state.keys())}")

        if 'players' not in frontend_state:
            print("❌ Frontend state missing 'players' key")
            return False

        if len(frontend_state['players']) != len(player_names):
            print(f"❌ Frontend player count mismatch")
            return False

        print(f"✅ Frontend state has {len(frontend_state['players'])} players")
    except Exception as e:
        print(f"❌ Frontend state generation failed: {e}")
        return False

    print("\n✅ All integration tests passed!")
    print("🎉 The game can be created, saved, loaded, and sent to frontend successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_game_start_flow())
    sys.exit(0 if success else 1)
