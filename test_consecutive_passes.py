#!/usr/bin/env python3
"""
Test that consecutive passes correctly trigger round transition,
even after non-pass moves.
"""
from app.state import Game, apply_move
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.StockRound.enums import StockRoundType
from app.base import StockPurchaseSource

# Create game
game = Game.start(["Alice", "Bob", "Carol"], variant="1889")

# Skip initial auction
from app.minigames.StockRound.minigame_stockround import StockRound
game.setMinigame("StockRound")
StockRound.onStart(game.state)
game.setPlayerOrder()
game.setCurrentPlayer()

# Float a company
company = game.state.public_companies[0]
company._floated = True
company.president = game.state.players[0]
company.stock_pos = (5, 5)
company.bankrupt = False

print("=== Test: Multiple rounds of play with passes ===")
print(f"Initial: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}")

# Round 1: Alice passes, Bob passes, Carol BUYS (interrupts the passes)
print("\n--- Round 1 ---")
alice = game.state.players[0]
bob = game.state.players[1]
carol = game.state.players[2]

# Alice passes
move = StockRoundMove()
move.move_type = StockRoundType.PASS
move.player_id = alice.id
move.player = alice

game = apply_move(game, move)
print(f"After Alice PASS: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")

# Bob passes
move = StockRoundMove()
move.move_type = StockRoundType.PASS
move.player_id = bob.id
move.player = bob

game = apply_move(game, move)
print(f"After Bob PASS: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")

# Carol buys (interrupts the passes - this should reset passed counter to 0)
move = StockRoundMove()
move.move_type = StockRoundType.BUY
move.player_id = carol.id
move.player = carol
move.public_company_id = company.id
move.source = StockPurchaseSource.IPO
move.ipo_price = 100

game = apply_move(game, move)
print(f"After Carol BUY: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")
# At this point, passed should be 0 (reset by the BUY)

# Round 2: All pass (should trigger transition)
print("\n--- Round 2: All Pass (should transition) ---")

# Alice passes
move = StockRoundMove()
move.move_type = StockRoundType.PASS
move.player_id = alice.id
move.player = alice

game = apply_move(game, move)
print(f"After Alice PASS: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")

# Bob passes
move = StockRoundMove()
move.move_type = StockRoundType.PASS
move.player_id = bob.id
move.player = bob

game = apply_move(game, move)
print(f"After Bob PASS: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")

# Carol passes (should trigger transition to OperatingRound1)
move = StockRoundMove()
move.move_type = StockRoundType.PASS
move.player_id = carol.id
move.player = carol

game = apply_move(game, move)
print(f"After Carol PASS: play={game.state.stock_round_play}, passed={game.state.stock_round_passed}, phase={game.minigame_class}")

print("\n=== Results ===")
if game.minigame_class == "OperatingRound1":
    print("✅ SUCCESS: Transitioned to OperatingRound1")
else:
    print(f"❌ FAILED: Still in {game.minigame_class}")
    print(f"   play={game.state.stock_round_play}, passed={game.state.stock_round_passed}")
