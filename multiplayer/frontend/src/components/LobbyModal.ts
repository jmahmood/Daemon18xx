/**
 * Lobby Modal component - for creating and joining games
 */

interface LobbyModalOptions {
  onCreateGame: (maxPlayers: number) => void;
  onJoinGame: (roomCode: string) => void;
}

export class LobbyModal {
  private options: LobbyModalOptions;

  constructor(options: LobbyModalOptions) {
    this.options = options;
  }

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'lobby-container';

    container.innerHTML = `
      <h1 class="lobby-title">🚂 Daemon18xx - 1889</h1>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
        <!-- Create Game -->
        <div style="padding: 30px; background: var(--background-tertiary); border-radius: 12px;">
          <h2 style="margin-bottom: 20px; font-size: 24px;">Create New Game</h2>

          <div class="form-group">
            <label class="form-label">Max Players:</label>
            <select id="max-players" class="form-input">
              <option value="3">3 Players</option>
              <option value="4">4 Players</option>
              <option value="5">5 Players</option>
              <option value="6" selected>6 Players</option>
            </select>
          </div>

          <button id="create-game-btn" style="width: 100%;">Create Game</button>

          <p style="margin-top: 20px; font-size: 14px; color: var(--text-secondary);">
            You'll receive links to share with other players. Each player gets a unique link.
          </p>
        </div>

        <!-- Join Game -->
        <div style="padding: 30px; background: var(--background-tertiary); border-radius: 12px;">
          <h2 style="margin-bottom: 20px; font-size: 24px;">Join Existing Game</h2>

          <div class="form-group">
            <label class="form-label">Room Code:</label>
            <input type="text" id="room-code" class="form-input"
                   placeholder="Enter 6-character code"
                   maxlength="6"
                   style="text-transform: uppercase;">
          </div>

          <button id="join-game-btn" style="width: 100%;">Join Game</button>

          <p style="margin-top: 20px; font-size: 14px; color: var(--text-secondary);">
            Enter the room code shared by the game creator.
          </p>
        </div>
      </div>

      <div style="margin-top: 40px; padding: 20px; background: var(--background-tertiary); border-radius: 12px;">
        <h3 style="margin-bottom: 15px;">About 1889: History of Shikoku Railways</h3>
        <p style="font-size: 14px; color: var(--text-secondary); line-height: 1.6;">
          1889 is an 18xx game set on the island of Shikoku in Japan. Players invest in railroad companies,
          build track networks, and run trains to generate revenue. The game features 7 public companies
          and 5 private companies. Games typically last 2-3 hours with 3-6 players.
        </p>
      </div>
    `;

    // Add event listeners
    const createBtn = container.querySelector('#create-game-btn');
    createBtn?.addEventListener('click', () => {
      const select = container.querySelector('#max-players') as HTMLSelectElement;
      const maxPlayers = parseInt(select.value);
      this.options.onCreateGame(maxPlayers);
    });

    const joinBtn = container.querySelector('#join-game-btn');
    joinBtn?.addEventListener('click', () => {
      const input = container.querySelector('#room-code') as HTMLInputElement;
      const roomCode = input.value.trim().toUpperCase();

      if (roomCode.length === 6) {
        this.options.onJoinGame(roomCode);
      } else {
        alert('Please enter a valid 6-character room code');
      }
    });

    return container;
  }
}
