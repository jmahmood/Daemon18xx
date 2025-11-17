/**
 * Main application class
 * Manages UI state, WebSocket connection, and game flow
 */

import { socketService } from './services/socketService';
import { soundEffects } from './utils/soundEffects';
import { parseGameURL } from './utils/urlParser';
import type { GameState, PlayerAction, AuthState } from './types';
import { Header } from './components/Header';
import { StockMarket } from './components/StockMarket';
import { HexMap } from './components/HexMap';
import { ActionTicker } from './components/ActionTicker';
import { PlayerList } from './components/PlayerList';
import { LobbyModal } from './components/LobbyModal';
import { GameLobby } from './components/GameLobby';
import { PrivateCompanyAuction } from './components/PrivateCompanyAuction';

export class App {
  private appContainer: HTMLElement;
  private authState: AuthState = { authenticated: false };
  private gameState: GameState | null = null;
  private gameLobby: GameLobby | null = null;
  private myPlayerName: string | null = null; // Track this player's name

  // UI Components
  private header: Header;
  private stockMarket: StockMarket;
  private hexMap: HexMap;
  private actionTicker: ActionTicker;
  private playerList: PlayerList;
  private privateAuction: PrivateCompanyAuction;
  private lobbyModal: LobbyModal | null = null;

  constructor() {
    this.appContainer = document.getElementById('app')!;

    // Initialize components
    this.header = new Header();
    this.stockMarket = new StockMarket();
    this.hexMap = new HexMap();
    this.actionTicker = new ActionTicker();
    this.playerList = new PlayerList();
    this.privateAuction = new PrivateCompanyAuction({
      onMakeMove: (moveData: any) => this.handleMakeMove(moveData)
    });
  }

  async initialize() {
    console.log('🎮 Initializing Daemon18xx Multiplayer...');

    // Parse URL for room code and token
    const urlParams = parseGameURL();

    if (urlParams.roomCode && urlParams.token) {
      // We have a direct game link
      await this.joinExistingGame(urlParams.roomCode, urlParams.token, urlParams.isSpectator);
    } else {
      // Show lobby/create game UI
      this.showLobbyUI();
    }

    // Setup WebSocket event handlers
    this.setupSocketHandlers();

    // Setup UI event handlers
    this.setupUIHandlers();
  }

  private async joinExistingGame(roomCode: string, token: string, isSpectator: boolean) {
    console.log(`🎮 Joining game: ${roomCode} (${isSpectator ? 'spectator' : 'player'})`);

    this.authState = {
      authenticated: false,
      roomCode,
      token,
    };

    // Authenticate with server
    socketService.authenticate(roomCode, token);

    // Show loading message
    this.showLoading('Connecting to game...');
  }

  private showLobbyUI() {
    // Clear loading
    this.appContainer.innerHTML = '';

    // Show lobby modal
    this.lobbyModal = new LobbyModal({
      onCreateGame: async (maxPlayers: number) => {
        await this.createNewGame(maxPlayers);
      }
    });

    this.appContainer.appendChild(this.lobbyModal.render());
  }

