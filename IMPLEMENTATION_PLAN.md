# Daemon18xx Implementation Plan

## Repository Survey Summary

**Date:** 2025-11-17
**Current Status:** Well-structured 18XX engine with solid fundamentals
**Test Coverage:** 112 passing tests
**Supported Variants:** 1830 (full), 1846 (partial), 1889 (partial)

### Current Implementation Strengths
- ✅ Complete stock round mechanics (buy/sell/pass, IPO, presidency)
- ✅ Full operating round (track, tokens, routes, dividends, trains)
- ✅ Private company initial auctions
- ✅ 12×5 stock market grid with directional movement
- ✅ Certificate limits and ownership rules
- ✅ Train rust mechanics with basic bankruptcy handling
- ✅ Configuration-driven variant system
- ✅ Stateless architecture suitable for serialization

### Critical Issues
- 🔴 **BROKEN:** SELL_PRIVATE_COMPANY raises NotImplementedError (blocks gameplay)
- ⚠️ 1846 and 1889 configs incomplete (missing stock market grids)
- ⚠️ Missing advanced features (private powers, loans, terrain costs)

---

## Pull Request Plan

### PHASE 1: Critical Fixes & Completions (Must-Have)

#### PR #1: Fix SELL_PRIVATE_COMPANY Integration 🔴 CRITICAL
**Priority:** HIGHEST
**Complexity:** Medium
**Files:** `app/minigames/StockRound/minigame_stockround.py`, tests
**Scope:**
- Remove NotImplementedError at line 103-113
- Integrate with existing StockRoundSellPrivateCompany auction minigame
- Add integration tests for complete sell flow
- Document private company sale mechanics

**Success Criteria:**
- Players can sell private companies during stock rounds
- All 112 existing tests still pass
- Add 8-10 new integration tests

---

#### PR #2: Complete 1846 Configuration
**Priority:** HIGH
**Complexity:** Low (data entry)
**Files:** `app/config/1846.py`
**Scope:**
- Add full stock market grid
- Complete public company definitions (currently only 2 companies)
- Add all private companies with proper revenue/costs
- Configure 1846-specific rules (dynamic IPO pricing)
- Add complete train roster

**Success Criteria:**
- Full playable 1846 variant
- Add 5-8 variant configuration tests
- Documentation of 1846-specific mechanics

---

#### PR #3: Complete 1889 Configuration
**Priority:** HIGH
**Complexity:** Low (data entry)
**Files:** `app/config/1889.py`
**Scope:**
- Add full stock market grid
- Complete public company definitions (currently only 2 companies)
- Add all private companies with proper revenue/costs
- Configure 1889-specific rules
- Add complete train roster

**Success Criteria:**
- Full playable 1889 variant
- Add 5-8 variant configuration tests
- Documentation of 1889-specific mechanics

---

### PHASE 2: Advanced Game Mechanics

#### PR #4: Implement Private Company Special Powers
**Priority:** HIGH
**Complexity:** High
**Files:** `app/base.py`, `app/minigames/operating_round.py`, configs
**Scope:**
- Create `SpecialPower` class framework
- Implement common power types:
  - Extra token placement (e.g., C&O in 1830)
  - Route revenue bonuses (e.g., B&O in 1830)
  - Free track placement (e.g., D&H in 1830)
  - Special terrain access
  - Purchase discounts
- Add power activation/expiration logic
- Update OperatingRound to check applicable powers
- Add powers to variant configs

**Success Criteria:**
- All major private company powers working
- Add 15-20 tests covering each power type
- Powers properly affect operating rounds
- Documentation of power system

---

#### PR #5: Implement Loan Mechanics
**Priority:** MEDIUM
**Complexity:** Medium
**Files:** `app/base.py`, `app/minigames/operating_round.py`, `app/state.py`
**Scope:**
- Extend partial loan system in TrainsRusted minigame
- Create `Loan` class to track debt
- Implement interest accrual (per operating round)
- Add repayment option during operating rounds
- Implement loan default consequences:
  - Forced share sales
  - Presidency transfer
  - Company receivership
- Track loan history in game state

**Success Criteria:**
- Companies can take loans from president
- Interest calculated correctly
- Defaults handled properly
- Add 10-12 tests covering loan lifecycle

---

#### PR #6: Terrain Cost Implementation (Bridges/Tunnels)
**Priority:** MEDIUM
**Complexity:** Medium
**Files:** `app/base.py`, `app/minigames/operating_round.py`, configs
**Scope:**
- Add terrain type tracking to hex/tile data
- Define terrain types: normal, bridge, tunnel, mountain
- Implement cost multipliers (typically 2x for difficult terrain)
- Update SPECIAL_HEX_RULES to include terrain
- Modify track placement to check and deduct terrain costs
- Add terrain data to variant configs

**Success Criteria:**
- Track placement costs account for terrain
- Add 8-10 tests for terrain scenarios
- Config system supports terrain definitions

