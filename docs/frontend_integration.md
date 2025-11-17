# Frontend Integration Guide

Building user interfaces for Daemon18xx games.

## Overview

Daemon18xx is designed to be frontend-agnostic. The stateless architecture makes it perfect for:

- **Web Applications** (React, Vue, Angular, etc.)
- **Mobile Apps** (React Native, Flutter, etc.)
- **Desktop Applications** (Electron, Qt, etc.)
- **REST APIs** (Flask, FastAPI, Django, etc.)

This guide shows you how to integrate the game engine with your frontend.

## Architecture Patterns

### Pattern 1: REST API Backend

Most common pattern for web/mobile apps.

```
Frontend (React/Vue/etc.)
    ↓ HTTP
Backend (Flask/FastAPI)
    ↓ Python
Daemon18xx Engine
```

### Pattern 2: Direct Integration

For Python-based frontends (e.g., Qt, Kivy).

```
Frontend (Qt/Kivy)
    ↓ Direct calls
Daemon18xx Engine
```

### Pattern 3: WebSocket Real-time

For multiplayer games requiring real-time updates.

```
Frontend
    ↓ WebSocket
Backend (with pub/sub)
    ↓ Python
Daemon18xx Engine
```

## REST API Example

Here's a minimal Flask API for the game engine:

### Basic Flask API

```python
from flask import Flask, request, jsonify
from app.state import Game
from app.logging_config import setup_logging
from app.game_history import GameHistory

app = Flask(__name__)
setup_logging(level='INFO', log_file='api.log')

# In-memory game storage (use Redis/DB for production)
games = {}
histories = {}

@app.route('/api/games', methods=['POST'])
def create_game():
    """Create a new game."""
    data = request.json
    players = data.get('players', [])
    variant = data.get('variant', '1830')

    if len(players) < 2:
        return jsonify({'error': 'Need at least 2 players'}), 400

    # Create game
    game = Game.start(players, variant)
    game_id = str(len(games) + 1)  # Simple ID generation

    # Store game and history
    games[game_id] = game
    histories[game_id] = GameHistory()
    histories[game_id].initialize(variant, players)

    return jsonify({
        'game_id': game_id,
        'variant': variant,
        'players': players,
        'current_phase': game.minigame_class,
        'current_player': game.current_player.name
    })

@app.route('/api/games/<game_id>', methods=['GET'])
def get_game_state(game_id):
    """Get current game state."""
    game = games.get(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    # Serialize game state
    return jsonify({
        'game_id': game_id,
        'phase': game.minigame_class,
        'current_player': {
            'id': game.current_player.id,
            'name': game.current_player.name,
            'cash': game.current_player.cash
        },
        'players': [
            {
                'id': p.id,
                'name': p.name,
                'cash': p.cash,
                'companies': [c.id for c in p.portfolio]
            }
            for p in game.state.players
        ],
        'companies': [
            {
                'id': c.id,
                'name': c.name,
                'price': c.get_current_price(),
                'president': c.president.name if c.president else None,
                'floated': c.isFloated(),
                'cash': c.cash
            }
            for c in game.state.public_companies
        ],
        'phase_summary': game.phase_validator.get_phase_summary() if game.phase_validator else {}
    })

@app.route('/api/games/<game_id>/moves', methods=['POST'])
def execute_move(game_id):
    """Execute a move."""
    game = games.get(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    data = request.json
    move_type = data.get('move_type')
    move_data = data.get('move_data', {})

    # Create move object based on type
    move = create_move_from_json(move_type, move_data, game)
    if not move:
        return jsonify({'error': 'Invalid move type'}), 400

    # Execute move
    success = game.performedMove(move)

    # Record in history
    histories[game_id].record_move(
        move=move,
        state=game.state,
        success=success,
        errors=game.errors() if not success else None,
        phase=game.minigame_class
    )

    if success:
        return jsonify({
            'success': True,
            'new_phase': game.minigame_class,
            'next_player': game.current_player.name
        })
    else:
        return jsonify({
            'success': False,
            'errors': game.errors()
        }), 400

@app.route('/api/games/<game_id>/valid-moves', methods=['GET'])
def get_valid_moves(game_id):
    """Get valid moves for current player."""
    game = games.get(game_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    # Generate valid moves based on current phase
    valid_moves = generate_valid_moves(game)

    return jsonify({
        'phase': game.minigame_class,
        'player': game.current_player.name,
        'moves': valid_moves
    })

@app.route('/api/games/<game_id>/history', methods=['GET'])
def get_game_history(game_id):
    """Get game history."""
    history = histories.get(game_id)
    if not history:
        return jsonify({'error': 'History not found'}), 404

    return jsonify(history.export_dict())

def create_move_from_json(move_type, move_data, game):
    """Helper to create move objects from JSON."""
    if move_type == 'buy_private':
        from app.minigames.PrivateCompanyInitialAuction.minigame_buy import BuyPrivateCompanyMove
        move = BuyPrivateCompanyMove()
        move.player_id = move_data['player_id']
        move.company_id = move_data['company_id']
        return move

    elif move_type == 'pass':
        from app.minigames.PrivateCompanyInitialAuction.minigame_buy import PassMove
        move = PassMove()
        move.player_id = move_data['player_id']
        return move

    elif move_type == 'buy_stock':
        from app.minigames.StockRound.minigame_stockround import BuyStockMove
        move = BuyStockMove()
        move.player_id = move_data['player_id']
        move.company_id = move_data['company_id']
        move.amount = move_data['amount']
        move.source = move_data['source']
        move.price = move_data['price']
        return move

    # Add more move types as needed
    return None

def generate_valid_moves(game):
    """Generate list of valid moves for current phase."""
    phase = game.minigame_class
    player = game.current_player

    if phase == "BuyPrivateCompany":
        # List available private companies
        available = [
            {
                'type': 'buy_private',
                'company_id': pc.name,
                'company_name': pc.name,
                'cost': pc.cost,
                'revenue': pc.revenue
            }
            for pc in game.state.private_companies
            if not pc.belongs_to and player.cash >= pc.cost
        ]
        available.append({'type': 'pass'})
        return available

    elif phase == "StockRound":
        # List available stock purchases
        moves = []
        for company in game.state.public_companies:
            if company.isFloated():
                # Can buy from IPO or BANK
                for source in ['IPO', 'BANK']:
                    price = company.get_current_price()
                    if player.cash >= price * 10:  # Cost for 10%
                        moves.append({
                            'type': 'buy_stock',
                            'company_id': company.id,
                            'company_name': company.name,
                            'source': source,
                            'price': price
                        })

        moves.append({'type': 'pass'})
        return moves

    return [{'type': 'pass'}]

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### Frontend React Example

```javascript
import React, { useState, useEffect } from 'react';

