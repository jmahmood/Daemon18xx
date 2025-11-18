"""
Test 3-player pass scenario using the real game flow (apply_move).
This simulates what actually happens in the backend.
"""

from app.state import Game, apply_move
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.StockRound.enums import StockRoundType

# Create a 3-player game
game = Game.start(["Alice", "Bob", "Carol"], variant="1889")

print("=== Initial Setup ===")
print(f"Players: {[p.name for p in game.state.players]}")
print(f"Initial phase: {game.minigame_class}")

# Skip initial auction and go straight to Stock Round
from app.minigames.StockRound.minigame_stockround import StockRound
game.setMinigame("StockRound")
StockRound.onStart(game.state)
game.setPlayerOrder()
game.setCurrentPlayer()

print(f"Current phase: {game.minigame_class}")
print(f"stock_round_count: {game.state.stock_round_count}")

# Float a company so we can transition to OperatingRound
company = game.state.public_companies[0]
company._floated = True
company.president = game.state.players[0]
company.stock_pos = (5, 5)
company.bankrupt = False
print(f"Floated company: {company.id}")

# Simulate each player passing
for i, player in enumerate(game.state.players):
    print(f"\n=== Player {i+1} ({player.name}) Passes ===")

    # Set current player
    game.current_player = player

    # Create PASS move
    move = StockRoundMove()
    move.move_type = StockRoundType.PASS
    move.player_id = player.id
    move.player = player

    print(f"Before move:")
    print(f"  Phase: {game.minigame_class}")
    print(f"  stock_round_play: {game.state.stock_round_play}")
    print(f"  stock_round_passed: {game.state.stock_round_passed}")

    # Apply the move using the real game flow
    game = apply_move(game, move)

    print(f"After move:")
    print(f"  Phase: {game.minigame_class}")
    print(f"  stock_round_play: {game.state.stock_round_play}")
    print(f"  stock_round_passed: {game.state.stock_round_passed}")

print(f"\n=== Final State ===")
print(f"Final phase: {game.minigame_class}")
print(f"Expected: OperatingRound1")
print(f"Success: {game.minigame_class == 'OperatingRound1'}")

if game.minigame_class == "OperatingRound1":
    print(f"✅ Transition worked!")
    print(f"Operating order: {game.operating_order}")
else:
    print(f"❌ Transition failed - still in {game.minigame_class}")
