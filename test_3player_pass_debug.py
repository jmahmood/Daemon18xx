"""
Debug test for 3-player pass scenario.
Issue: Stock Round doesn't transition to Operating Round when all 3 players pass.
"""

from app.state import Game
from app.minigames.StockRound.minigame_stockround import StockRound, StockRoundMove

# Create a 3-player game
game = Game.start(["Alice", "Bob", "Carol"], variant="1889")
state = game.state

print("=== Initial Setup ===")
print(f"Players: {[p.name for p in state.players]}")
print(f"Number of players: {len(state.players)}")

# Start stock round
game.setMinigame("StockRound")
StockRound.onStart(state)
game.setPlayerOrder()

print("\n=== Stock Round Started ===")
print(f"stock_round_count: {state.stock_round_count}")
print(f"stock_round_play: {state.stock_round_play}")
print(f"stock_round_passed: {state.stock_round_passed}")

# Create the stock round instance
stock_round = game.getMinigame()

# Simulate each player passing
for i, current_player in enumerate(state.players):
    print(f"\n=== Player {i+1} ({current_player.name}) Passes ===")

    # Create PASS move using proper Move object
    from app.minigames.StockRound.move import StockRoundMove as SRMove
    from app.minigames.StockRound.enums import StockRoundType
    move = SRMove()
    move.move_type = StockRoundType.PASS  # Use enum, not string
    move.player_id = current_player.id
    move.player = current_player

    # Set current player for validation
    game.current_player = current_player

    # Use isValidMove to check
    print(f"Checking isValidMove...")
    print(f"  current_player: {current_player.name} (id: {current_player.id})")
    print(f"  move type: {move.move_type}")
    print(f"  minigame_class: {game.minigame_class}")

    result = game.isValidMove(move)
    print(f"isValidMove result: {result}")

    if result:
        is_valid_player = game.isValidPlayer(move)
        print(f"isValidPlayer result: {is_valid_player}")

        if is_valid_player:
            # Run the move
            move_result = stock_round.run(move, state)
            print(f"stock_round.run result: {move_result}")

        print(f"stock_round_play: {state.stock_round_play}")
        print(f"stock_round_passed: {state.stock_round_passed}")

        # Check what next() returns
        next_phase = stock_round.next(state)
        print(f"next() returns: {next_phase}")
        print(f"last_deal_player: {stock_round.last_deal_player}")

        # Check the transition condition
        check_play_mod = state.stock_round_play % len(state.players)
        check_play_gt_zero = state.stock_round_play > 0
        check_all_passed = state.stock_round_passed == len(state.players)

        print(f"Transition checks:")
        print(f"  stock_round_play % len(players) == 0: {check_play_mod} == 0 → {check_play_mod == 0}")
        print(f"  stock_round_play > 0: {state.stock_round_play} > 0 → {check_play_gt_zero}")
        print(f"  stock_round_passed == len(players): {state.stock_round_passed} == {len(state.players)} → {check_all_passed}")
        print(f"  ALL CONDITIONS: {check_play_mod == 0 and check_play_gt_zero and check_all_passed}")
    else:
        print(f"Move validation failed!")
        break

print("\n=== Final State ===")
print(f"Current minigame: {game.minigame_class}")
print(f"Should transition to OperatingRound1: {stock_round.next(state)}")
