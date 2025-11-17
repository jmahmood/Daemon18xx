# Quickstart Guide

Get up and running with Daemon18xx in 5 minutes!

## Installation

```bash
# Clone the repository
git clone https://github.com/jmahmood/Daemon18xx.git
cd Daemon18xx

# No external dependencies required - pure Python!
python --version  # Ensure Python 3.7+ is installed
```

## Your First Game

### 1. Start a Game

```python
from app.state import Game

# Create a new game with 3 players
game = Game.start(
    players=['Alice', 'Bob', 'Charlie'],
    variant='1830'  # Can also use '1846' or '1889'
)

print(f"Game started! Current phase: {game.minigame_class}")
print(f"Current player: {game.current_player.name}")
```

### 2. Make a Move

```python
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompanyMove

# Alice buys a private company
move = BuyPrivateCompanyMove(
    player_id=game.current_player.id,
    company_id="C&O"  # Chesapeake & Ohio
)

# Execute the move
success = game.performedMove(move)

if success:
    print("✓ Move successful!")
    print(f"Next player: {game.current_player.name}")
else:
    print("✗ Move failed!")
    print(f"Errors: {game.errors()}")
```

### 3. Check Game State

```python
# View player information
for player in game.state.players:
    print(f"{player.name}: ${player.cash}")

# View available private companies
for company in game.state.private_companies:
    if not company.belongs_to:
        print(f"{company.name} - ${company.cost}")

# View phase information
summary = game.phase_validator.get_phase_summary()
print(f"Stock Rounds: {summary['stock_round_count']}")
print(f"Operating Rounds: {summary['operating_round_count']}")
```

## Common Workflows

### Full Game Loop

```python
from app.state import Game
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompanyMove, PassMove

game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')

# Game loop
while game.isOngoing():
    current_player = game.current_player
    print(f"\n{current_player.name}'s turn ({game.minigame_class})")

    # Get valid moves (this would come from your game logic/UI)
    # For this example, we'll just pass
    move = PassMove(player_id=current_player.id)

    success = game.performedMove(move)

    if not success:
        print(f"Invalid move: {game.errors()}")
        break

    # Check if phase changed
    if game.minigame_class == "StockRound":
        print("→ Moved to Stock Round!")
        break  # Exit for this example
```

### Buying Stock

```python
from app.minigames.StockRound.minigame_stockround import BuyStockMove

# Assumes game is in StockRound phase
move = BuyStockMove(
    player_id=game.current_player.id,
    company_id="PRR",  # Pennsylvania Railroad
    amount=20,  # Buy 20% (2 shares)
    source="IPO",  # or "BANK"
    price=100  # Price per share
)

success = game.performedMove(move)
```

### Enabling Logging

```python
from app.logging_config import setup_logging

# Enable INFO level logging to console
setup_logging(level='INFO', debug_mode=False)

# Enable DEBUG logging with JSON output
setup_logging(level='DEBUG', debug_mode=True)

# Log to file
setup_logging(level='INFO', log_file='game.log')

# Now start your game - all actions will be logged
game = Game.start(['Alice', 'Bob'], variant='1830')
```

### Tracking Game History

```python
from app.game_history import GameHistory

# Create history tracker
history = GameHistory()
history.initialize(variant='1830', players=['Alice', 'Bob', 'Charlie'])

# In your game loop
success = game.performedMove(move)
history.record_move(
    move=move,
    state=game.state,
    success=success,
    phase=game.minigame_class
)

# Export history
history.export_json('games/game_20251117.json')

# Query history
alice_moves = history.get_moves_by_player("Alice")
stock_round_moves = history.get_moves_by_phase("StockRound")
failed_moves = history.get_failed_moves()
```

## Understanding Game Phases

Daemon18xx uses a "minigame" architecture where each game phase is a separate minigame:

### Phase Flow

```
BuyPrivateCompany (Initial Auction)
    ↓
BiddingForPrivateCompany (if competitive bidding)
    ↓
StockRound (Buy/sell stock)
    ↓
OperatingRound (Companies operate)
    ↓
OperatingRound (2nd operating round)
    ↓
OperatingRound (3rd operating round)
    ↓
StockRound (Next stock round)
    ↓
...continues...
```

### Checking Valid Phases

```python
# Get valid next phases
valid_phases = game.phase_validator.get_valid_next_phases(game.minigame_class)
print(f"Can transition to: {valid_phases}")

# Check specific transition
can_go = game.phase_validator.can_transition(
    "StockRound",
    "OperatingRound"
)
```

