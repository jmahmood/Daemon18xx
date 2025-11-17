# Authentication Fix Summary

## Issues Found

### 1. RuntimeWarning - Coroutine Not Awaited
**Location:** `server.py:166`
```python
sio.enter_room(sid, room_code)  # ❌ Missing await
```

**Error:**
```
RuntimeWarning: coroutine 'AsyncServer.enter_room' was never awaited
```

**Fix:**
```python
await sio.enter_room(sid, room_code)  # ✅ Properly awaited
```

### 2. Invalid Token Error for Players
**Problem:** Player tokens were generated but never stored in the database.

**Flow Before (Broken):**
1. Game created → player tokens generated
2. Tokens returned to creator but NOT stored in database
3. Player tries to authenticate → `verify_token()` checks database
4. Token not found → "Invalid token" error ❌

**Flow After (Fixed):**
1. Game created → player tokens generated
2. **NEW:** Pre-register players in database with tokens as "Player N (pending)"
3. Player authenticates → token found in database ✅
4. Player sets name → updates "pending" to actual name

## Code Changes

### database.py

**Added pre-registration in `create_game()`:**
```python
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
```

**Added `update_player_name()` method:**
```python
async def update_player_name(self, player_token: str, player_name: str) -> bool:
    """Update a player's name (when they join with a pre-registered token)"""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute("""
            UPDATE players
            SET player_name = ?, last_seen_at = CURRENT_TIMESTAMP
            WHERE player_token = ?
        """, (player_name, player_token))
        await db.commit()
        return True
```

### server.py

**Updated `join_game()` handler:**
- Changed from creating new player → updating existing player's name
- Now works with pre-registered tokens
- Validates that only players (not creator/spectator) can set names

**Added missing import:**
```python
from datetime import datetime
```

## Testing the Fix

1. **Start fresh:**
   ```bash
   cd multiplayer/backend
   rm -f game.db  # Remove old database
   python server.py
   ```

2. **Create game:**
   - Returns player URLs with tokens
   - Database now has 6 "Player N (pending)" entries

3. **Player joins:**
   - Opens player URL
   - Authenticates successfully (token found in database) ✅
   - Frontend prompts for name
   - `join_game` updates "Player 1 (pending)" → "Alice"

4. **Check database:**
   ```sql
   SELECT player_name, player_token FROM players WHERE game_id = 1;
   ```
   Should show actual names instead of "(pending)"

## Additional Notes

- Players are now visible in the lobby immediately after authentication
- The "(pending)" suffix helps identify players who haven't set their name yet
- Creator can see which slots are filled vs. empty
- Spectators work the same way (authenticate with spectator token)

## Files Modified

- `multiplayer/backend/database.py`
  - `create_game()`: Pre-register players
  - `update_player_name()`: New method

- `multiplayer/backend/server.py`
  - Line 166: Added `await`
  - `join_game()`: Changed logic
  - Added `datetime` import
