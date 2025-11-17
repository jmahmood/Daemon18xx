# Daemon18xx Multiplayer - 1889 WebSocket Game

A real-time multiplayer implementation of 1889: History of Shikoku Railways using WebSockets. Play over your local network with friends!

## Features

- **Real-time Multiplayer**: WebSocket-based gameplay with instant updates
- **Full Game Visibility**: All players see the market, their status, and public information
- **Interactive Interface**: Inspired by Apple Human Interface Guidelines and Jef Raskin's principles
- **Spectator Mode**: Allow others to watch the game on a large monitor
- **Persistent Games**: Games are saved to SQLite and survive server restarts
- **Reconnection Support**: Bookmark your player link and rejoin anytime
- **Beautiful UI**: Dark theme with zoomable hex map, stock market grid, and real-time action ticker

## Architecture

```
multiplayer/
├── backend/          # Python FastAPI + Socket.IO server
│   ├── server.py     # Main server application
│   ├── database.py   # SQLite persistence layer
│   └── requirements.txt
│
├── frontend/         # TypeScript + Vite client
│   ├── src/
│   │   ├── components/  # UI components (Header, Map, Stock Market, etc.)
│   │   ├── services/    # WebSocket service
│   │   └── utils/       # Helpers (sound effects, URL parsing)
│   └── package.json
│
└── shared/           # Shared game data
    └── 1889_map.py   # Hex map configuration for Shikoku
```

## Quick Start

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 18+** (for frontend)
- Local network access

### 1. Install Backend Dependencies

```bash
cd multiplayer/backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd multiplayer/frontend
npm install
```

### 3. Start the Backend Server

```bash
cd multiplayer/backend
python server.py
```

The server will start on `http://0.0.0.0:8000`

### 4. Start the Frontend Dev Server

In a new terminal:

```bash
cd multiplayer/frontend
npm run dev
```

The frontend will start on `http://0.0.0.0:5173`

### 5. Access the Game

Open your browser to:
```
http://localhost:5173
```

Or from another device on your network:
```
http://<your-ip-address>:5173
```

## How to Play

### Creating a Game

1. Open the application in your browser
2. Click "Create New Game"
3. Choose the number of players (3-6)
4. You'll receive:
   - **Your creator link** - Open this to manage the game
   - **Player links** - Share these with other players (one per player)
   - **Spectator link** - Share this for view-only access

5. Each player should:
   - Open their unique player link
   - Bookmark it for reconnection
   - Wait in the lobby

6. When all players have joined, the creator starts the game

### Game Interface

**Header** (Always Visible):
- Current game phase
- Active player indicator
- Your cash and certificate count

**Main Tabs**:
- **Map**: Interactive zoomable hex map of Shikoku
  - Zoom: Mouse wheel
  - Pan: Click and drag
- **Stock Market**: 2×12 grid showing stock prices
  - Click cells to see companies at that price
- **Companies**: Detailed view of all 7 public companies

**Footer** (Always Visible):
- Real-time action ticker showing all player moves
- Scrolls automatically with sound effects
- Toggle sound on/off

**Sidebar**:
- Player list with cash and certificate counts
- Current player highlighted
- Click players for detailed info (expandable)

### Reconnection

If you lose connection or close your browser:

1. Open your bookmarked player link
2. The server will restore your session
3. Continue playing from where you left off

### Spectator Mode

Spectators can:
- View the entire game state
- See all player actions in real-time
- Watch the map and market updates
- **Cannot** make moves or interact

Perfect for displaying on a large monitor/TV while everyone plays on their own devices!

## Game Rules (1889)

### Setup
- 3-6 players
- Starting cash: ¥2500 ÷ number of players
- 5 private companies (¥20 to ¥200)
- 7 public companies

### Game Flow

1. **Private Company Auction**: Players bid on 5 private railways
2. **Stock Rounds**: Buy and sell shares of public companies
3. **Operating Rounds**: Companies lay track, place tokens, run trains
4. **Repeat** until game end conditions

### Victory
Player with the most wealth (cash + stock values) wins!

## Network Configuration

### Running on Local Network

The server binds to `0.0.0.0` by default, making it accessible from other devices.

**To connect from other devices:**

1. Find your host machine's IP address:
   ```bash
   # Linux/Mac
   ip addr show | grep inet
   # or
   ifconfig | grep inet

   # Windows
   ipconfig
   ```

2. On other devices, navigate to:
   ```
   http://<host-ip-address>:5173
   ```

3. Share player links like:
   ```
   http://192.168.1.100:5173/game/ABC123/play?token=xyz...
   ```

### Port Configuration

- **Backend**: Port 8000 (configurable in `server.py`)
- **Frontend Dev**: Port 5173 (configurable in `vite.config.ts`)
- **WebSocket**: Uses same port as backend with Socket.IO

## Development

### Backend Development

The backend is a FastAPI + Socket.IO server with SQLite persistence.

**Key files:**
- `server.py`: Main server with WebSocket handlers
- `database.py`: Database operations and schemas

**Running tests:**
```bash
cd ../../  # Go to project root
python -m pytest
```

### Frontend Development

The frontend is built with Vite + TypeScript.

**Key directories:**
- `src/components/`: UI components
- `src/services/`: WebSocket client service
- `src/utils/`: Utilities (sound, URL parsing)

**Development mode:**
```bash
npm run dev
```

**Production build:**
```bash
npm run build
npm run preview
```

### Adding New Features

**Backend**:
1. Add WebSocket event handler in `server.py`
2. Update database schema if needed in `database.py`
3. Integrate with Daemon18xx engine

**Frontend**:
1. Create new component in `src/components/`
2. Add event handlers in `socketService.ts`
3. Update `app.ts` to wire it up

## Database

Games are persisted in SQLite (`game.db`).

**Tables:**
- `games`: Game rooms and metadata
- `players`: Player information and tokens
- `game_states`: Snapshots of game state for each move

**Location:** `multiplayer/backend/game.db`

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 isn't in use: `lsof -i :8000`

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Install dependencies: `npm install`
- Check port 5173 isn't in use

### Can't connect from other devices
- Check firewall settings (allow ports 5173 and 8000)
- Verify you're on the same network
- Try accessing via IP address instead of hostname

### WebSocket connection fails
- Check browser console for errors
- Verify backend is running
- Check browser WebSocket support (all modern browsers OK)

### Game state not persisting
- Check `game.db` file exists and is writable
- Check server logs for database errors

## Production Deployment

For production (not just local network), you'll want to:

1. **Build the frontend:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Serve static files from backend:**
   - Mount `frontend/dist` in FastAPI
   - Update `server.py` to serve static files

3. **Use production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -k uvicorn.workers.UvicornWorker server:socket_app
   ```

4. **Set up reverse proxy** (nginx/Apache)

5. **Use proper database** (PostgreSQL instead of SQLite)

6. **Enable HTTPS** for secure WebSocket connections

## License

Part of Daemon18xx project. See main repository for license information.

## Contributing

This multiplayer implementation is designed to work with the core Daemon18xx engine.

To contribute:
1. Make sure changes don't break the core library
2. Keep multiplayer code isolated in `/multiplayer` directory
3. Test with multiple simultaneous clients
4. Follow the existing code style

## Credits

- **Game Design**: 1889 by Yasutaka Ikeda
- **Engine**: Daemon18xx by the core team
- **UI Design**: Inspired by Apple Human Interface Guidelines and Jef Raskin's "The Humane Interface"

---

**Enjoy your game of 1889! 🚂**
