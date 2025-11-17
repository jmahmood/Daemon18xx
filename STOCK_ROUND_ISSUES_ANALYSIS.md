# Stock Round Issues Analysis

## Critical Issues Found

### 1. **CRITICAL BUG: Player Not Paid When Selling Stock**

**Location:** `app/minigames/StockRound/minigame_stockround.py:46-57`

**Problem:**
The `_sellround()` method calls `company.sell(player, amount)` but never credits cash to the player.

```python
def _sellround(self, move: StockRoundMove, kwargs: MutableGameState) -> None:
    sale_history = kwargs.sales[kwargs.stock_round_count]
    for company, amount in move.for_sale:
        company.sell(move.player, amount)  # ❌ Only updates ownership, doesn't pay player
        company.priceDown(amount)
        company.checkPresident()
        move.player.sold_this_round.add(company)
        # ... history tracking
```

The `PublicCompany.sell()` method explicitly states at line 615:
```python
# Player has to get paid for this, this is not handled by this class.
```

**Impact:**
- Players can sell stock but receive $0
- This breaks the entire economy - players lose money without receiving payment
- Game becomes unplayable

**Fix Required:**
```python
def _sellround(self, move: StockRoundMove, kwargs: MutableGameState) -> None:
    sale_history = kwargs.sales[kwargs.stock_round_count]
    for company, amount in move.for_sale:
        # Calculate payment BEFORE selling (in case price changes)
        price_per_share = company.stockPrice[StockPurchaseSource.BANK]
        payment = (amount / 10) * price_per_share  # amount is in %, price is per 10%

        company.sell(move.player, amount)
        move.player.cash += payment  # ✅ Pay the player!
        company.priceDown(amount)
        company.checkPresident()
        move.player.sold_this_round.add(company)
        # ... history tracking
```

---

### 2. **POTENTIAL BUG: BUYSELL Order May Be Wrong**

**Location:** `app/minigames/StockRound/minigame_stockround.py:59-68`

**Problem:**
The `_buysell()` method calls `_buyround()` first, then `_sellround()`:

```python
def _buysell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
    if not self.validateBuy(move, kwargs) or not self.validateSales(move, kwargs):
        return False
    elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
        return False
    self._buyround(move, kwargs)   # ❌ BUY FIRST
    self._sellround(move, kwargs)  # ❌ SELL SECOND
    # ...
```

**Expected Behavior:**
In real 18xx games, you typically **SELL FIRST, THEN BUY**, so you can use the proceeds from sales to fund purchases.

**Impact:**
- Players can't use sale proceeds to buy stock in the same turn
- Validation may incorrectly reject valid moves (player appears to not have enough cash during buy validation, but would have cash after selling)

**Fix Required:**
```python
def _buysell(self, move: StockRoundMove, kwargs: MutableGameState) -> bool:
    if not self.validateBuy(move, kwargs) or not self.validateSales(move, kwargs):
        return False
    elif self.isFirstPurchase(move) and not self.validateFirstPurchase(move):
        return False
    self._sellround(move, kwargs)  # ✅ SELL FIRST
    self._buyround(move, kwargs)   # ✅ BUY SECOND
    kwargs.stock_round_play += 1
    self.last_deal_player = move.player
    return True
```

**Validation Issue:**
The validation at line 60 checks `validateBuy()` BEFORE the sell happens, so it will reject moves where the player needs sale proceeds to afford the purchase. This needs to be reconsidered or the validation needs to account for future cash from sales.

---

### 3. **EDGE CASE: President Share Dumping Without Replacement**

**Location:** `app/minigames/StockRound/minigame_stockround.py:265-297`

**Problem:**
The `_validateSale()` method checks if there are potential replacement presidents:

```python
err(
    len(company.potentialPresidents() - {player}) > 0 or my_stock - amount >= 20,
    "There are no other potential presidents, so you can't sell your shares..."
)
```

**Edge Case:**
What happens if a president tries to sell shares when:
- No other player owns >= 20%
- The president would drop below 20% after the sale
- But another player would become the new largest shareholder (even though < 20%)

**Current Behavior:**
The validation BLOCKS the sale because `len(company.potentialPresidents() - {player}) == 0`.

**18xx Rules Clarification Needed:**
- Some 18xx variants require the president to ALWAYS own the president cert (20%)
- Other variants allow presidency to "dump" if no one owns 20%, leaving the company in receivership
- Need to verify which rule applies to 1889

**Potential Impact:**
- May block legitimate sales
- May not handle bankruptcy/receivership scenarios correctly

---

### 4. **POTENTIAL BUG: Stock Round Count Initialization**

**Location:** `app/base.py:50`

**Problem:**
`MutableGameState.__init__()` initializes `stock_round_count = 0`, and `StockRound.onStart()` increments it to 1.

```python
# In MutableGameState.__init__
self.stock_round_count: int = 0

# In StockRound.onStart()
kwargs.stock_round_count += 1  # First round becomes round 1
```

**Array Access Issue:**
The code accesses `kwargs.purchases[kwargs.stock_round_count]` and `kwargs.sales[kwargs.stock_round_count]`.

- Round 1: Accesses index 1 (but onStart() only appended 1 item, at index 0)
- This will cause **IndexError** on first stock round!

**Fix Required:**
Either:
1. Don't increment `stock_round_count` in `onStart()` (keep it 0-indexed)
2. Or use `stock_round_count - 1` when accessing arrays

**Recommended Fix:**
```python
# Option 1: Keep stock_round_count 0-indexed
@staticmethod
def onStart(kwargs: MutableGameState) -> None:
    # DON'T increment here, just initialize tracking
    kwargs.purchases.append({})
    kwargs.sales.append({})
    kwargs.stock_round_passed = 0
    kwargs.stock_round_play = 0
    # stock_round_count stays at 0 for first round

# Then access as:
purchase_history = kwargs.purchases[kwargs.stock_round_count]  # Index 0 for first round
```

