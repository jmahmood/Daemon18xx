# Stock Round Implementation Guide

## Overview
This document outlines the requirements and implementation steps for adding Stock Round functionality to the Daemon18xx multiplayer web application.

---

## 1. Game Flow & Rules

### Stock Round Basics
- **Turn Order**: Players take turns in sequence (same as private auction)
- **Round Ends When**: All players pass in succession
- **Next Phase**: Operating Round 1

### Valid Actions Per Turn
A player may choose ONE of the following:

1. **BUY** - Purchase 1 share (10%) of a public company
   - From IPO (Initial Public Offering) - money goes to company
   - From Bank Pool - money goes to bank
   - First purchase requires buying President's certificate (20%) and setting IPO price

2. **SELL** - Sell shares you own
   - Can sell multiple companies in one turn
   - Cannot sell and buy the same company in one turn
   - Cannot sell president's certificate unless you have another 10% to replace it
   - Stock price decreases when you sell

3. **BUYSELL** - Sell first, then buy (in that order)
   - Sell shares from company A
   - Buy shares from company B (must be different company)
   - Useful for freeing up cash or certificate slots

4. **PASS** - Skip your turn
   - When all players pass consecutively, round ends

5. **SELL_PRIVATE_COMPANY** - Auction your private company
   - Triggers a mini-auction phase
   - Other players can bid
   - Not implemented in initial version (future enhancement)

---

## 2. Backend Implementation

### 2.1 Data Structures

#### StockRoundMove Format
```python
{
    "move_type": "BUY" | "SELL" | "BUYSELL" | "PASS" | "SELL_PRIVATE_COMPANY",
    "player_id": "player-uuid",

    # For BUY/BUYSELL moves:
    "public_company_id": "AR" | "IR" | "SR" | etc,
    "source": "IPO" | "BANK",
    "ipo_price": 100,  # Only for first purchase (president's cert)

    # For SELL/BUYSELL moves:
    "for_sale_raw": [
        ["AR", 10],  # [company_id, amount]
        ["IR", 20]
    ]
}
```

### 2.2 Server Changes (server.py)

#### Update construct_move()
```python
def construct_move(move_type: str, move_data: Dict[str, Any]):
    """Construct a Move object from type and data"""
    from app.base import Move

    if move_type == "BuyPrivateCompanyMove":
        # ... existing code ...

    elif move_type == "StockRoundMove":
        base_move = Move()
        base_move.msg = json.dumps(move_data)
        base_move.player_id = move_data.get('player_id')
        return StockRoundMove.fromMove(base_move)

    # ... rest of move types ...
```

#### Update make_move event handler
The existing handler should work, but verify:
- Move validation happens via `apply_move()`
- State is serialized and broadcast
- Turn advances automatically

### 2.3 Serialization Updates (game_serializer.py)

#### Add to serialize_game_state_only()
```python
# Add stock market data
if hasattr(game.state, 'stock_market') and game.state.stock_market:
    state['stock_market'] = serialize_stock_market(game.state.stock_market)

# Enhance public companies serialization
state['public_companies'] = [
    {
        'id': c.id,
        'name': c.name,
        'short_name': c.short_name,
        'floated': c.isFloated(),
        'ipo_price': c.stockPrice.get(StockPurchaseSource.IPO, 0),
        'market_price': c.stockPrice.get(StockPurchaseSource.BANK, 0),
        'ipo_shares': c.stocks.get(StockPurchaseSource.IPO, 0),
        'bank_shares': c.stocks.get(StockPurchaseSource.BANK, 0),
        'president': c.president.name if c.president else None,
        'president_id': c.president.id if c.president else None,
        'cash': c.cash if c.cash else 0,
        'stock_position': c.stock_pos,
        'shareholders': {
            player.name: amount
            for player, amount in c.owners.items()
        }
    }
    for c in game.state.public_companies
]

# Add player stock holdings
state['players'] = [
    {
        'id': p.id,
        'name': p.name,
        'cash': p.cash,
        'order': p.order,
        'certificates': p.getCertificateCount(),
        'holdings': {
            company.short_name: amount
            for company, amount in p.getStockHoldings()
        }
    }
    for p in game.state.players
]
```

