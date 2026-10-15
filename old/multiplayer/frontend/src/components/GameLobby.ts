/**
 * Game Lobby component - shows players waiting and allows starting the game
 */

export class GameLobby {
  private element: HTMLElement | null = null;
  private players: any[] = [];
  private maxPlayers: number = 6;
  private isCreator: boolean = false;
  private onStartGame?: (playerNames: string[]) => void;

  constructor(options: {
    maxPlayers: number;
    isCreator: boolean;
    onStartGame?: (playerNames: string[]) => void;
  }) {
    this.maxPlayers = options.maxPlayers;
    this.isCreator = options.isCreator;
    this.onStartGame = options.onStartGame;
  }

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'lobby-container';
    container.id = 'game-lobby';

    container.innerHTML = `
      <h1 class="lobby-title">🚂 Game Lobby</h1>

      <div style="background: var(--background-tertiary); padding: 20px; border-radius: 12px; margin-bottom: 20px;">
        <h3 style="margin-bottom: 15px;">Waiting for Players...</h3>
        <div class="player-slots" id="player-slots">
          ${this.renderPlayerSlots()}
        </div>
      </div>

      ${this.isCreator ? `
        <div style="background: var(--background-tertiary); padding: 20px; border-radius: 12px;">
          <h3 style="margin-bottom: 15px;">Creator Controls</h3>

          <div class="form-group">
            <label class="form-label">Number of Players:</label>
            <select id="active-player-count" class="form-input">
              <option value="3">3 Players</option>
              <option value="4">4 Players</option>
              <option value="5">5 Players</option>
              <option value="6" selected>6 Players</option>
            </select>
            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
              Only the selected number of players will be used. Empty slots will be ignored.
            </p>
          </div>

          <button id="start-game-btn" style="width: 100%;" disabled>
            Start Game (Waiting for players...)
          </button>

          <p style="margin-top: 15px; font-size: 14px; color: var(--text-secondary);">
            Need at least 3 players with names to start.
          </p>
        </div>
      ` : `
        <div style="text-align: center; padding: 20px; background: var(--background-tertiary); border-radius: 12px;">
          <p style="font-size: 16px;">Waiting for the game creator to start...</p>
        </div>
      `}
    `;

    this.element = container;
    this.setupEventListeners();
    return container;
  }

  private renderPlayerSlots(): string {
    const slots = [];
    for (let i = 0; i < this.maxPlayers; i++) {
      const player = this.players[i];
      const isPending = player && player.player_name.includes('(pending)');
      const hasName = player && !isPending;

      slots.push(`
        <div class="player-slot ${hasName ? 'filled' : 'empty'}">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
              <strong>Player ${i + 1}:</strong>
              ${hasName ? `
                <span style="color: var(--success-color); margin-left: 10px;">
                  ${this.escapeHtml(player.player_name)} ✓
                </span>
              ` : isPending ? `
                <span style="color: var(--warning-color); margin-left: 10px;">
                  Connected (setting name...)
                </span>
              ` : `
                <span style="color: var(--text-secondary); margin-left: 10px;">
                  Empty
                </span>
              `}
            </div>
          </div>
        </div>
      `);
    }
    return slots.join('');
  }

  updatePlayers(players: any[]) {
    this.players = players.sort((a, b) => a.player_order - b.player_order);
    this.refresh();
  }

  private refresh() {
    if (!this.element) return;

    const slotsContainer = this.element.querySelector('#player-slots');
    if (slotsContainer) {
      slotsContainer.innerHTML = this.renderPlayerSlots();
    }

    // Update start button state
    if (this.isCreator) {
      const startBtn = this.element.querySelector('#start-game-btn') as HTMLButtonElement;
      const playerCountSelect = this.element.querySelector('#active-player-count') as HTMLSelectElement;

      if (startBtn && playerCountSelect) {
        const targetCount = parseInt(playerCountSelect.value);
        const readyPlayers = this.players.filter(p => !p.player_name.includes('(pending)')).slice(0, targetCount);
        const canStart = readyPlayers.length >= 3 && readyPlayers.length >= targetCount;

        startBtn.disabled = !canStart;
        if (canStart) {
          startBtn.textContent = `Start Game with ${readyPlayers.length} Players`;
        } else {
          startBtn.textContent = `Start Game (Need ${targetCount - readyPlayers.length} more players)`;
        }
      }
    }
  }

  private setupEventListeners() {
    if (!this.element || !this.isCreator) return;

    const startBtn = this.element.querySelector('#start-game-btn');
    const playerCountSelect = this.element.querySelector('#active-player-count');

    if (startBtn) {
      startBtn.addEventListener('click', () => {
        this.handleStartGame();
      });
    }

    if (playerCountSelect) {
      playerCountSelect.addEventListener('change', () => {
        this.refresh();
      });
    }
  }

  private handleStartGame() {
    if (!this.onStartGame || !this.element) return;

    const playerCountSelect = this.element.querySelector('#active-player-count') as HTMLSelectElement;
    const targetCount = parseInt(playerCountSelect.value);

    // Get players with names (not pending)
    const readyPlayers = this.players
      .filter(p => !p.player_name.includes('(pending)'))
      .slice(0, targetCount)
      .map(p => p.player_name);

    if (readyPlayers.length >= 3) {
      this.onStartGame(readyPlayers);
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