---

#### PR #7: Enhanced Route Validation with Board Topology
**Priority:** MEDIUM
**Complexity:** High
**Files:** `app/base.py`, `app/minigames/operating_round.py`
**Scope:**
- Implement actual hex adjacency checking (currently simplified)
- Add track orientation and connection validation
- Differentiate city vs. town revenue
- Validate track curves and through-routes
- Check track type compatibility (e.g., yellow must connect properly)
- Add route visualization helper for debugging
- Support complex route rules (branch scoring, terminus bonuses)

**Success Criteria:**
- Routes validated against actual board topology
- Invalid connections properly rejected
- Add 15-20 complex route tests
- Support advanced routing rules

---

#### PR #8: Full Bankruptcy & Receivership Rules
**Priority:** MEDIUM
**Complexity:** High
**Files:** `app/base.py`, `app/state.py`, `app/minigames/bankruptcy.py` (new)
**Scope:**
- Extend beyond current TrainsRusted simplified handling
- Implement full receivership state for companies
- Add bankruptcy triggers:
  - Trains rust with no replacement
  - Operating costs exceed treasury
  - Loan defaults
- Implement forced share sales (president first)
- Handle share redistribution to bank pool
- Presidential share transfer on bankruptcy
- Company reformation rules (variant-specific)

**Success Criteria:**
- Complete bankruptcy flow implemented
- Add 12-15 bankruptcy scenario tests
- All edge cases handled (multiple bankruptcies, no buyers, etc.)

---

### PHASE 3: Architecture Improvements

#### PR #9: Clarify Game State Architecture
**Priority:** MEDIUM
**Complexity:** High (architectural refactor)
**Files:** `app/state.py`, all minigames
**Addresses:** TODO at `state.py:91`
**Scope:**
- Extract mutable game state from minigame logic
- Create clear `GameState` class with immutable snapshots
- Separate state calculation from move validation
- Document state transition patterns
- Consider event sourcing approach (aligns with TODO.md goals)
- Clean up kwargs dict pattern for state passing

**Success Criteria:**
- Clear separation: state vs. logic vs. validation
- All 112 tests still pass after refactor
- Add 5-10 state management tests
- Improved documentation of architecture

---

#### PR #10: Improve Move Type Detection
**Priority:** LOW
**Complexity:** Medium
**Files:** `app/state.py`, `app/base.py`
**Addresses:** TODO at `state.py:174`
**Scope:**
- Replace duck typing with proper type checking
- Implement factory pattern for Move creation
- Add `MoveType` enum with validation
- Centralize move dispatch logic
- Create extensible move validation system
- Document how to add new move types

**Success Criteria:**
- Type-safe move handling
- Add 8-10 move validation tests
- Documentation for extending move types

---

#### PR #11: Refactor Cross-Linking Patterns
**Priority:** LOW
**Complexity:** Medium
**Files:** `app/base.py`, minigames
**Scope:**
- Address Player↔Company bidirectional references
- Implement cleaner relationship management
- Reduce coupling between game objects
- Add relationship helper methods
- Document object lifecycle and ownership

**Success Criteria:**
- Cleaner object relationships
- Reduced coupling
- All existing tests pass
- Better code maintainability

---

### PHASE 4: Polish & Extensions

#### PR #12: Add Historical Stock Price Tracking
**Priority:** LOW
**Complexity:** Low
**Files:** `app/base.py`, `app/state.py`
**Scope:**
- Track price history per company
- Add price movement audit trail (why price changed)
- Implement variant-specific historical movement rules
- Add price history API for frontend consumption
- Support price charts/graphs

**Success Criteria:**
- Complete price history available
- Add 5-8 history tracking tests
- Frontend-friendly API

---

#### PR #13: Game Phase Transition Validation
**Priority:** LOW
**Complexity:** Medium
**Files:** `app/state.py`
**Scope:**
- Add explicit phase transition validation
- Enforce correct sequence: Initial Auction → Stock Round → Operating Round
- Validate operating round counts per set (based on variant rules)
- Add phase completion checks
- Implement phase hooks for cleanup/setup

**Success Criteria:**
- Invalid phase transitions rejected
- Add 10-12 phase transition tests
- Clear phase state machine

---

#### PR #14: Add Game Variant: 1817
**Priority:** LOW
**Complexity:** High
**Files:** `app/config/1817.py`, potentially `app/base.py`
**Scope:**
- Create full 1817 configuration
- Implement short-line companies (unique to 1817)
- Add 1817-specific loan mechanics (more complex than standard)
- Configure 1817 stock market (different grid)
- Implement acquisition mechanics
- Add train roster and phase system

**Success Criteria:**
- Playable 1817 variant
- Add 10+ variant-specific tests
- Documentation of 1817 unique rules

---

