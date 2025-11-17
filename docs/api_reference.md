# API Reference

Complete API documentation for the Daemon18xx game engine.

## Table of Contents

- [Core Classes](#core-classes)
  - [Game](#game)
  - [Player](#player)
  - [PublicCompany](#publiccompany)
  - [PrivateCompany](#privatecompany)
  - [MutableGameState](#mutablegamestate)
- [Moves](#moves)
- [Features](#features)
  - [Price History](#price-history)
  - [Logging](#logging)
  - [Phase Validation](#phase-validation)
  - [Game History](#game-history)
- [Minigames](#minigames)

---

## Core Classes

### Game

The main game controller that manages game state and phase transitions.

**Location:** `app/state.py`

#### Methods

##### `Game.start(players: List[str], variant: str = "1830") -> Game`

Static method to create and initialize a new game.

**Parameters:**
- `players` (List[str]): List of player names
- `variant` (str): Game variant ("1830", "1846", or "1889")

**Returns:** Initialized Game instance

**Example:**
```python
game = Game.start(['Alice', 'Bob', 'Charlie'], variant='1830')
```

---

##### `Game.initialize(players: List[Player], config, saved_game: dict = None, variant: str = "1830") -> Game`

Static method to initialize a game with Player objects (advanced).

**Parameters:**
- `players` (List[Player]): List of Player objects
- `config`: Game configuration object
- `saved_game` (dict, optional): Saved game state for loading
- `variant` (str): Game variant name

**Returns:** Initialized Game instance

---

##### `game.performedMove(move: Move) -> bool`

Execute a move and update game state.

**Parameters:**
- `move` (Move): The move to execute

**Returns:** True if move succeeded, False if validation failed

**Example:**
```python
success = game.performedMove(move)
if not success:
    print(f"Errors: {game.errors()}")
```

---

##### `game.isValidMove(move: Move) -> bool`

Check if a move is valid for the current game state.

**Parameters:**
- `move` (Move): The move to validate

**Returns:** True if valid, False otherwise

---

##### `game.isValidPlayer(move: Move) -> bool`

Check if the move's player is the current player.

**Parameters:**
- `move` (Move): The move to check

**Returns:** True if correct player, False otherwise

---

##### `game.errors() -> List[str]`

Get list of validation errors from last move attempt.

**Returns:** List of error messages

---

##### `game.setMinigame(minigame_class: str) -> None`

Set the current game phase (with validation).

**Parameters:**
- `minigame_class` (str): Name of the minigame phase

**Valid phases:** "BuyPrivateCompany", "BiddingForPrivateCompany", "StockRound", "Auction", "OperatingRound"

---

##### `game.getState() -> MutableGameState`

Get the current mutable game state.

**Returns:** MutableGameState object

---

##### `game.sort_operating_order() -> List[str]`

Sort companies for operating round order.

**Returns:** List of company IDs in operating order

---

#### Attributes

- `game.state` (MutableGameState): Current game state
- `game.current_player` (Player): Current player
- `game.minigame_class` (str): Current phase name
- `game.phase_validator` (PhaseValidator): Phase transition validator
- `game.variant` (str): Game variant name
- `game.config`: Game configuration
- `game.operating_order` (List[str]): Current operating order
- `game.errors_list` (List[str]): Current error list

---

### Player

Represents an individual player in the game.

**Location:** `app/base.py`

#### Methods

##### `Player.create(name: str, cash: int, order: int) -> Player`

Static method to create a new player.

**Parameters:**
- `name` (str): Player name
- `cash` (int): Starting cash
- `order` (int): Turn order position (0-indexed)

**Returns:** Player instance

**Example:**
```python
player = Player.create("Alice", 1000, 0)
```

---

##### `player.addToPortfolio(company: PublicCompany, amount: int, price: int) -> None`

Add shares to player's portfolio.

**Parameters:**
- `company` (PublicCompany): Company to add shares of
- `amount` (int): Percentage of shares (10, 20, etc.)
- `price` (int): Price paid per share

---

##### `player.payCash(amount: int) -> None`

Deduct cash from player.

**Parameters:**
- `amount` (int): Amount to deduct

---

##### `player.receiveCash(amount: int) -> None`

Add cash to player.

**Parameters:**
- `amount` (int): Amount to add

---

#### Attributes

- `player.name` (str): Player name
- `player.id` (str): Unique player ID
- `player.cash` (int): Current cash
- `player.order` (int): Turn order
- `player.portfolio` (Set[PublicCompany]): Companies owned
- `player.private_companies` (Set[PrivateCompany]): Private companies owned
- `player.passed` (bool): Whether player passed this round

---

### PublicCompany

Represents a public railroad company.

**Location:** `app/base.py`

#### Methods

##### `PublicCompany.initiate(id: str, name: str, short_name: str, tokens_available: int, token_costs: List[int]) -> PublicCompany`

Create a new public company.

**Parameters:**
- `id` (str): Company ID (e.g., "PRR")
- `name` (str): Full company name
- `short_name` (str): Abbreviated name
- `tokens_available` (int): Number of station tokens
- `token_costs` (List[int]): Cost for each token placement

**Returns:** PublicCompany instance

---

##### `company.setInitialPrice(ipo_price: int) -> None`

Set the initial stock price.

**Parameters:**
- `ipo_price` (int): Initial price per 10% share

---

##### `company.buyStock(player: Player, amount: int, source: StockPurchaseSource) -> None`

Sell shares to a player.

**Parameters:**
- `player` (Player): Buying player
- `amount` (int): Percentage of shares (10, 20, etc.)
- `source` (StockPurchaseSource): Source (IPO or BANK)

---

##### `company.sell(player: Player, amount: int) -> None`

Player sells shares back to company.

**Parameters:**
- `player` (Player): Selling player
- `amount` (int): Percentage of shares

---

##### `company.priceUp(spaces: int, reason: str = "Price increase") -> None`

Increase stock price.

**Parameters:**
- `spaces` (int): Number of spaces to move up
- `reason` (str): Reason for increase (for history)

---

##### `company.priceDown(amount: int) -> None`

Decrease stock price based on shares sold.

**Parameters:**
- `amount` (int): Percentage of shares sold

---

##### `company.payDividends() -> None`

Distribute accumulated income to shareholders.

---

##### `company.incomeToCash() -> None`

Move accumulated income to company treasury (withhold).

---

##### `company.addIncome(amount: int) -> None`

Add to accumulated income.

**Parameters:**
- `amount` (int): Income amount

---

##### `company.isFloated() -> bool`

Check if company has floated.

**Returns:** True if floated

---

##### `company.checkFloated() -> bool`

Check and update float status.

**Returns:** True if newly floated

---

##### `company.hasNoTrains() -> bool`

Check if company has no trains.

**Returns:** True if no trains

---

##### `company.hasValidRoute(board: GameBoard = None) -> bool`

Check if company can operate a route.

**Returns:** True if can operate

---

##### `company.take_loan(amount: int, lender: Player, interest_rate: float, current_round: int) -> Loan`

Take out a loan (PR #5).

**Parameters:**
- `amount` (int): Loan principal
- `lender` (Player): Who is lending (usually president)
- `interest_rate` (float): Interest rate (e.g., 0.05 for 5%)
- `current_round` (int): Current game round

**Returns:** Loan object

---

##### `company.repay_loan(loan: Loan, amount: int) -> int`

Repay all or part of a loan.

**Parameters:**
- `loan` (Loan): The loan to repay
- `amount` (int): Amount to repay

**Returns:** Actual amount repaid

---

##### `company.total_debt() -> int`

Calculate total outstanding debt.

**Returns:** Total debt amount

---

##### `company.can_service_debt() -> bool`

Check if company can make minimum debt payments.

**Returns:** True if can service debt

---

##### `company.record_price_change(old_price: int, new_price: int, reason: str, round_number: int = 0, player_id: Optional[str] = None) -> None`

Record a stock price change (PR #12).

**Parameters:**
- `old_price` (int): Price before change
- `new_price` (int): Price after change
- `reason` (str): Reason for change
- `round_number` (int): Game round
- `player_id` (str, optional): Player who triggered change

---

##### `company.get_price_history(limit: Optional[int] = None, since_round: Optional[int] = None) -> List[PriceHistoryEntry]`

Query price history (PR #12).

**Parameters:**
- `limit` (int, optional): Max number of entries
- `since_round` (int, optional): Only entries from this round onward

**Returns:** List of PriceHistoryEntry objects

---

##### `company.get_current_price() -> int`

Get current stock price.

**Returns:** Current price

---

#### Attributes

- `company.id` (str): Company ID
- `company.name` (str): Full name
- `company.short_name` (str): Abbreviated name
- `company.cash` (int): Company cash
- `company.president` (Player): Current president
- `company.owners` (Dict[Player, int]): Share ownership
- `company.stocks` (Dict[StockPurchaseSource, int]): Available shares
- `company.stockPrice` (Dict[StockPurchaseSource, int]): Stock prices
- `company.trains` (List[Train]): Owned trains
- `company.tokens` (List): Station tokens
- `company.tokens_available` (int): Available tokens
- `company.bankrupt` (bool): Bankruptcy status
- `company.loans` (List[Loan]): Outstanding loans
- `company.price_history` (List[PriceHistoryEntry]): Price change history
- `company.stock_market` (StockMarket): Attached stock market
- `company.stock_pos` (Tuple[int, int]): Position on stock market grid

---

### PrivateCompany

Represents a private company with special powers.

**Location:** `app/base.py`

#### Attributes

- `pc.name` (str): Company name
- `pc.short_name` (str): Abbreviated name
- `pc.cost` (int): Purchase cost
- `pc.actual_cost` (int): Actual cost paid (if auctioned)
- `pc.revenue` (int): Revenue per round
- `pc.belongs_to` (Player): Owner
- `pc.belongs_to_company` (PublicCompany): Public company owner (if sold)
- `pc.power` (SpecialPower): Special power (if any)
- `pc.order` (int): Priority order

---

### MutableGameState

Container for mutable game state passed to minigames.

**Location:** `app/base.py`

#### Attributes

- `state.players` (List[Player]): All players
- `state.public_companies` (List[PublicCompany]): Public companies
- `state.private_companies` (List[PrivateCompany]): Private companies
- `state.priority_deal_player` (Player): Priority deal holder
- `state.stock_round_count` (int): Number of stock rounds completed
- `state.stock_round_play` (int): Current play within stock round
- `state.stock_round_passed` (int): Number of passed players
- `state.auction` (List[Tuple[str, int]]): Current auction bids
- `state.auctioned_private_company` (PrivateCompany): Company being auctioned
- `state.sales` (List[Dict]): Sales history per stock round
- `state.purchases` (List[Dict]): Purchase history per stock round
- `state.track_laid` (Set[str]): Companies that laid track this OR

---

## Moves

### BuyPrivateCompanyMove

Purchase a private company during initial auction.

**Location:** `app/minigames/PrivateCompanyInitialAuction/minigame_buy.py`

**Attributes:**
- `player_id` (str): Player making purchase
- `company_id` (str): Private company ID

---

### PassMove

Pass on current action.

**Location:** Various minigame modules

**Attributes:**
- `player_id` (str): Player passing

---

### BuyStockMove

Purchase public company stock.

**Location:** `app/minigames/StockRound/minigame_stockround.py`

**Attributes:**
- `player_id` (str): Buyer
- `company_id` (str): Company to buy from
- `amount` (int): Percentage to buy
- `source` (str): "IPO" or "BANK"
- `price` (int): Price per share

---

### SellStockMove

Sell public company stock.

**Location:** `app/minigames/StockRound/minigame_stockround.py`

**Attributes:**
- `player_id` (str): Seller
- `company_id` (str): Company to sell
- `amount` (int): Percentage to sell

---

### LayTrackMove

Lay track during operating round.

**Location:** `app/minigames/operating_round.py`

**Attributes:**
- `company_id` (str): Company laying track
- `tile_id` (str): Tile to place
- `location` (str): Board location
- `rotation` (int): Tile rotation

---

### RunTrainsMove

Operate trains for revenue.

**Location:** `app/minigames/operating_round.py`

**Attributes:**
- `company_id` (str): Operating company
- `routes` (List): Train routes

---

### PayDividendsMove

Pay dividends to shareholders.

**Location:** `app/minigames/operating_round.py`

**Attributes:**
- `company_id` (str): Company paying
- `amount` (int): Total dividend amount

---

### WithholdDividendsMove

Withhold revenue to company treasury.

**Location:** `app/minigames/operating_round.py`

**Attributes:**
- `company_id` (str): Company withholding

---

## Features

### Price History

Track all stock price changes with reasons and timestamps.

**Location:** `app/base.py` (PriceHistoryEntry, PublicCompany methods)

#### PriceHistoryEntry

**Attributes:**
- `round_number` (int): Game round
- `old_price` (int): Price before change
- `new_price` (int): Price after change
- `reason` (str): Why price changed
- `player_id` (str, optional): Who triggered change
- `timestamp` (str, optional): ISO timestamp

**Example:**
```python
history = company.get_price_history()
for entry in history:
    print(f"Round {entry.round_number}: {entry.reason}")
    print(f"  ${entry.old_price} → ${entry.new_price}")
```

---

### Logging

Structured logging system with context and performance tracking.

**Location:** `app/logging_config.py`

#### setup_logging

```python
setup_logging(
    level: str = 'INFO',
    debug_mode: bool = False,
    log_file: Optional[str] = None
) -> None
```

Configure application logging.

**Parameters:**
- `level`: Log level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
- `debug_mode`: Enable JSON output and verbose logging
- `log_file`: Optional file path for file logging

---

#### get_logger

```python
get_logger(name: str) -> ContextLogger
```

Get a logger with context support.

**Parameters:**
- `name`: Logger name (typically `__name__`)

**Returns:** ContextLogger instance

**Example:**
```python
from app.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Move executed", extra={'player': 'Alice', 'amount': 100})
```

---

#### PerformanceTimer

Context manager for timing operations.

**Example:**
```python
from app.logging_config import PerformanceTimer, get_logger

logger = get_logger(__name__)

with PerformanceTimer(logger, "Complex operation", player_id="Alice"):
    # ... operation ...
    pass
```

---

### Phase Validation

Validate and track game phase transitions.

**Location:** `app/phase_validation.py`

#### PhaseValidator

##### Constructor

```python
PhaseValidator(variant: str = "1830")
```

**Parameters:**
- `variant`: Game variant name

---

##### Methods

```python
can_transition(from_phase: str, to_phase: str) -> bool
```

Check if transition is valid.

---

```python
record_transition(from_phase: Optional[str], to_phase: str) -> None
```

Record a phase transition.

---

```python
validate_and_record(from_phase: Optional[str], to_phase: str) -> bool
```

Validate and record in one call.

---

```python
get_valid_next_phases(from_phase: str) -> Set[str]
```

Get all valid next phases from current phase.

---

```python
get_phase_summary() -> Dict[str, int]
```

Get summary of phase statistics.

---

```python
get_transition_history() -> List[PhaseTransition]
```

Get full transition history.

---

### Game History

Record and export move history.

**Location:** `app/game_history.py`

#### GameHistory

##### Methods

```python
initialize(variant: str, players: List[str]) -> None
```

Initialize with game metadata.

---

```python
record_move(
    move: Move,
    state: MutableGameState,
    success: bool,
    errors: Optional[List[str]] = None,
    phase: Optional[str] = None
) -> None
```

Record a move.

---

```python
export_json(filepath: str, pretty: bool = True) -> None
```

Export history to JSON file.

---

```python
get_moves_by_player(player_id: str) -> List[Dict[str, Any]]
```

Get all moves by specific player.

---

```python
get_moves_by_phase(phase: str) -> List[Dict[str, Any]]
```

Get all moves in specific phase.

---

```python
get_failed_moves() -> List[Dict[str, Any]]
```

Get all failed moves.

---

## Minigames

### Minigame Base Class

All minigames inherit from the `Minigame` class.

**Location:** `app/minigames/base.py`

#### Methods

```python
run(move: Move, state: MutableGameState) -> bool
```

Execute and validate a move.

---

```python
next(state: MutableGameState) -> str
```

Determine next phase.

---

```python
errors() -> List[str]
```

Get validation errors.

---

```python
onStart(state: MutableGameState) -> None
```

Called when phase starts.

---

```python
onComplete(state: MutableGameState) -> None
```

Called when phase completes.

---

```python
onTurnStart(state: MutableGameState) -> None
```

Called at start of each turn.

---

```python
onTurnComplete(state: MutableGameState) -> None
```

Called at end of each turn.

---

## Constants

### StockPurchaseSource

```python
from app.base import StockPurchaseSource

StockPurchaseSource.IPO  # Buy from IPO
StockPurchaseSource.BANK  # Buy from bank pool
```

### TerrainType

```python
from app.base import TerrainType

TerrainType.NORMAL    # 1x cost
TerrainType.MOUNTAIN  # 2x cost
TerrainType.BRIDGE    # 2x cost (1.5x in 1846)
TerrainType.TUNNEL    # 2x cost
```

### PowerType

```python
from app.base import PowerType

PowerType.EXTRA_TOKEN       # Additional token placement
PowerType.REVENUE_BONUS     # Bonus revenue on routes
PowerType.FREE_TRACK        # Free or discounted track laying
PowerType.TERRAIN_DISCOUNT  # Reduce terrain costs
PowerType.TRAIN_DISCOUNT    # Discount on train purchases
```

---

## Utility Functions

### apply_move

```python
apply_move(game: Game, move: Move) -> Game
```

Execute move on game (wrapper around game.performedMove).

**Location:** `app/state.py`

---

### validate_transition

```python
validate_transition(from_phase: str, to_phase: str, variant: str = "1830") -> Tuple[bool, Optional[str]]
```

Validate phase transition (standalone function).

**Location:** `app/phase_validation.py`

**Returns:** (is_valid, error_message)

---

### load_history_from_json

```python
load_history_from_json(filepath: str) -> GameHistory
```

Load game history from JSON file.

**Location:** `app/game_history.py`

---

## Type Hints

The codebase uses Python type hints throughout. Import common types:

```python
from typing import List, Dict, Set, Optional, Tuple
from app.base import Player, PublicCompany, PrivateCompany, Move
from app.base import MutableGameState, StockPurchaseSource
```

---

**Navigation:**
- [← Back to Main](README.md)
- [Frontend Integration Guide →](frontend_integration.md)
- [Examples →](examples/)
