/**
 * Stock Market Grid component - displays the stock market with company tokens
 */

import type { StockMarketCell } from '../types';

export class StockMarket {
  private element: HTMLElement | null = null;
  private grid: StockMarketCell[][] = [];

  render(): HTMLElement {
    const container = document.createElement('div');
    container.style.cssText = 'padding: 20px; overflow: auto;';

    const marketContainer = document.createElement('div');
    marketContainer.id = 'stock-market-grid';
    marketContainer.className = 'stock-market';

    container.appendChild(marketContainer);

    // Add legend
    const legend = document.createElement('div');
    legend.style.cssText = 'margin-top: 30px; padding: 20px; background: var(--background-tertiary); border-radius: 8px;';
    legend.innerHTML = `
      <h3 style="margin-bottom: 15px;">Stock Market Legend</h3>
      <div style="display: flex; gap: 30px;">
        <div>
          <span style="display: inline-block; width: 20px; height: 20px; background: #f5f5f5; border: 1px solid #000; margin-right: 8px;"></span>
          <span>White Band</span>
        </div>
        <div>
          <span style="display: inline-block; width: 20px; height: 20px; background: #ffd700; border: 1px solid #000; margin-right: 8px;"></span>
          <span>Yellow Band</span>
        </div>
        <div>
          <span style="display: inline-block; width: 20px; height: 20px; background: #8b4513; border: 1px solid #000; margin-right: 8px;"></span>
          <span>Brown Band</span>
        </div>
      </div>
      <p style="margin-top: 15px; font-size: 14px; color: var(--text-secondary);">
        White: Normal trading | Yellow: Protected from hostile takeovers | Brown: Premium prices
      </p>
    `;

    container.appendChild(legend);

    this.element = container;
    return container;
  }

  update(grid: StockMarketCell[][]) {
    this.grid = grid;
    this.renderGrid();
  }

  private renderGrid() {
    if (!this.element) return;

    const gridContainer = this.element.querySelector('#stock-market-grid');
    if (!gridContainer) return;

    // Set grid dimensions
    const rows = this.grid.length;
    const cols = this.grid[0]?.length || 0;

    (gridContainer as HTMLElement).style.gridTemplateColumns = `repeat(${cols}, 80px)`;
    (gridContainer as HTMLElement).style.gridTemplateRows = `repeat(${rows}, 60px)`;

    // Build grid HTML
    gridContainer.innerHTML = this.grid.map((row, rowIndex) =>
      row.map((cell, colIndex) => this.renderCell(cell, rowIndex, colIndex)).join('')
    ).join('');

    // Add click handlers
    gridContainer.querySelectorAll('.stock-cell').forEach(cellEl => {
      cellEl.addEventListener('click', () => {
        const row = parseInt((cellEl as HTMLElement).dataset.row || '0');
        const col = parseInt((cellEl as HTMLElement).dataset.col || '0');
        this.onCellClick(row, col);
      });
    });
  }

  private renderCell(cell: StockMarketCell, row: number, col: number): string {
    const bandClass = cell.band.toLowerCase();
    const arrow = cell.arrow ? `↗` : '';

    return `
      <div class="stock-cell ${bandClass}" data-row="${row}" data-col="${col}">
        <div class="stock-cell-price">¥${cell.price}</div>
        ${arrow ? `<div style="font-size: 12px;">${arrow}</div>` : ''}
        <div class="stock-cell-companies" id="cell-${row}-${col}-companies"></div>
      </div>
    `;
  }

  private onCellClick(row: number, col: number) {
    const cell = this.grid[row]?.[col];
    if (!cell) return;

    console.log('Clicked cell:', cell);
    // TODO: Show companies at this price, allow trading
  }
}