## Working with Companies

### Public Companies

```python
# Get all public companies
companies = game.state.public_companies

for company in companies:
    if company.isFloated():
        print(f"{company.name}")
        print(f"  President: {company.president.name if company.president else 'None'}")
        print(f"  Cash: ${company.cash}")
        print(f"  Stock Price: ${company.get_current_price()}")
        print(f"  Trains: {len(company.trains)}")
```

### Private Companies

```python
# Get all private companies
for pc in game.state.private_companies:
    owner = pc.belongs_to.name if pc.belongs_to else "Available"
    print(f"{pc.name}: {owner} (${pc.cost})")

    # Check if has special power
    if pc.power:
        print(f"  Power: {pc.power.power_type.name}")
```

### Stock Price History

```python
# Get price history for a company
company = game.state.public_companies[0]  # First company
history = company.get_price_history()

for entry in history:
    print(f"Round {entry.round_number}: ${entry.old_price} → ${entry.new_price}")
    print(f"  Reason: {entry.reason}")

# Query recent price changes
recent = company.get_price_history(limit=5)

# Query since specific round
since_round_3 = company.get_price_history(since_round=3)
```

## Advanced Features

### Loans

```python
# Company takes a loan from president
company = game.state.public_companies[0]
president = company.president

loan = company.take_loan(
    amount=500,
    lender=president,
    interest_rate=0.05,  # 5%
    current_round=1
)

print(f"Loan ID: {loan.id}")
print(f"Balance: ${loan.balance}")

# Repay loan
company.repay_loan(loan, amount=100)

# Check total debt
total_debt = company.total_debt()
can_service = company.can_service_debt()
```

### Terrain Costs

```python
from app.base import TerrainType

# Check terrain cost for track laying
terrain_cost = some_tile.terrain_cost()  # Returns multiplier

# Terrain types:
# - TerrainType.NORMAL: 1x cost
# - TerrainType.MOUNTAIN: 2x cost
# - TerrainType.BRIDGE: 2x cost (1.5x in 1846)
# - TerrainType.TUNNEL: 2x cost
```

### Special Powers

```python
from app.base import PowerType

# Check private company power
if pc.power and pc.power.power_type == PowerType.TRAIN_DISCOUNT:
    discount_amount = pc.power.value  # e.g., 20
    print(f"Train discount: ${discount_amount}")
```

## Running Tests

```bash
# All tests
python -m unittest discover app/unittests -v

# Specific feature tests
python -m unittest app.unittests.test_PriceHistory -v
python -m unittest app.unittests.test_Logging -v
python -m unittest app.unittests.test_PhaseValidation -v

# Specific variant tests
python -m unittest app.unittests.test_1846_variant -v
```

## Common Pitfalls

### ❌ Don't: Modify state directly

```python
# BAD - Don't do this!
game.state.players[0].cash += 100
```

### ✅ Do: Use moves and game methods

```python
# GOOD - Use proper game mechanics
# (There isn't a direct "give cash" move - use game transactions)
```

### ❌ Don't: Assume phase transitions

```python
# BAD - Don't assume you can transition anywhere
game.setMinigame("OperatingRound")  # Might be invalid!
```

### ✅ Do: Check valid transitions

```python
# GOOD - Validate first
if game.phase_validator.can_transition(current, "OperatingRound"):
    game.setMinigame("OperatingRound")
```

### ❌ Don't: Ignore validation errors

```python
# BAD - Silently fails
success = game.performedMove(move)
```

### ✅ Do: Handle errors properly

```python
# GOOD - Check and handle errors
success = game.performedMove(move)
if not success:
    errors = game.errors()
    print(f"Move failed: {errors}")
    # Handle the error appropriately
```

## Next Steps

Now that you're familiar with the basics, explore:

- **[API Reference](api_reference.md)** - Complete API documentation
- **[Game Concepts](game_concepts.md)** - Learn 18XX terminology
- **[Frontend Integration](frontend_integration.md)** - Build a UI
- **[Examples](examples/)** - More code examples

## Need Help?

- Check the [API Reference](api_reference.md) for detailed method documentation
- Review [examples/](examples/) for more complex scenarios
- See [features/logging.md](features/logging.md) for debugging tips

---

**Navigation:**
- [← Back to Main](README.md)
- [Next: Game Concepts →](game_concepts.md)
- [API Reference →](api_reference.md)