---

### 5. **Missing Cash Payment in Sell (Related to Issue #1)**

**Location:** Multiple places in `app/base.py`

**Problem:**
The `PublicCompany.sell()` method only updates ownership and bank pool, but doesn't handle cash:

```python
def sell(self, player: Player, amount: int):
    self.owners[player] = self.owners.get(player, 0) - amount
    # Player has to get paid for this, this is not handled by this class.
    self.stocks[StockPurchaseSource.BANK] += amount
```

Similarly, `Player` class has no `removeFromPortfolio()` method to handle receiving cash from sales.

**Architectural Issue:**
The `buy()` method is asymmetric with `sell()`:
- `buy()` handles BOTH ownership AND cash (`player.addToPortfolio()` subtracts cash)
- `sell()` only handles ownership, not cash

**Fix Required:**
Either:
1. Add a `Player.removeFromPortfolio()` method that adds cash
2. Or handle cash explicitly in `StockRound._sellround()`

**Recommended Approach:**
Keep the asymmetry but document it clearly, and fix `_sellround()` to handle payment (as shown in Issue #1).

---

## Non-Critical Issues

### 6. **Bank Pool Limit Edge Case**

**Location:** `app/minigames/StockRound/minigame_stockround.py:283-289`

**Issue:**
The validation checks if selling would exceed the bank pool limit:

```python
err(
    company.availableStock(StockPurchaseSource.BANK) + amount <= BANK_POOL_LIMIT,
    "You can't sell that much ({}); the bank can only have {} shares max.",
    amount, BANK_POOL_LIMIT,
),
```

**Question:**
What should happen if the bank pool is full?
- Block the sale entirely? (current behavior)
- Allow partial sale up to the limit?
- Force company into bankruptcy?

**Recommendation:**
Current behavior (block sale) is correct for most 18xx variants. Document this explicitly.

---

### 7. **First Stock Round Restriction**

**Location:** `app/minigames/StockRound/minigame_stockround.py:230-231`

**Issue:**
Selling is blocked in the first stock round:

```python
err(kwargs.stock_round_count > 1,
    "You can only sell after the first stock round.")
```

**Problem with Issue #4:**
If `stock_round_count` starts at 1 (after increment in `onStart()`), this check becomes:
- Stock round 1: `stock_round_count == 1`, so `1 > 1` is False → **Can't sell in round 1** ✅ CORRECT
- Stock round 2: `stock_round_count == 2`, so `2 > 1` is True → **Can sell in round 2** ✅ CORRECT

But if we fix Issue #4 to use 0-indexing:
- Stock round 0: `0 > 1` is False → Can't sell ✅
- Stock round 1: `1 > 1` is False → **Can't sell in round 2!** ❌ WRONG

**Fix Required if using 0-indexing:**
```python
err(kwargs.stock_round_count >= 1,  # Allow selling from round 1 onwards (second round)
    "You can only sell after the first stock round.")
```

---

## Testing Recommendations

### Critical Path Tests Needed:

1. **Test selling stock:**
   ```python
   # Player sells stock and receives cash
   initial_cash = player.cash
   company_price = company.stockPrice[StockPurchaseSource.BANK]
   # Sell 10% at $100/share
   move = StockRoundMove(move_type=SELL, for_sale=[(company, 10)])
   game.performedMove(move)
   assert player.cash == initial_cash + company_price  # ✅ Player gets paid
   ```

2. **Test BUYSELL order:**
   ```python
   # Player has $100, company sells for $50, company buys for $120
   player.cash = 100
   # Without sell-first, this should fail validation
   # With sell-first, player gets $50, then buys for $120 (has $150)
   move = StockRoundMove(move_type=BUYSELL, for_sale=[(companyA, 10)], public_company=companyB)
   game.performedMove(move)
   assert player.cash == 100 + 50 - 120 == 30  # ✅ Sell proceeds used for buy
   ```

3. **Test stock round count indexing:**
   ```python
   # First stock round
   game = Game.start(["Alice", "Bob"], "1889")
   # Trigger stock round transition
   assert game.state.stock_round_count == 0  # or 1, depending on fix
   # Make a purchase
   move = StockRoundMove(move_type=BUY, ...)
   game.performedMove(move)
   # Should not crash with IndexError
   assert len(game.state.purchases) > game.state.stock_round_count
   ```

4. **Test president dumping:**
   ```python
   # President owns 30%, no one else owns >= 20%
   # President tries to sell to 15%
   # Should fail validation OR transfer to highest shareholder
   ```

5. **Test first round sell restriction:**
   ```python
   # First stock round
   move = StockRoundMove(move_type=SELL, for_sale=[(company, 10)])
   assert not game.isValidMove(move)  # Should be blocked

   # Second stock round
   # ... advance to next stock round
   move = StockRoundMove(move_type=SELL, for_sale=[(company, 10)])
   assert game.isValidMove(move)  # Should be allowed
   ```

---

## Summary

### Must Fix (Breaks Gameplay):
1. ✅ **Issue #1**: Player not paid when selling stock
2. ✅ **Issue #4**: Stock round count array indexing error

### Should Fix (Incorrect Behavior):
3. ✅ **Issue #2**: BUYSELL order (sell should come before buy)

### Consider/Verify:
4. ⚠️ **Issue #3**: President dumping edge case (verify 1889 rules)
5. ⚠️ **Issue #7**: First round restriction interaction with stock_round_count fix

### Document Only:
6. 📝 **Issue #6**: Bank pool limit behavior (current implementation is correct)
7. 📝 **Issue #5**: Architectural asymmetry between buy/sell (acceptable design)