#### PR #15: Add Game Variant: 18Chesapeake
**Priority:** LOW
**Complexity:** Medium
**Files:** `app/config/18chesapeake.py`
**Scope:**
- Create full 18Chesapeake configuration
- Implement capitalization variants
- Add company formation rules (different from 1830)
- Configure stock market
- Add private companies and powers
- Train roster

**Success Criteria:**
- Playable 18Chesapeake variant
- Add 10+ variant-specific tests
- Documentation of unique mechanics

---

#### PR #16: Enhanced Logging & Debugging
**Priority:** LOW
**Complexity:** Low
**Files:** All Python files
**Scope:**
- Add structured logging throughout codebase
- Create game replay functionality (replay moves from history)
- Add move history export (JSON format)
- Implement debug mode with detailed validation output
- Add performance logging for complex operations

**Success Criteria:**
- Comprehensive logging system
- Replay functionality working
- Add logging configuration tests
- Debug mode helps troubleshooting

---

#### PR #17: API Documentation & Examples
**Priority:** LOW
**Complexity:** Low
**Files:** `docs/`, docstrings in all modules
**Scope:**
- Generate API documentation from docstrings (Sphinx or similar)
- Add more example game flows
- Create integration guide for frontend developers
- Document all move types and validation rules
- Add architecture diagrams
- Create quickstart guide

**Success Criteria:**
- Complete API documentation
- Multiple example integrations
- Frontend integration guide
- Improved developer onboarding

---

## Implementation Recommendations

### Suggested Order
1. **PR #1** (CRITICAL) - Unblocks private company sales
2. **PR #2-3** - Provides 3 fully playable variants
3. **PR #4** - High-value feature for gameplay depth
4. **PR #5-8** - Core mechanics expansion (parallel if resources available)
5. **PR #9-11** - Architecture improvements (if long-term maintenance planned)
6. **PR #12-17** - Polish and extensions (as time/interest permits)

### Effort Estimates
- **Phase 1:** 2-3 weeks (critical for playability)
- **Phase 2:** 4-6 weeks (core features)
- **Phase 3:** 2-3 weeks (architectural improvements)
- **Phase 4:** 3-4 weeks (polish and new variants)
- **Total:** 11-16 weeks for complete implementation

### Quick Wins (High value, low effort)
- ✅ PR #1: Fix critical bug (~3-5 days)
- ✅ PR #2-3: Complete variants (~2-3 days each)
- ✅ PR #12: Price tracking (~2-3 days)
- ✅ PR #16: Logging (~2-3 days)

### Complex Tasks (High value, high effort)
- ⚠️ PR #4: Private company powers (~1-2 weeks)
- ⚠️ PR #7: Route validation (~1-2 weeks)
- ⚠️ PR #8: Bankruptcy (~1-2 weeks)
- ⚠️ PR #9: State architecture (~1-2 weeks)

---

## Testing Strategy

### Test Coverage Goals
- Maintain 100% of existing 112 tests passing
- Target 90%+ code coverage for new features
- Add integration tests for complex workflows
- Add regression tests for bug fixes

### Test Categories
- **Unit Tests:** Individual function/method validation
- **Integration Tests:** Multi-component workflows (e.g., complete stock round)
- **Variant Tests:** Ensure each variant loads and plays correctly
- **Regression Tests:** Prevent known bugs from reoccurring
- **Edge Case Tests:** Boundary conditions, rare scenarios

---

## Risk Assessment

### Low Risk
- PR #2-3: Data entry, unlikely to break existing functionality
- PR #12: Additive feature, no existing logic changed
- PR #16-17: Documentation and logging, non-functional

### Medium Risk
- PR #4-8: New mechanics, could interact with existing systems
- PR #10-11: Refactoring, but well-tested

### High Risk
- PR #1: Touches core stock round logic
- PR #9: Major architectural change affecting all components

### Mitigation Strategies
- Extensive test coverage before merging
- Code review for high-risk PRs
- Feature flags for experimental features
- Gradual rollout of architectural changes

---

## Success Metrics

### Phase 1 Success
- Private company sales work in all scenarios
- 3 fully playable variants (1830, 1846, 1889)
- Zero critical bugs

### Phase 2 Success
- All major 18XX mechanics implemented
- Private company powers working
- Complex scenarios (loans, bankruptcy) handled

### Phase 3 Success
- Clean, maintainable architecture
- Clear separation of concerns
- Easy to extend with new variants/features

### Phase 4 Success
- Excellent documentation
- Multiple variants playable
- Production-ready for frontend integration

---

## Notes

- Current codebase is high quality with good test coverage
- Stateless design makes it suitable for web/API deployment
- Configuration system makes adding variants straightforward
- TODO.md suggests interest in event sourcing architecture (consider in PR #9)
- Recent development focused on operating rounds and stock market (PRs #40-42)

---

**Last Updated:** 2025-11-17
**Status:** Planning Phase Complete - Ready for Implementation