  private async createNewGame(maxPlayers: number) {
    try {
      const response = await fetch('/api/games/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_players: maxPlayers })
      });

      const data = await response.json();

      if (data.success) {
        // Show URLs to share
        this.showGameURLs(data);
      }
    } catch (error) {
      console.error('Failed to create game:', error);
      alert('Failed to create game. Please try again.');
    }
  }

  private showGameURLs(data: any) {
    // Create a modal showing all the URLs
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';

    const creatorUrl = `${window.location.origin}${data.creator_url}`;
    const spectatorUrl = `${window.location.origin}${data.spectator_url}`;
    const playerUrls = data.player_urls.map((url: string) => `${window.location.origin}${url}`);

    modal.innerHTML = `
      <div class="modal" style="max-width: 800px;">
        <div class="modal-header">
          <h2 class="modal-title">🎮 Game Created: ${data.room_code}</h2>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 20px; font-size: 16px;">
            Share these links with players. Each link is unique and can be bookmarked.
          </p>

          <!-- Creator Link -->
          <div style="background: var(--background-tertiary); padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 2px solid var(--primary-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <strong style="color: var(--primary-color);">👑 Creator Link (You)</strong>
              <button onclick="window.open('${creatorUrl}', '_blank')"
                      style="padding: 8px 16px; font-size: 12px;">
                Open in New Tab
              </button>
            </div>
            <input class="form-input" readonly value="${creatorUrl}"
                   onclick="this.select(); navigator.clipboard.writeText(this.value);"
                   style="font-size: 11px; font-family: monospace;">
            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
              Click to copy. You can manage the game and start it.
            </p>
          </div>

          <!-- Player Links -->
          <div style="background: var(--background-tertiary); padding: 15px; border-radius: 8px; margin-bottom: 15px;">
            <strong style="display: block; margin-bottom: 10px;">👥 Player Links (Share these)</strong>
            ${playerUrls.map((url: string, i: number) => `
              <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                  <span style="font-size: 13px; color: var(--text-secondary);">Player ${i + 1}</span>
                  <button onclick="window.open('${url}', '_blank')"
                          style="padding: 6px 12px; font-size: 11px;">
                    Open in New Tab
                  </button>
                </div>
                <input class="form-input" readonly value="${url}"
                       onclick="this.select(); navigator.clipboard.writeText(this.value);"
                       style="font-size: 10px; font-family: monospace; margin-bottom: 0;">
              </div>
            `).join('')}
            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 10px;">
              Click any link to copy it. Each player needs their own unique link.
            </p>
          </div>

          <!-- Spectator Link -->
          <div style="background: var(--background-tertiary); padding: 15px; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <strong>👁️ Spectator Link</strong>
              <button onclick="window.open('${spectatorUrl}', '_blank')"
                      style="padding: 8px 16px; font-size: 12px;">
                Open in New Tab
              </button>
            </div>
            <input class="form-input" readonly value="${spectatorUrl}"
                   onclick="this.select(); navigator.clipboard.writeText(this.value);"
                   style="font-size: 11px; font-family: monospace;">
            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
              For viewing only (display on a large monitor).
            </p>
          </div>

          <div style="margin-top: 20px; padding: 15px; background: var(--background-secondary); border-radius: 8px;">
            <strong>💡 Testing Tips:</strong>
            <ul style="margin: 10px 0 0 20px; font-size: 13px; line-height: 1.8;">
              <li>Click "Open in New Tab" buttons to test in different tabs</li>
              <li>Use incognito windows for separate sessions</li>
              <li>Each link has a unique token - don't mix them up!</li>
              <li>Room Code: <strong>${data.room_code}</strong></li>
            </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button onclick="window.location.href='${data.creator_url}'">
            Go to Game Lobby
          </button>
        </div>
      </div>
    `;

    this.appContainer.appendChild(modal);
  }

  private setupSocketHandlers() {
    // Connection events
    socketService.on('internal:connected', () => {
      console.log('✅ Connected to server');
    });

    socketService.on('internal:disconnected', (data) => {
      console.log('🔌 Disconnected:', data.reason);
      this.showError('Disconnected from server. Attempting to reconnect...');
    });

    socketService.on('internal:connection_error', (data) => {
      console.error('❌ Connection error:', data);
      if (data.attempts >= 5) {
        this.showError('Failed to connect to server. Please refresh the page.');
      }
    });

    // Authentication
    socketService.on('authenticated', (data) => {
      console.log('✅ Authenticated:', data);
      this.authState.authenticated = true;
      this.authState.authType = data.auth_type;

      // If player, prompt for name first
      if (data.auth_type === 'player') {
        this.promptForPlayerName();
      } else {
        // Creator or spectator - show lobby
        this.showGameLobby(data.game);
      }

      // Request current game state
      socketService.requestGameState();
    });

    // Game events
    socketService.on('game_started', (data) => {
      console.log('🎮 Game started');
      soundEffects.playSuccess();
      this.gameState = data.game_state;

      // Switch from lobby to game UI
      this.buildMainUI();
      this.updateUI();
    });

    socketService.on('game_state_update', (data) => {
      console.log('📊 Game state updated');
      this.gameState = data.game_state;
      this.updateUI();
    });

    socketService.on('player_action', (action: PlayerAction) => {
      console.log('🎬 Player action:', action);
      this.actionTicker.addAction(action);
      soundEffects.playChime();
    });

    socketService.on('player_joined', (data) => {
      console.log('👤 Player joined:', data);

      // If this is us joining (our name matches), show the lobby
      if (data.player_name === this.myPlayerName && this.authState.authType === 'player' && !this.gameLobby) {
        this.showGameLobby({ room_code: this.authState.roomCode, max_players: 6 });
      }

      // Update lobby if visible (for all players including us)
      if (this.gameLobby) {
        this.gameLobby.updatePlayers(data.players);
      }

      // Update player list
      this.updatePlayerList(data.players);
    });

    // Errors
    socketService.on('error', (error) => {
      console.error('❌ Error:', error);
      this.showError(error.message || 'An error occurred');
    });
  }

  private setupUIHandlers() {
    // Tab switching
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;

      if (target.classList.contains('tab')) {
        const tabName = target.dataset.tab;
        if (tabName) {
          this.switchTab(tabName);
        }
      }
    });

    // Sound toggle
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;

      if (target.id === 'sound-toggle') {
        const enabled = !soundEffects.isEnabled();
        soundEffects.setEnabled(enabled);
        target.textContent = enabled ? '🔊 Sound On' : '🔇 Sound Off';
      }
    });
  }

  private buildMainUI() {
    this.appContainer.innerHTML = '';

    const container = document.createElement('div');
    container.className = 'app-container';

    // Header
    container.appendChild(this.header.render());

    // Main content with tabs
    const mainContent = document.createElement('div');
    mainContent.className = 'main-content';

    // Tabs navigation
    const tabsNav = document.createElement('div');
    tabsNav.className = 'tabs';
    tabsNav.innerHTML = `
      <div class="tab active" data-tab="auction">🏢 Auction</div>
      <div class="tab" data-tab="map">🗺️ Map</div>
      <div class="tab" data-tab="market">📈 Stock Market</div>
      <div class="tab" data-tab="companies">🏭 Companies</div>
    `;

    mainContent.appendChild(tabsNav);

    // Tab content
    const tabContent = document.createElement('div');
    tabContent.className = 'tab-content';

    // Auction tab (active by default)
    const auctionPanel = document.createElement('div');
    auctionPanel.className = 'tab-panel active';
    auctionPanel.dataset.tab = 'auction';
    auctionPanel.appendChild(this.privateAuction.render());

    // Map tab
    const mapPanel = document.createElement('div');
    mapPanel.className = 'tab-panel';
    mapPanel.dataset.tab = 'map';
    mapPanel.appendChild(this.hexMap.render());

    // Market tab
    const marketPanel = document.createElement('div');
    marketPanel.className = 'tab-panel';
    marketPanel.dataset.tab = 'market';
    marketPanel.appendChild(this.stockMarket.render());

    // Companies tab
    const companiesPanel = document.createElement('div');
    companiesPanel.className = 'tab-panel';
    companiesPanel.dataset.tab = 'companies';
    companiesPanel.innerHTML = '<div class="company-grid" id="company-grid"></div>';

    tabContent.appendChild(auctionPanel);
    tabContent.appendChild(mapPanel);
    tabContent.appendChild(marketPanel);
    tabContent.appendChild(companiesPanel);

    mainContent.appendChild(tabContent);
    container.appendChild(mainContent);

    // Footer (ticker)
    container.appendChild(this.actionTicker.render());

    // Sidebar (player list)
    container.appendChild(this.playerList.render());

    this.appContainer.appendChild(container);
  }

  private switchTab(tabName: string) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
      tab.classList.toggle('active', (tab as HTMLElement).dataset.tab === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
      panel.classList.toggle('active', (panel as HTMLElement).dataset.tab === tabName);
    });

    soundEffects.playClick();
  }

  private updateUI() {
    if (!this.gameState) return;

    // Update header
    this.header.update(this.gameState);

    // Find and set current player ID for auction
    if (this.myPlayerName && this.gameState.players) {
      const myPlayer = this.gameState.players.find((p: any) => p.name === this.myPlayerName);
      if (myPlayer) {
        this.privateAuction.setCurrentPlayer(myPlayer.id);
      }
    }

    // Update private company auction
    this.privateAuction.updateGameState(this.gameState);

    // Update stock market
    if (this.gameState.stock_market) {
      this.stockMarket.update(this.gameState.stock_market);
    }

    // Update player list
    if (this.gameState.players) {
      this.playerList.update(this.gameState.players);
    }

    // Update hex map (if companies have placed tokens, etc.)
    this.hexMap.update(this.gameState);
  }

  private updatePlayerList(players: any[]) {
    this.playerList.update(players);
  }

  private handleMakeMove(moveData: any) {
    console.log(`🎯 Making move:`, moveData);

    // Send move to server via Socket.IO
    socketService.makeMove('BuyPrivateCompanyMove', moveData);
  }

  private showLoading(message: string) {
    this.appContainer.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; gap: 20px;">
        <div style="font-size: 24px;">🚂</div>
        <p style="font-size: 18px;">${message}</p>
      </div>
    `;
  }

  private showError(message: string) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: var(--danger-color);
      color: white;
      padding: 15px 20px;
      border-radius: 8px;
      box-shadow: var(--shadow);
      z-index: 10000;
      animation: slideIn 0.3s;
    `;
    errorDiv.textContent = message;

    this.appContainer.appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }

  private promptForPlayerName() {
    this.appContainer.innerHTML = '';

    // Generate a default Transformer Autobot name
    const autobotNames = [
      'Optimus Prime', 'Bumblebee', 'Jazz', 'Ironhide', 'Ratchet',
      'Prowl', 'Bluestreak', 'Sideswipe', 'Wheeljack', 'Sunstreaker'
    ];
    const randomIndex = Math.floor(Math.random() * autobotNames.length);
    const defaultName = autobotNames[randomIndex];

    const container = document.createElement('div');
    container.className = 'lobby-container';
    container.innerHTML = `
      <h1 class="lobby-title">🚂 Welcome to 1889!</h1>

      <div style="max-width: 500px; margin: 0 auto; background: var(--background-tertiary); padding: 40px; border-radius: 12px;">
        <h2 style="margin-bottom: 20px;">Enter Your Name</h2>

        <div class="form-group">
          <label class="form-label">Player Name:</label>
          <input type="text" id="player-name-input" class="form-input"
                 placeholder="Enter your name..."
                 value="${this.escapeHtml(defaultName)}"
                 maxlength="20"
                 autofocus>
        </div>

        <button id="set-name-btn" style="width: 100%;">Join Game</button>

        <p style="margin-top: 20px; font-size: 14px; color: var(--text-secondary);">
          Choose a name that other players will see during the game.
        </p>
      </div>
    `;

    this.appContainer.appendChild(container);

    const input = container.querySelector('#player-name-input') as HTMLInputElement;
    const button = container.querySelector('#set-name-btn') as HTMLButtonElement;

    const submitName = () => {
      const name = input.value.trim();
      if (name) {
        this.myPlayerName = name; // Remember this player's name
        socketService.joinGame(name);
        this.showLoading('Joining game lobby...');
      }
    };

    button.addEventListener('click', submitName);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        submitName();
      }
    });
  }

  private async showGameLobby(game: any) {
    this.appContainer.innerHTML = '';

    // Fetch current players
    const response = await fetch(`/api/games/${game.room_code}`);
    const gameData = await response.json();

    this.gameLobby = new GameLobby({
      maxPlayers: game.max_players,
      isCreator: this.authState.authType === 'creator',
      onStartGame: (playerNames: string[]) => {
        socketService.startGame(playerNames);
        this.showLoading('Starting game...');
      }
    });

    this.appContainer.appendChild(this.gameLobby.render());

    if (gameData.players) {
      this.gameLobby.updatePlayers(gameData.players);
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
