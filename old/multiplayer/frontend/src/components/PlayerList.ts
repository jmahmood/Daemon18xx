/**
 * Player List component - sidebar showing all players with expandable details
 */

import type { Player } from '../types';

export class PlayerList {
  private element: HTMLElement | null = null;
  private players: Player[] = [];
  private collapsed = false;

  render(): HTMLElement {
    const sidebar = document.createElement('div');
    sidebar.className = 'sidebar';
    sidebar.id = 'player-sidebar';

    sidebar.innerHTML = `
      <div class="player-list" id="player-list">
        <h3 style="margin-bottom: 15px; font-size: 18px;">Players</h3>
        <div id="player-list-items">
          <!-- Player items will be inserted here -->
        </div>
      </div>
    `;

    // Add toggle button
    const toggle = document.createElement('button');
    toggle.className = 'sidebar-toggle';
    toggle.textContent = '👥';
    toggle.onclick = () => this.toggleSidebar();

    this.element = sidebar;
    return sidebar;
  }

  update(players: Player[]) {
    this.players = players;
    this.renderPlayerItems();
  }

  private renderPlayerItems() {
    if (!this.element) return;

    const container = this.element.querySelector('#player-list-items');
    if (!container) return;

    container.innerHTML = this.players.map((player, index) => `
      <div class="player-list-item ${player.isCurrentPlayer ? 'current' : ''}"
           data-player-id="${player.id}">
        <div class="player-name">
          ${index + 1}. ${this.escapeHtml(player.name)}
          ${player.isCurrentPlayer ? '⭐' : ''}
        </div>
        <div class="player-details">
          <span>Cash: $${player.cash}</span>
          <span>Certs: ${player.certificates || 0}</span>
        </div>
      </div>
    `).join('');

    // Add click handlers for expansion (future feature)
    container.querySelectorAll('.player-list-item').forEach(item => {
      item.addEventListener('click', () => {
        const playerId = (item as HTMLElement).dataset.playerId;
        this.showPlayerDetails(playerId);
      });
    });
  }

  private toggleSidebar() {
    if (!this.element) return;

    this.collapsed = !this.collapsed;
    this.element.classList.toggle('collapsed', this.collapsed);
  }

  private showPlayerDetails(playerId?: string) {
    if (!playerId) return;

    const player = this.players.find(p => p.id === playerId);
    if (!player) return;

    // TODO: Show detailed player info in a modal
    console.log('Show details for player:', player);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
