# Daemon18xx Documentation

Welcome to the Daemon18xx game engine documentation! This directory contains comprehensive guides, API references, and examples for working with the 18XX board game engine.

## Documentation Overview

### Getting Started
- **[Quickstart Guide](quickstart.md)** - Get up and running in 5 minutes
- **[Architecture Overview](architecture.md)** - High-level system design
- **[Game Concepts](game_concepts.md)** - 18XX game rules and terminology

### Developer Guides
- **[API Reference](api_reference.md)** - Complete API documentation
- **[Frontend Integration Guide](frontend_integration.md)** - Building UIs with the engine
- **[Move Types Reference](move_types.md)** - All available moves and validation
- **[Examples](examples/)** - Code examples and tutorials

### Features
- **[Historical Price Tracking](features/price_history.md)** - Track stock price changes
- **[Logging & Debugging](features/logging.md)** - Structured logging and game history
- **[Phase Validation](features/phase_validation.md)** - Game phase transitions
- **[Special Powers](features/special_powers.md)** - Private company powers
- **[Loans & Bankruptcy](features/loans_bankruptcy.md)** - Financial mechanics
- **[Terrain Costs](features/terrain_costs.md)** - Track laying costs

### Variants
- **[1830](variants/1830.md)** - Robber Barons variant
- **[1846](variants/1846.md)** - Race for the Midwest
- **[1889](variants/1889.md)** - Shikoku variant

## Quick Links

### For New Users
Start with the [Quickstart Guide](quickstart.md) to understand the basics, then explore [Game Concepts](game_concepts.md) to learn 18XX terminology.

### For Frontend Developers
Read the [Frontend Integration Guide](frontend_integration.md) and [API Reference](api_reference.md) to build your UI.

### For Game Engine Developers
Check out the [Architecture Overview](architecture.md) and browse the [Examples](examples/) directory.

### For Debugging
See [Logging & Debugging](features/logging.md) for troubleshooting tools.

## What is Daemon18xx?

Daemon18xx is a Python-based game engine for 18XX railway games. It provides:

- ✅ **Stateless Architecture** - Suitable for web/API deployment
- ✅ **Multiple Variants** - 1830, 1846, 1889 fully implemented
- ✅ **Comprehensive Testing** - 233+ tests, all passing
- ✅ **Phase-Based Design** - Modular minigames for each phase
- ✅ **Advanced Features** - Loans, terrain costs, bankruptcy, special powers
- ✅ **Developer Tools** - Logging, history tracking, phase validation

## Key Features

### ⚡ Stateless Minigame Architecture
Game phases are separate "minigames" that receive state as parameters, making the engine perfect for web APIs and distributed systems.

### 📊 Historical Tracking
Complete price history, move history, and phase transitions are tracked for debugging, analysis, and replay.

### 🔒 Validation System
Comprehensive move validation ensures games follow rules correctly, with detailed error messages.

### 🎨 Frontend-Ready
Clean API design makes it easy to build web UIs, mobile apps, or desktop clients.

### 🧩 Extensible
Easy to add new variants, special powers, and game mechanics without modifying core code.

## Architecture Highlights

```
Game State (Immutable)
    ↓
Minigame Validates Move
    ↓
Minigame Mutates State
    ↓
Phase Transition Check
    ↓
New Minigame (if needed)
```

Each game phase is a self-contained "minigame" that validates moves, mutates state, and determines the next phase. This design enables:

- Easy testing (test each minigame independently)
- Clear separation of concerns
- Simplified debugging
- Parallelizable operations

## Example Usage

```python
from app.state import Game

# Start a new game
game = Game.start(
    players=['Alice', 'Bob', 'Charlie'],
    variant='1830'
)

# Make moves
from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompanyMove

move = BuyPrivateCompanyMove(
    player_id=game.current_player.id,
    company_id="C&O"
)

success = game.performedMove(move)

if success:
    print(f"Move successful! Next player: {game.current_player.name}")
else:
    print(f"Move failed: {game.errors()}")
```

## Testing

Run the complete test suite:

```bash
# All tests
python -m unittest discover app/unittests -v

# Specific test file
python -m unittest app.unittests.test_PriceHistory -v

# Single test
python -m unittest app.unittests.test_PriceHistory.PriceHistoryEntryTests.test_entry_creation
```

Current status: **233 tests passing** ✅

## Contributing

### Adding a New Variant

1. Create config file in `app/config/yourvariant.py`
2. Define companies, stock market, and rules
3. Add variant-specific tests
4. Document in `docs/variants/yourvariant.md`

### Adding a New Feature

1. Implement feature in appropriate module
2. Write comprehensive tests (aim for 10+ tests)
3. Update relevant documentation
4. Submit PR with clear description

### Coding Standards

- **Type hints** for all public APIs
- **Docstrings** for all classes and public methods
- **Tests** for all new functionality
- **Logging** for important operations
- **Validation** for all user input

## Support

### Issues & Bugs
Report issues at: https://github.com/jmahmood/Daemon18xx/issues

### Questions
For questions about game rules or implementation, see:
- [Game Concepts](game_concepts.md) for rules
- [API Reference](api_reference.md) for implementation
- [Examples](examples/) for code samples

## License

[Include license information here]

## Credits

Built with ❤️ for the 18XX gaming community.

---

**Navigation:**
- [Next: Quickstart Guide →](quickstart.md)
- [Architecture Overview →](architecture.md)
- [API Reference →](api_reference.md)
