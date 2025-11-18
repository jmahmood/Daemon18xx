# Round Flow Documentation - Daemon18xx

## Overview

This document explains how game phases (rounds) transition in Daemon18xx, covering Stock Rounds and Operating Rounds.

## Complete Game Flow Diagram

```
Game Start
    ↓
BuyPrivateCompany (Initial Auction)
    ↓
    ├─→ BiddingForPrivateCompany (if bidding occurs)
    │       ↓
    │   BuyPrivateCompany
    │       ↓
    └─────────→ StockRound
                    ↓
        ┌───────────┴───────────┐
        │    All Players Pass?   │
        └───────────┬───────────┘
                    │
         ┌─────────┼─────────┐
         NO        YES        │
         │          │         │
         │          ↓         │
         │   OperatingRound1  │
         │          │         │
         │   ┌──────┴──────┐  │
         │   │More Companies?│ │
         │   └──────┬──────┘  │
         │          │         │
         │      ┌───┼───┐     │
         │      YES  NO  │     │
         │      │    │   │     │
         │      │    ↓   │     │
         │      │  More OR?    │
         │      │    │   │     │
         │      │  ┌─┼───┴──┐  │
         │      │  YES    NO │  │
         │      │  │      │  │  │
         │      │  ↓      │  │  │
         │      │ OperatingRound2 │
         │      │  │      │  │  │
         │      │  ↓      ↓  ↓  │
         └──────┴──┴──────┴──┴──┘
                    │
                    ↓
              StockRound
                (repeat cycle)
```

## Detailed Phase Descriptions

### 1. StockRound

**Purpose:** Players buy and sell shares of public companies.

**Transitions:**
- **Stays in StockRound:** If not all players have passed
- **→ Auction:** If a player sells a private company (mid-game auction)
- **→ OperatingRound1:** When all players pass

**Transition Logic** (`StockRound.next()`):
```python
def next(self, kwargs: MutableGameState) -> str:
    # Check for private company auction
    if self.sell_private_company_auction:
        kwargs.auction = []
        return "Auction"

    # Check if all players have passed (one complete round)
    if (kwargs.stock_round_play % len(players) == 0 and
        kwargs.stock_round_play > 0 and
        kwargs.stock_round_passed == len(players)):

        # Rotate priority deal player
        if self.last_deal_player:
            idx = players.index(self.last_deal_player)
            kwargs.priority_deal_player = players[(idx + 1) % len(players)]

        return "OperatingRound1"

    return "StockRound"
```

**Key State Variables:**
- `stock_round_play`: Number of player actions taken
- `stock_round_passed`: Number of players who have passed
- `priority_deal_player`: Player who acts first (rotates each round)
- `last_deal_player`: Last player to buy/sell stock

**Initialization** (`StockRound.onStart()`):
- Appends new dictionaries to `purchases[]` and `sales[]`
- Resets `stock_round_play` and `stock_round_passed` to 0
- Does NOT increment `stock_round_count` (that happens in `onComplete()`)

**Completion** (`StockRound.onComplete()`):
- Checks all companies for price increases
- Clears `sold_this_round` for all players
- Increments `stock_round_count` for next round

### 2. OperatingRound (ORx)

**Purpose:** Floated companies operate trains, lay track, place tokens, and pay dividends.

**Transitions:**
- **Stays in OperatingRound1:** If more companies are waiting in current round
- **→ OperatingRound2:** If current round complete but more rounds remain
- **→ OperatingRound3:** (if applicable, depends on game phase)
- **→ TrainsRusted:** If trains rust and company has no valid trains
- **→ StockRound:** When all operating rounds complete

**Transition Logic** (`OperatingRound.next()`):
```python
def next(self, **kwargs) -> str:
    # Check for rusted trains requiring emergency purchase
    if self.rusted_train_type:
        for pc in public_companies:
            pc.removeRustedTrains(self.rusted_train_type)
            if pc.hasNoTrains() and not pc.hasValidRoute(board):
                return "TrainsRusted"
        self.rusted_train_type = None

    # Continue same round if more companies waiting
    if kwargs.get("playerTurn").anotherCompanyWaiting():
        return f"OperatingRound{kwargs.get('currentOperatingRound')}"

    # Move to next operating round if more rounds remain
    if (not kwargs.get("playerTurn").anotherCompanyWaiting() and
        kwargs.get("currentOperatingRound") < kwargs.get("totalOperatingRounds")):

        current_or = kwargs.get("currentOperatingRound") + 1
        kwargs["currentOperatingRound"] = current_or
        kwargs.get("playerTurn").restart(current_or)
        return f"OperatingRound{current_or}"

    # All operating rounds complete - return to Stock Round
    return "StockRound"
```

