#!/usr/bin/env python3
"""
Test that companies float at exactly 50% sold (not 51%+).
"""
from app.state import Game, apply_move
from app.minigames.StockRound.move import StockRoundMove
from app.minigames.StockRound.enums import StockRoundType
from app.base import StockPurchaseSource

# Create game
game = Game.start(["Alice", "Bob", "Carol"], variant="1889")

# Skip to StockRound
from app.minigames.StockRound.minigame_stockround import StockRound
game.setMinigame("StockRound")
StockRound.onStart(game.state)
game.setPlayerOrder()
game.setCurrentPlayer()

alice = game.state.players[0]
bob = game.state.players[1]
carol = game.state.players[2]
company = game.state.public_companies[0]  # AR

print(f"=== Testing Float at Exactly 50% ===")
print(f"Company: {company.short_name} ({company.name})")
print(f"Initial IPO shares: {company.stocks[StockPurchaseSource.IPO]}%")
print(f"Initial floated: {company.isFloated()}")
print()

# Alice starts the company (gets 20% president's cert)
print("--- Alice starts company (20% president's cert) ---")
move = StockRoundMove()
move.move_type = StockRoundType.BUY
move.player_id = alice.id
move.player = alice
move.public_company_id = company.id
move.source = StockPurchaseSource.IPO
move.ipo_price = 100

game = apply_move(game, move)
print(f"IPO shares remaining: {company.stocks[StockPurchaseSource.IPO]}%")
print(f"Outstanding shares: {company.outstanding_shares}%")
print(f"Floated: {company.isFloated()}")
print()

# Bob buys 10%
print("--- Bob buys 10% ---")
move = StockRoundMove()
move.move_type = StockRoundType.BUY
move.player_id = bob.id
move.player = bob
move.public_company_id = company.id
move.source = StockPurchaseSource.IPO

game = apply_move(game, move)
print(f"IPO shares remaining: {company.stocks[StockPurchaseSource.IPO]}%")
print(f"Outstanding shares: {company.outstanding_shares}%")
print(f"Floated: {company.isFloated()}")
print()

# Carol buys 10%
print("--- Carol buys 10% ---")
move = StockRoundMove()
move.move_type = StockRoundType.BUY
move.player_id = carol.id
move.player = carol
move.public_company_id = company.id
move.source = StockPurchaseSource.IPO

game = apply_move(game, move)
print(f"IPO shares remaining: {company.stocks[StockPurchaseSource.IPO]}%")
print(f"Outstanding shares: {company.outstanding_shares}%")
print(f"Floated: {company.isFloated()}")
print(f"Treasury: ${company.cash}")
print()

# Alice buys another 10%
print("--- Alice buys another 10% (total 60% sold) ---")
move = StockRoundMove()
move.move_type = StockRoundType.BUY
move.player_id = alice.id
move.player = alice
move.public_company_id = company.id
move.source = StockPurchaseSource.IPO

game = apply_move(game, move)
print(f"IPO shares remaining: {company.stocks[StockPurchaseSource.IPO]}%")
print(f"Outstanding shares: {company.outstanding_shares}%")
print(f"Floated: {company.isFloated()}")
print()

print("=== Results ===")
if company.isFloated():
    print(f"✅ SUCCESS: Company floated with {company.outstanding_shares}% sold")
    print(f"   Treasury: ${company.cash}")
else:
    print(f"❌ FAILED: Company not floated despite {company.outstanding_shares}% sold")