---

## 3. Frontend Implementation

### 3.1 New Component: StockRound.ts

Create `/multiplayer/frontend/src/components/StockRound.ts`

#### Component Structure
```typescript
export class StockRound {
  private element: HTMLElement | null = null;
  private gameState: any = null;
  private currentPlayerId: string | null = null;
  private onMakeMove?: (moveData: any) => void;

  constructor(options: { onMakeMove?: (moveData: any) => void }) {
    this.onMakeMove = options.onMakeMove;
  }

  render(): HTMLElement {
    // Create main container with sections:
    // 1. Turn indicator (YOUR TURN / Waiting for X)
    // 2. Available companies grid
    // 3. Your holdings summary
    // 4. Action buttons (Buy/Sell/Pass)
  }

  updateGameState(gameState: any): void {
    // Update component with new game state
  }

  setCurrentPlayer(playerId: string): void {
    // Set who is viewing this component
  }
}
```

#### UI Sections

**1. Turn Indicator**
```
┌─────────────────────────────────────┐
│  🎯 YOUR TURN - Choose an action    │
└─────────────────────────────────────┘
```
or
```
┌─────────────────────────────────────┐
│  Waiting for Alice to make a move   │
└─────────────────────────────────────┘
```

**2. Available Companies Grid**
```
┌──────────────────┬──────────────────┬──────────────────┐
│ AR - Awa Railroad│ IR - Iyo Railway │ SR - Sanuki Rail │
│                  │                  │                  │
│ IPO: $100/share  │ IPO: Not started │ IPO: $90/share   │
│ Available: 8     │ Available: 10    │ Available: 5     │
│                  │                  │                  │
│ Bank: $95/share  │ Bank: N/A        │ Bank: $90/share  │
│ Available: 2     │                  │ Available: 1     │
│                  │                  │                  │
│ President: Alice │ President: —     │ President: Bob   │
│ Floated: Yes     │ Floated: No      │ Floated: Yes     │
│                  │                  │                  │
│ [Buy from IPO]   │ [Start Company]  │ [Buy from IPO]   │
│ [Buy from Bank]  │                  │ [Buy from Bank]  │
└──────────────────┴──────────────────┴──────────────────┘
```

**3. Your Holdings Panel**
```
┌─────────────────────────────────────┐
│ Your Stock Holdings                 │
├─────────────────────────────────────┤
│ AR: 20% (President)                 │
│ IR: 10%                             │
│ SR: 30% (President)                 │
│                                     │
│ Total Certificates: 6 / 20          │
│ Cash: $350                          │
└─────────────────────────────────────┘
```

