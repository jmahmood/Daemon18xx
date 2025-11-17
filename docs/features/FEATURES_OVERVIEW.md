# Features Overview

Complete overview of all features in the Daemon18xx game engine.

## Table of Contents

- [Core Features](#core-features)
- [Phase 4 Features (Recently Added)](#phase-4-features)
- [Advanced Mechanics](#advanced-mechanics)
- [Developer Tools](#developer-tools)
- [Variants](#variants)

---

## Core Features

### Stateless Minigame Architecture

The game is structured as a series of "minigames" that each handle a specific game phase:

- **BuyPrivateCompany**: Initial private company auction
- **BiddingForPrivateCompany**: Competitive bidding on private companies
- **StockRound**: Buy/sell stock
- **OperatingRound**: Companies operate trains and pay dividends
- **Auction**: Mid-game private company auctions

Each minigame:
- Validates moves independently
- Mutates game state
- Determines the next phase
- Has lifecycle hooks (onStart, onComplete, etc.)

**Benefits:**
- Easy to test (isolate each phase)
- Clear separation of concerns
- Suitable for web APIs (stateless)
- Parallelizable operations

---

### Stock Market System

Full stock market implementation with:

- **Grid-based stock market**: 12×5 grid with prices and movement rules
- **Price bands**: Yellow, Brown bands with different movement rules
- **Arrow cells**: Special cells with directional movement
- **Stock purchase**: From IPO or Bank pool
- **Stock sales**: Trigger price drops
- **Sold-out bonuses**: Price increases when sold out
- **Dividend payouts**: Automatic share distribution

**API:**
```python
# Attach company to market
company.attach_market(stock_market, row=1, col=3)

# Buy stock
company.buyStock(player, amount=20, source=StockPurchaseSource.IPO)

# Price movements
company.priceUp(spaces=1, reason="Dividend paid")
company.priceDown(amount=10)  # 10% sold

# Dividends
company.payDividends()  # Pay to shareholders
company.incomeToCash()  # Withhold to treasury
```

---

### Company Management

Comprehensive company mechanics:

- **Floating**: Companies float when 60% sold
- **Presidency**: Automatic president changes
- **Share pools**: IPO and Bank pools
- **Train ownership**: Companies own trains
- **Station tokens**: Limited tokens with costs
- **Cash management**: Company treasury

**API:**
```python
# Check status
if company.isFloated():
    print(f"President: {company.president.name}")
    print(f"Cash: ${company.cash}")
    print(f"Stock price: ${company.get_current_price()}")

# Presidency
company.checkPresident()  # Auto-detect president changes

# Floating
if company.checkFloated():
    print("Company just floated!")
```

---

### Player Management

Player state and portfolio tracking:

- **Cash management**: Track player cash
- **Portfolio**: Set of owned companies
- **Share ownership**: Track % ownership per company
- **Private companies**: Owned private companies
- **Turn order**: Player order tracking

**API:**
```python
# Create player
player = Player.create("Alice", cash=1000, order=0)

# Transactions
player.payCash(100)
player.receiveCash(50)

# Portfolio
player.addToPortfolio(company, amount=20, price=100)

# Query
companies_owned = list(player.portfolio)
private_companies = list(player.private_companies)
```

---

## Phase 4 Features

### 🆕 Historical Stock Price Tracking (PR #12)

Complete history of all stock price changes with reasons and timestamps.

**Features:**
- Tracks every price change with old/new price
- Records reason for change (e.g., "Dividend paid", "Stock sold")
- Optional player ID for player-triggered changes
- ISO timestamps for audit trail
- Query methods with filtering

**API:**
```python
# Automatic tracking (already integrated)
company.priceUp(1, "Stock sold out")  # Automatically recorded
company.priceDown(10)  # Automatically recorded

# Query history
history = company.get_price_history()
for entry in history:
    print(f"Round {entry.round_number}: ${entry.old_price} → ${entry.new_price}")
    print(f"  Reason: {entry.reason}")
    print(f"  Time: {entry.timestamp}")

# Query with filters
recent_changes = company.get_price_history(limit=5)
since_round_3 = company.get_price_history(since_round=3)
```

**Use Cases:**
- **Debugging**: Track down why a price changed unexpectedly
- **Visualization**: Display price charts in frontend
- **Analysis**: Study price patterns and strategies
- **Audit**: Verify game integrity and fairness

**Integration:**
- Seamlessly integrated into all price change methods
- No performance overhead (simple list append)
- Automatically records during stock market movements

---

### 🆕 Enhanced Logging & Debugging (PR #16)

Professional structured logging system with game history tracking.

#### Structured Logging

**Features:**
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Context data support (add extra info to logs)
- Debug mode with JSON output
- File logging support
- Performance timing utilities

**API:**
```python
from app.logging_config import setup_logging, get_logger, PerformanceTimer

# Configure logging
setup_logging(level='INFO', debug_mode=False, log_file='game.log')

# Get logger
logger = get_logger(__name__)

# Log with context
logger.info("Move executed", extra={'player': 'Alice', 'amount': 100})

# Performance timing
with PerformanceTimer(logger, "Complex operation", player_id="Alice"):
    # ... operation ...
    pass
```

**Modes:**
- **Normal mode**: Human-readable logs with context
- **Debug mode**: JSON output for machine parsing
- **File mode**: Write to file for production

#### Game History Tracking

**Features:**
- Records all moves with timestamp and success status
- Captures validation errors for failed moves
- Lightweight state snapshots after successful moves
- Export to JSON for analysis
- Query methods for filtering

**API:**
```python
from app.game_history import GameHistory

# Create tracker
history = GameHistory()
history.initialize(variant='1830', players=['Alice', 'Bob'])

# Record moves (in game loop)
success = game.performedMove(move)
history.record_move(
    move=move,
    state=game.state,
    success=success,
    errors=game.errors() if not success else None,
    phase=game.minigame_class
)

# Export
history.export_json('games/game_20251117.json')

# Query
alice_moves = history.get_moves_by_player("Alice")
stock_moves = history.get_moves_by_phase("StockRound")
failed_moves = history.get_failed_moves()
```

**Use Cases:**
- **Debugging**: Review exact sequence leading to bug
- **Testing**: Generate test cases from real games
- **Analysis**: Study player strategies
- **Replay**: Foundation for game replay feature
- **Compliance**: Audit trail for competitive play

---

### 🆕 Game Phase Transition Validation (PR #13)

Formal state machine for validating game phase transitions.

**Features:**
- Defines valid phase transitions
- Enforces correct game flow
- Tracks phase history with timestamps
- Counts stock/operating rounds
- Variant-specific operating round limits

**Valid Transitions:**
```
BuyPrivateCompany → {StockRound, BiddingForPrivateCompany}
BiddingForPrivateCompany → {BuyPrivateCompany, StockRound}
StockRound → {OperatingRound, StockRound, Auction}
Auction → {StockRound}
OperatingRound → {StockRound, OperatingRound}
```

**Variant Rules:**
- **1830**: Max 3 operating rounds per stock round
- **1846**: Max 3 operating rounds per stock round
- **1889**: Max 2 operating rounds per stock round
- **1817**: Max 4 operating rounds per stock round

**API:**
```python
# Automatic validation (integrated into Game.setMinigame)
game.setMinigame("StockRound")  # Validated automatically

# Manual validation
validator = game.phase_validator

if validator.can_transition("StockRound", "OperatingRound"):
    # Proceed
    pass

# Query valid phases
valid = validator.get_valid_next_phases("StockRound")
# Returns: {'OperatingRound', 'StockRound', 'Auction'}

# Get summary
summary = validator.get_phase_summary()
# {
#   'current_phase': 'StockRound',
#   'stock_round_count': 2,
#   'operating_round_count': 5,
#   'operating_rounds_this_set': 0
# }

# History
transitions = validator.get_transition_history()
for t in transitions:
    print(f"{t.from_phase} → {t.to_phase} at {t.timestamp}")
```

**Use Cases:**
- **Development**: Catch phase transition bugs early
- **Validation**: Ensure games follow rules
- **UI**: Display valid next phases to users
- **Frontend**: Prevent invalid user actions
- **Debugging**: Review phase flow history

---

## Advanced Mechanics

### 💰 Loans & Debt Management (PR #5)

Companies can take loans with interest.

**Features:**
- Loans from president or bank
- Interest accrual per round
- Partial and full repayment
- Debt service checks
- Credit history tracking

**API:**
```python
# Take loan
loan = company.take_loan(
    amount=500,
    lender=president,
    interest_rate=0.05,  # 5%
    current_round=1
)

# Repay
company.repay_loan(loan, amount=100)

# Check debt
total = company.total_debt()
can_pay = company.can_service_debt()

# Accrue interest (each round)
company.accrue_loan_interest()
```

---

### 🗻 Terrain Costs (PR #6)

Track laying costs multipliers based on terrain.

**Terrain Types:**
- **NORMAL**: 1x cost
- **MOUNTAIN**: 2x cost
- **BRIDGE**: 2x cost (1.5x in 1846)
- **TUNNEL**: 2x cost

**API:**
```python
from app.base import TerrainType

# Set terrain on tile
tile.terrain_type = TerrainType.MOUNTAIN

# Get cost multiplier
multiplier = tile.terrain_cost()  # Returns 2.0

# Variant-specific
# In 1846, bridges are 1.5x instead of 2x
```

---

### 🎯 Special Powers (PR #4)

Private companies grant special powers.

**Power Types:**
- **EXTRA_TOKEN**: Additional token placement
- **REVENUE_BONUS**: Bonus revenue on routes
- **FREE_TRACK**: Free or discounted track laying
- **TERRAIN_DISCOUNT**: Ignore/reduce terrain costs
- **TRAIN_DISCOUNT**: Discount on train purchases

**API:**
```python
from app.base import PowerType, SpecialPower

# Create power
power = SpecialPower(
    power_type=PowerType.TRAIN_DISCOUNT,
    value=20,  # $20 discount
    description="$20 off train purchases"
)

# Assign to private company
private_company.power = power

# Check power
if pc.power and pc.power.power_type == PowerType.TRAIN_DISCOUNT:
    discount = pc.power.value
```

---

### 📍 Enhanced Route Validation (PR #7)

Improved topology checking for train routes.

**Features:**
- Validates continuous track
- Checks station token placement
- Verifies revenue calculations
- Topology validation

**API:**
```python
# Check if company can operate
if company.hasValidRoute(board):
    # Can run trains
    pass
```

---

### 💸 Bankruptcy & Receivership (PR #8)

Handle company and player bankruptcy.

**Features:**
- Company bankruptcy detection
- Forced share sales
- Asset liquidation
- Receivership state
- President liability

**API:**
```python
# Mark bankrupt
company.bankrupt = True

# Check if can service debt
if not company.can_service_debt():
    # Initiate bankruptcy proceedings
    pass
```

---

## Developer Tools

### Testing Framework

**233 tests** covering all functionality:

```bash
# All tests
python -m unittest discover app/unittests -v

# Specific feature
python -m unittest app.unittests.test_PriceHistory -v
python -m unittest app.unittests.test_Logging -v
python -m unittest app.unittests.test_PhaseValidation -v

# Specific test
python -m unittest app.unittests.test_PriceHistory.PriceHistoryEntryTests.test_entry_creation
```

**Test Categories:**
- Unit tests for individual methods
- Integration tests for workflows
- Variant-specific tests
- Edge case tests

---

### Configuration System

Easy variant configuration:

```python
# app/config/yourvariant.py
NAME = "YourVariant"

PRIVATE_COMPANIES = [...]
PUBLIC_COMPANIES = [...]
STOCK_MARKET = create_stock_market(...)

def starting_cash(num_players):
    return {3: 500, 4: 400, 5: 350}[num_players]
```

---

### Architecture Documentation (PR #11)

Comprehensive inline documentation:

- Object relationship patterns
- Cross-linking rationale
- Design decisions
- State management principles

---

## Variants

### 1830: Robber Barons

The classic 18XX game.

**Features:**
- 8 public companies
- 6 private companies
- 12×5 stock market
- 3 operating rounds per set

**Companies:** PRR, B&O, NYC, C&O, Erie, Reading, CP, LV

---

### 1846: Race for the Midwest

Unique capitalization and mechanics.

**Features:**
- Bridge terrain uses 1.5x multiplier
- Different stock market layout
- Unique private companies
- Special powers integration

---

### 1889: Shikoku

Japanese variant with modified rules.

**Features:**
- 7 public companies
- Smaller stock market
- 2 operating rounds per set
- Different private companies

---

## Future Features

### Planned Enhancements

- **Game replay**: Replay from move history
- **Save/load**: Serialize and restore games
- **AI players**: Computer opponents
- **Multiplayer server**: Networked play
- **Web dashboard**: Visual game monitoring
- **More variants**: 1817, 18Chesapeake, etc.

---

## Feature Comparison

| Feature | Status | Tests | Documentation |
|---------|--------|-------|---------------|
| Core Game Loop | ✅ Complete | 162 tests | ✅ |
| Stock Market | ✅ Complete | ✅ | ✅ |
| Private Companies | ✅ Complete | ✅ | ✅ |
| Operating Rounds | ✅ Complete | ✅ | ✅ |
| **Price History** | ✅ PR #12 | 25 tests | ✅ |
| **Logging System** | ✅ PR #16 | 15 tests | ✅ |
| **Phase Validation** | ✅ PR #13 | 31 tests | ✅ |
| Special Powers | ✅ PR #4 | ✅ | ✅ |
| Loans | ✅ PR #5 | ✅ | ✅ |
| Terrain Costs | ✅ PR #6 | ✅ | ✅ |
| Route Validation | ✅ PR #7 | ✅ | ✅ |
| Bankruptcy | ✅ PR #8 | ✅ | ✅ |
| 1830 Variant | ✅ | ✅ | ✅ |
| 1846 Variant | ✅ | ✅ | ✅ |
| 1889 Variant | ✅ | ✅ | ✅ |

**Total:** 233 tests passing ✅

---

**Navigation:**
- [← Back to Main](../README.md)
- [Price History Details](price_history.md)
- [Logging Details](logging.md)
- [Phase Validation Details](phase_validation.md)
