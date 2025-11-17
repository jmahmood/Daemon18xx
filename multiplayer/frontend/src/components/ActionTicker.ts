/**
 * Action Ticker component - displays real-time game actions in a scrolling ticker
 */

import type { PlayerAction } from '../types';
import { soundEffects } from '../utils/soundEffects';

export class ActionTicker {
  private element: HTMLElement | null = null;
  private actions: PlayerAction[] = [];
  private maxActions = 20;

  render(): HTMLElement {
    const footer = document.createElement('div');
    footer.className = 'footer';

    footer.innerHTML = `
      <div class="ticker-container">
        <div class="ticker-content" id="ticker-content">
          <div class="ticker-item">
            <span class="player-name">System</span>
            <span class="action">Game initialized. Waiting for players...</span>
          </div>
        </div>
        <button class="sound-toggle" id="sound-toggle">🔊 Sound On</button>
      </div>
    `;

    this.element = footer;
    return footer;
  }

  addAction(action: PlayerAction) {
    this.actions.push(action);

    // Keep only recent actions
    if (this.actions.length > this.maxActions) {
      this.actions.shift();
    }

    this.updateTicker();
  }

  private updateTicker() {
    if (!this.element) return;

    const tickerContent = this.element.querySelector('#ticker-content');
    if (!tickerContent) return;

    // Build ticker HTML (duplicate for seamless loop)
    const tickerHTML = this.actions.map(action => `
      <div class="ticker-item">
        <span class="player-name">${this.escapeHtml(action.player_name)}</span>
        <span class="action">${this.escapeHtml(action.action)}</span>
        <span style="color: var(--text-secondary); font-size: 12px;">${this.formatTime(action.timestamp)}</span>
      </div>
    `).join('');

    // Duplicate content for seamless scrolling
    tickerContent.innerHTML = tickerHTML + tickerHTML;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  }
}