**4. Action Area** (shown when it's your turn)
```
┌─────────────────────────────────────┐
│ SELECT ACTION                       │
├─────────────────────────────────────┤
│ [📈 Buy Stock]                      │
│ [📉 Sell Stock]                     │
│ [⏭️ Pass]                           │
└─────────────────────────────────────┘
```

### 3.2 Buy Stock Flow

When player clicks "Buy from IPO" on a company:

1. **For Non-Started Companies (First Purchase)**:
   ```
   ┌───────────────────────────────────┐
   │ Start Awa Railroad                │
   ├───────────────────────────────────┤
   │ You will become President         │
   │ Cost: 20% shares                  │
   │                                   │
   │ Select IPO Price:                 │
   │ ○ $100                            │
   │ ○ $90                             │
   │ ○ $82                             │
   │ ○ $76                             │
   │ ○ $71                             │
   │ ○ $67                             │
   │                                   │
   │ Total Cost: $XXX                  │
   │                                   │
   │ [Confirm]  [Cancel]               │
   └───────────────────────────────────┘
   ```

2. **For Started Companies (Regular Purchase)**:
   ```
   ┌───────────────────────────────────┐
   │ Buy Stock - Awa Railroad          │
   ├───────────────────────────────────┤
   │ Amount: 10% (1 certificate)       │
   │ Price: $100 per share             │
   │ Total Cost: $100                  │
   │                                   │
   │ [Confirm Purchase]  [Cancel]      │
   └───────────────────────────────────┘
   ```

### 3.3 Sell Stock Flow

When player clicks "Sell Stock":

```
┌───────────────────────────────────┐
│ Sell Stock                        │
├───────────────────────────────────┤
│ Select shares to sell:            │
│                                   │
│ AR - Awa Railroad                 │
│ You own: 20% (President)          │
│ ☐ Sell 10% @ $95 = $95           │
│                                   │
│ IR - Iyo Railway                  │
│ You own: 10%                      │
│ ☑ Sell 10% @ $88 = $88           │
│                                   │
│ Total Proceeds: $88               │
│                                   │
│ [Confirm Sale]  [Cancel]          │
└───────────────────────────────────┘
```

### 3.4 Integration with App.ts

Update `app.ts` to show StockRound component:

```typescript
// In constructor
this.stockRound = new StockRound({
  onMakeMove: (moveData: any) => this.handleStockRoundMove(moveData)
});

// In buildMainUI() - update auction panel setup
const auctionPanel = document.createElement('div');
auctionPanel.className = 'tab-panel active';
auctionPanel.dataset.tab = 'auction';
auctionPanel.id = 'auction-panel';
// Initially empty, filled by updateUI based on phase

// In updateUI()
const phase = this.gameState.phase;
const auctionPanel = document.getElementById('auction-panel');

if (phase === 'StockRound') {
  // Clear and show stock round UI
  if (auctionPanel && !auctionPanel.querySelector('.stock-round-container')) {
    auctionPanel.innerHTML = '';
    auctionPanel.appendChild(this.stockRound.render());
  }

  // Update with current state
  if (this.myPlayerName && this.gameState.players) {
    const myPlayer = this.gameState.players.find((p: any) => p.name === this.myPlayerName);
    if (myPlayer) {
      this.stockRound.setCurrentPlayer(myPlayer.id);
    }
  }
  this.stockRound.updateGameState(this.gameState);

} else if (phase === 'BuyPrivateCompany' || phase === 'BiddingForPrivateCompany') {
  // ... existing auction code ...
}

// Add handler
private handleStockRoundMove(moveData: any) {
  console.log('🎯 Stock Round move:', moveData);
  socketService.makeMove('StockRoundMove', moveData);
}
```

---

## 4. CSS Styling

Add to `/multiplayer/frontend/index.html`:

```css
/* Stock Round Styles */
.stock-round-container {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.company-card {
  background: var(--background-tertiary);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  padding: 15px;
  transition: all 0.2s;
}

.company-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.company-card.not-started {
  border-color: var(--warning-color);
}

.company-card.floated {
  border-color: var(--success-color);
}

.stock-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.stock-btn {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 6px;
}

.buy-stock-btn {
  background: var(--success-color);
}

.sell-stock-btn {
  background: var(--danger-color);
}

.holdings-panel {
  background: var(--background-secondary);
  border-radius: 12px;
  padding: 20px;
  margin: 20px 0;
}

.holding-item {
  padding: 10px;
  margin: 8px 0;
  background: var(--background-tertiary);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
}

.president-badge {
  background: var(--warning-color);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  margin-left: 8px;
}
```

---

## 5. Testing Checklist

### 5.1 Backend Tests
- [ ] Move construction works for all StockRoundType variants
- [ ] BUY move: First purchase (president's cert) sets IPO price correctly
- [ ] BUY move: Regular purchase deducts cash and transfers shares
- [ ] SELL move: Shares transfer to bank pool, cash increases, price drops
- [ ] BUYSELL move: Can sell A and buy B in one turn
- [ ] BUYSELL move: Cannot sell and buy same company
- [ ] PASS move: Increments pass counter
- [ ] Round ends when all players pass consecutively
- [ ] Turn order rotates correctly
- [ ] Priority deal player updates for next round

### 5.2 Frontend Tests
- [ ] Company grid displays all 7 public companies
- [ ] Non-started companies show "Start Company" button
- [ ] Started companies show IPO and Bank purchase options
- [ ] Buy modal validates sufficient cash
- [ ] Buy modal validates certificate limit
- [ ] Sell modal shows only owned stocks
- [ ] Sell modal prevents selling president cert without replacement
- [ ] Turn indicator shows correctly for each player
- [ ] Move broadcasts update all players' UIs
- [ ] Stock prices update visually after trades

### 5.3 Integration Tests
- [ ] Private auction → Stock Round transition works
- [ ] Stock Round → Operating Round transition works
- [ ] Multiple stock rounds in succession work
- [ ] Priority deal player rotates correctly between rounds
- [ ] Game state persists correctly across rounds
- [ ] Reconnecting players see correct state

---

## 6. Implementation Order

### Phase 1: Backend Foundation
1. Update `construct_move()` in server.py for StockRoundMove
2. Test move creation with sample data
3. Verify serialization includes all stock data
4. Test round completion and phase transition

### Phase 2: Basic Frontend
1. Create StockRound.ts component skeleton
2. Implement company grid display (read-only)
3. Implement holdings panel display
4. Add turn indicator
5. Test UI updates with mock data

### Phase 3: Buy Functionality
1. Implement "Start Company" flow (first purchase)
2. Implement regular buy from IPO
3. Implement buy from Bank
4. Add validation (cash, certificates)
5. Test end-to-end buy flow

### Phase 4: Sell Functionality
1. Implement sell stock modal
2. Add validation (president cert, sold_this_round)
3. Test sell flow
4. Implement BUYSELL combined flow

### Phase 5: Pass & Round End
1. Implement PASS action
2. Test round completion detection
3. Verify transition to Operating Round
4. Test priority deal player rotation

### Phase 6: Polish
1. Add loading states
2. Add error handling
3. Add sound effects
4. Improve visual feedback
5. Add animations

---

## 7. Known Limitations & Future Work

### Not Implemented in V1
- SELL_PRIVATE_COMPANY auction flow
- Stock market price visualization
- Operating rounds (future phases)
- Train purchases
- Route running
- Dividend payments

### Future Enhancements
- Visual stock chart showing price history
- Company detail modal with full financials
- Certificate limit warning indicator
- Undo last action (before confirm)
- AI player recommendations
- Tutorial mode for new players

---

## 8. Key Files Reference

### Backend
- `/multiplayer/backend/server.py` - WebSocket handlers, move processing
- `/multiplayer/backend/game_serializer.py` - State serialization
- `/app/minigames/StockRound/minigame_stockround.py` - Stock round logic
- `/app/minigames/StockRound/move.py` - Move structure
- `/app/minigames/StockRound/enums.py` - Move types
- `/app/minigames/StockRound/const.py` - Game constants

### Frontend
- `/multiplayer/frontend/src/components/StockRound.ts` - Main component (TO CREATE)
- `/multiplayer/frontend/src/app.ts` - App orchestration
- `/multiplayer/frontend/src/types.ts` - TypeScript interfaces
- `/multiplayer/frontend/index.html` - CSS styles

### Game Engine
- `/app/base.py` - Core classes (Player, PublicCompany, etc.)
- `/app/state.py` - Game state management

---

## 9. Example Move Payloads

### Buy Stock (Regular)
```json
{
  "move_type": "BUY",
  "player_id": "abc-123-def",
  "public_company_id": "AR",
  "source": "IPO"
}
```

### Buy Stock (First Purchase / Start Company)
```json
{
  "move_type": "BUY",
  "player_id": "abc-123-def",
  "public_company_id": "AR",
  "source": "IPO",
  "ipo_price": 100
}
```

### Sell Stock
```json
{
  "move_type": "SELL",
  "player_id": "abc-123-def",
  "for_sale_raw": [
    ["AR", 10],
    ["IR", 20]
  ]
}
```

### Buy and Sell
```json
{
  "move_type": "BUYSELL",
  "player_id": "abc-123-def",
  "public_company_id": "SR",
  "source": "BANK",
  "for_sale_raw": [
    ["AR", 10]
  ]
}
```

### Pass
```json
{
  "move_type": "PASS",
  "player_id": "abc-123-def"
}
```

---

## End of Document

This implementation guide provides a complete roadmap for adding Stock Round functionality to the multiplayer Daemon18xx application. Follow the phases in order, testing thoroughly at each step.