function GameBoard({ gameId }) {
  const [gameState, setGameState] = useState(null);
  const [validMoves, setValidMoves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch game state
  useEffect(() => {
    fetchGameState();
    const interval = setInterval(fetchGameState, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [gameId]);

  async function fetchGameState() {
    try {
      const response = await fetch(`/api/games/${gameId}`);
      const data = await response.json();
      setGameState(data);

      // Fetch valid moves
      const movesResponse = await fetch(`/api/games/${gameId}/valid-moves`);
      const movesData = await movesResponse.json();
      setValidMoves(movesData.moves);

      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function executeMove(move) {
    try {
      const response = await fetch(`/api/games/${gameId}/moves`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          move_type: move.type,
          move_data: move
        })
      });

      const result = await response.json();

      if (result.success) {
        // Refresh game state
        fetchGameState();
      } else {
        alert(`Move failed: ${result.errors.join(', ')}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!gameState) return <div>No game found</div>;

  return (
    <div className="game-board">
      <h1>18XX Game - {gameState.phase}</h1>

      <div className="current-player">
        <h2>Current Player: {gameState.current_player.name}</h2>
        <p>Cash: ${gameState.current_player.cash}</p>
      </div>

      <div className="players">
        <h3>Players</h3>
        {gameState.players.map(player => (
          <div key={player.id} className="player">
            <strong>{player.name}</strong>: ${player.cash}
            {player.companies.length > 0 && (
              <span> ({player.companies.join(', ')})</span>
            )}
          </div>
        ))}
      </div>

      <div className="companies">
        <h3>Public Companies</h3>
        {gameState.companies.map(company => (
          <div key={company.id} className="company">
            <strong>{company.name}</strong> - ${company.price}
            <br />
            President: {company.president || 'None'}
            {company.floated && <span> ✓ Floated</span>}
          </div>
        ))}
      </div>

      <div className="valid-moves">
        <h3>Available Moves</h3>
        {validMoves.map((move, index) => (
          <button
            key={index}
            onClick={() => executeMove(move)}
            className="move-button"
          >
            {move.type === 'buy_private' && `Buy ${move.company_name} ($${move.cost})`}
            {move.type === 'buy_stock' && `Buy ${move.company_name} stock ($${move.price})`}
            {move.type === 'pass' && 'Pass'}
          </button>
        ))}
      </div>
    </div>
  );
}

export default GameBoard;
```

## State Serialization

### Serializing Game State

The game state needs to be serialized for transmission:

```python
def serialize_game_state(game: Game) -> dict:
    """Serialize full game state to JSON-compatible dict."""
    return {
        'phase': game.minigame_class,
        'variant': game.variant,
        'current_player_id': game.current_player.id if game.current_player else None,
        'players': [serialize_player(p) for p in game.state.players],
        'public_companies': [serialize_public_company(c) for c in game.state.public_companies],
        'private_companies': [serialize_private_company(c) for c in game.state.private_companies],
        'phase_info': game.phase_validator.get_phase_summary() if game.phase_validator else {}
    }

def serialize_player(player: Player) -> dict:
    """Serialize a player."""
    return {
        'id': player.id,
        'name': player.name,
        'cash': player.cash,
        'order': player.order,
        'portfolio': [c.id for c in player.portfolio],
        'private_companies': [pc.name for pc in player.private_companies],
        'passed': player.passed
    }

def serialize_public_company(company: PublicCompany) -> dict:
    """Serialize a public company."""
    return {
        'id': company.id,
        'name': company.name,
        'short_name': company.short_name,
        'cash': company.cash,
        'price': company.get_current_price(),
        'president': company.president.id if company.president else None,
        'floated': company.isFloated(),
        'shares_available': {
            'IPO': company.stocks.get(StockPurchaseSource.IPO, 0),
            'BANK': company.stocks.get(StockPurchaseSource.BANK, 0)
        },
        'trains': [t.type for t in company.trains],
        'tokens_available': company.tokens_available,
        'bankrupt': company.bankrupt,
        'total_debt': company.total_debt(),
        'price_history': [
            {
                'round': e.round_number,
                'old_price': e.old_price,
                'new_price': e.new_price,
                'reason': e.reason
            }
            for e in company.get_price_history(limit=10)  # Last 10 changes
        ]
    }

def serialize_private_company(pc: PrivateCompany) -> dict:
    """Serialize a private company."""
    return {
        'name': pc.name,
        'short_name': pc.short_name,
        'cost': pc.cost,
        'revenue': pc.revenue,
        'owner': pc.belongs_to.id if pc.belongs_to else None,
        'company_owner': pc.belongs_to_company.id if pc.belongs_to_company else None,
        'power': {
            'type': pc.power.power_type.name,
            'value': pc.power.value
        } if pc.power else None
    }
```

## Real-Time Updates (WebSocket)

For multiplayer games, use WebSockets for real-time updates:

```python
from flask import Flask
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('join_game')
def on_join(data):
    """Player joins a game room."""
    game_id = data['game_id']
    player_id = data['player_id']
    join_room(game_id)

    emit('player_joined', {
        'player_id': player_id,
        'game_id': game_id
    }, room=game_id)

@socketio.on('execute_move')
def on_move(data):
    """Player executes a move."""
    game_id = data['game_id']
    game = games.get(game_id)

    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # Create and execute move
    move = create_move_from_json(data['move_type'], data['move_data'], game)
    success = game.performedMove(move)

    if success:
        # Broadcast new state to all players in room
        emit('game_updated', {
            'game_state': serialize_game_state(game),
            'move_by': data['move_data']['player_id']
        }, room=game_id)
    else:
        emit('move_failed', {
            'errors': game.errors()
        })

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
```

## UI Components Needed

### Essential Components

1. **Game Board**
   - Stock market grid
   - Company information cards
   - Player information panel

2. **Move Interface**
   - Buy/sell stock buttons
   - Private company auction
   - Operating round controls

3. **Information Displays**
   - Phase indicator
   - Current player
   - Available actions

4. **History Viewer**
   - Move log
   - Price history charts
   - Game timeline

### Component Data Flow

```
Backend (Daemon18xx)
    ↓ Serialize State
REST API / WebSocket
    ↓ JSON
Frontend State Management (Redux/Context)
    ↓ Props
React Components
    ↓ Render
User Interface
```

## Performance Considerations

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_valid_moves_cached(game_id, phase, player_id):
    """Cache valid moves calculation."""
    game = games.get(game_id)
    return generate_valid_moves(game)
```

### Pagination

For large game histories:

```python
@app.route('/api/games/<game_id>/history')
def get_game_history_paginated(game_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    history = histories.get(game_id)
    if not history:
        return jsonify({'error': 'Not found'}), 404

    total_moves = history.get_move_count()
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'moves': history.moves[start:end],
        'page': page,
        'per_page': per_page,
        'total': total_moves,
        'pages': (total_moves + per_page - 1) // per_page
    })
```

### Delta Updates

Only send what changed:

```python
def compute_state_delta(old_state, new_state):
    """Compute delta between states."""
    delta = {}

    if old_state['phase'] != new_state['phase']:
        delta['phase'] = new_state['phase']

    # Compare players
    for old_p, new_p in zip(old_state['players'], new_state['players']):
        if old_p['cash'] != new_p['cash']:
            delta.setdefault('players', {})[new_p['id']] = {
                'cash': new_p['cash']
            }

    # Add more delta logic...

    return delta
```

## Error Handling

### Frontend Error Handling

```javascript
async function executeMove(move) {
  try {
    const response = await fetch(`/api/games/${gameId}/moves`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ move_type: move.type, move_data: move })
    });

    const result = await response.json();

    if (!response.ok) {
      // Backend validation error
      showError(`Move invalid: ${result.errors.join(', ')}`);
      return;
    }

    if (!result.success) {
      // Game engine validation error
      showError(`Move failed: ${result.errors.join(', ')}`);
      return;
    }

    // Success - update UI
    updateGameState(result);

  } catch (error) {
    // Network or other error
    showError(`Network error: ${error.message}`);
  }
}
```

### Backend Error Handling

```python
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {e}", exc_info=True)

    return jsonify({
        'error': 'Internal server error',
        'message': str(e) if app.debug else 'An error occurred'
    }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404
```

## Security Considerations

### Player Authentication

```python
from functools import wraps
from flask import request

def require_player_auth(f):
    """Decorator to require player authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        game_id = kwargs.get('game_id')
        player_id = request.json.get('player_id')

        # Verify player is in game
        game = games.get(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        if not any(p.id == player_id for p in game.state.players):
            return jsonify({'error': 'Unauthorized'}), 403

        return f(*args, **kwargs)

    return decorated_function

@app.route('/api/games/<game_id>/moves', methods=['POST'])
@require_player_auth
def execute_move(game_id):
    # ... move execution ...
    pass
```

### Move Validation

Always validate on backend, never trust frontend:

```python
@app.route('/api/games/<game_id>/moves', methods=['POST'])
def execute_move(game_id):
    # Frontend validation is just UX
    # Backend must validate everything

    game = games.get(game_id)
    move = create_move_from_json(...)

    # Engine handles validation
    success = game.performedMove(move)

    if not success:
        # Don't expose internal errors to users
        return jsonify({
            'success': False,
            'errors': sanitize_errors(game.errors())
        }), 400
```

## Testing Your Integration

### API Testing

```python
import unittest
from app import app

class APITests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_create_game(self):
        response = self.client.post('/api/games', json={
            'players': ['Alice', 'Bob', 'Charlie'],
            'variant': '1830'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('game_id', data)

    def test_execute_move(self):
        # Create game
        create_response = self.client.post('/api/games', json={
            'players': ['Alice', 'Bob'],
            'variant': '1830'
        })
        game_id = create_response.json['game_id']

        # Execute move
        move_response = self.client.post(f'/api/games/{game_id}/moves', json={
            'move_type': 'pass',
            'move_data': {'player_id': 'Alice'}
        })

        self.assertEqual(move_response.status_code, 200)
```

## Example Projects

### Minimal Web App

See `examples/web_app/` for a minimal Flask + React example.

### Mobile App

See `examples/mobile_app/` for React Native example.

### Desktop App

See `examples/desktop_app/` for Electron example.

---

**Navigation:**
- [← Back to API Reference](api_reference.md)
- [Examples →](examples/)
- [Main Documentation](README.md)