**Key State Variables:**
- `operating_order`: List of company IDs in operating order (sorted by stock price)
- `currentOperatingRound`: Current OR number (1, 2, or 3)
- `totalOperatingRounds`: Total ORs for this set (depends on game phase)
- `track_laid`: Set of companies that laid track this round

**Initialization** (`OperatingRound.onStart()`):
- Distributes revenue from private companies
- Resets `track_laid` set
- Resets `token_placed` flag for all companies
- Accrues loan interest on company loans
- **Calls `game.sort_operating_order()`** to populate operating order

**Operating Order Sorting** (`game.sort_operating_order()`):
```python
def sort_operating_order(self) -> List[str]:
    # Get floated, non-bankrupt companies
    companies = [
        c for c in self.state.public_companies
        if c.isFloated() and not c.bankrupt
    ]

    # Sort by: stock price (desc), row, prior order
    companies.sort(
        key=lambda c: (
            -market.cell(*c.stock_pos).price,  # Highest price first
            c.stock_pos[0],                     # Row (lower first)
            prior_index(c.id)                   # Maintain stable order
        )
    )

    self.operating_order = [c.id for c in companies]
    return self.operating_order
```

### 3. TrainsRusted

**Purpose:** Emergency train purchase when a company has no valid trains after rusting.

**Transitions:**
- **→ OperatingRound{N}:** After successful train purchase
- **→ StockRound:** If company goes bankrupt

**Transition Logic** (`TrainsRusted.next()`):
```python
def next(self, **kwargs) -> str:
    current_or = kwargs.get("currentOperatingRound", "")
    if self.bankrupt:
        return "StockRound"
    return f"OperatingRound{current_or}"
```

**Emergency Purchase Process:**
1. Company must buy a train immediately
2. If company cash insufficient, president loans money (10% interest)
3. If loan insufficient, president must sell shares
4. If still can't afford, company goes bankrupt

### 4. Auction (Mid-Game Private Company Sale)

**Purpose:** Mid-game auction when a player sells a private company.

**Transitions:**
- **→ StockRound:** After auction completes

**Key Points:**
- Triggered by `SELL_PRIVATE_COMPANY` move during Stock Round
- Uses same auction mechanics as initial private company auction
- Returns to Stock Round when complete

## Phase Normalization

The phase validator normalizes numbered operating rounds for validation:

```python
@staticmethod
def normalize_phase(phase: str) -> str:
    """Normalize phase names for validation.

    OperatingRound1 → OperatingRound
    OperatingRound2 → OperatingRound
    OperatingRound3 → OperatingRound
    StockRound → StockRound (unchanged)
    """
    if phase and phase.startswith("OperatingRound"):
        return "OperatingRound"
    return phase
```

This allows the validator to accept:
- `StockRound → OperatingRound1` ✓
- `OperatingRound1 → OperatingRound2` ✓
- `OperatingRound2 → StockRound` ✓

While still maintaining numbered phases in the actual game state.

## Valid Phase Transitions

```
VALID_TRANSITIONS = {
    "BuyPrivateCompany": {"StockRound", "BiddingForPrivateCompany"},
    "BiddingForPrivateCompany": {"BuyPrivateCompany", "StockRound"},
    "StockRound": {"OperatingRound", "StockRound", "Auction"},
    "Auction": {"StockRound"},
    "OperatingRound": {"StockRound", "OperatingRound"},
}
```

Note: `OperatingRound` is the normalized form used in validation.

## Example Game Flow

### Typical 1889 Game (2 Operating Rounds per Set)

```
1. BuyPrivateCompany (initial auction)
     ↓
2. StockRound #1 (players buy shares)
     ↓
3. OperatingRound1 (companies operate - first time)
     ↓
4. OperatingRound2 (companies operate - second time)
     ↓
5. StockRound #2 (players trade shares)
     ↓
6. OperatingRound1 (companies operate)
     ↓
7. OperatingRound2 (companies operate)
     ↓
8. StockRound #3
     ↓
   ... (cycle continues until game end)
```

### With Train Rusting

```
1. StockRound #5
     ↓
2. OperatingRound1
     ├─→ Company A operates normally
     ├─→ Company B operates normally
     ├─→ Company C buys 4-train (rusts 2-trains)
     └─→ Company D has no valid trains
           ↓
3. TrainsRusted
     ├─→ Company D president loans money
     ├─→ Company D buys new train
     └─→ Returns to OperatingRound1
           ↓
4. OperatingRound1 (continues)
     ↓
5. OperatingRound2
     ↓
6. StockRound #6
```

## Testing

All round transitions are validated by comprehensive tests in `test_FullGameFlowIntegration.py`:

1. **test_full_cycle_stock_to_operating_to_stock()** - Complete SR → OR → SR cycle
2. **test_operating_order_sorting()** - Operating order population and sorting
3. **test_phase_validator_accepts_transitions()** - Phase validation
4. **test_round_transition_logic()** - Detailed next() logic for all transitions

**Test Results:** ✅ All 4 integration tests pass (75/75 total tests passing)

## Implementation Notes

### Critical Requirements

1. **OperatingRound.onStart() must receive `game=self`**
   - Required to call `game.sort_operating_order()`
   - Sets `operating_order` list with floated companies

2. **StockRound signatures accept `**extra_kwargs`**
   - Allows game kwarg to be passed through
   - Maintains compatibility with varied calling patterns

3. **Phase normalization before validation**
   - Validator normalizes `OperatingRound1/2/3` → `OperatingRound`
   - Actual game uses numbered phases for tracking

4. **setPlayerOrder() handles None for operating rounds**
   - Operating rounds don't use player order (companies operate, not players)
   - Returns early instead of attempting to call None

### Round Count Indexing

**Stock Round Count (0-based):**
```python
# First stock round
stock_round_count = 0
purchases[0] = {}  # ✓ Direct indexing
sales[0] = {}

# Increment happens in onComplete(), NOT onStart()
StockRound.onComplete(state)
# stock_round_count = 1
```

**Operating Round Count (1-based):**
```python
# First operating round
currentOperatingRound = 1
totalOperatingRounds = 2

# Increments when transitioning to next OR
if currentOperatingRound < totalOperatingRounds:
    currentOperatingRound += 1  # Now 2
    return "OperatingRound2"
```

## Debugging Tips

### Check Phase Transitions

```python
# View phase validator history
validator.get_transition_history()
# Returns: [PhaseTransition(from, to, timestamp, ...)]

# Check valid next phases
validator.get_valid_next_phases("StockRound")
# Returns: {'OperatingRound', 'StockRound', 'Auction'}
```

### Verify Operating Order

```python
# After OperatingRound.onStart()
print(game.operating_order)
# ['IR', 'AR', 'SR', ...]  # Company IDs in order

# Check sorting criteria
for company in state.public_companies:
    if company.isFloated():
        price = config.STOCK_MARKET.cell(*company.stock_pos).price
        print(f"{company.id}: ${price} at {company.stock_pos}")
```

### Monitor Round State

```python
# Stock Round
print(f"Round: {state.stock_round_count}")
print(f"Play: {state.stock_round_play}")
print(f"Passed: {state.stock_round_passed}/{len(state.players)}")

# Operating Round
print(f"Current OR: {currentOperatingRound}/{totalOperatingRounds}")
print(f"Operating order: {game.operating_order}")
print(f"Companies left: {playerTurn.anotherCompanyWaiting()}")
```

## Related Files

- `app/minigames/StockRound/minigame_stockround.py` - Stock Round logic
- `app/minigames/operating_round.py` - Operating Round logic
- `app/phase_validation.py` - Phase transition validation
- `app/state.py` - Game state management, setMinigame(), sort_operating_order()
- `app/unittests/test_FullGameFlowIntegration.py` - Integration tests

## See Also

- [Phase Validation Documentation](app/phase_validation.py) - Detailed validation rules
- [Stock Round Implementation](STOCK_ROUND_IMPLEMENTATION.md) - Stock Round specifics
- [Test Suite](app/unittests/) - Comprehensive test coverage
