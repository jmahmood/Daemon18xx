/**
 * Hex Map component - SVG-based interactive map with zoom and pan
 */

import type { GameState } from '../types';

// Hex map data (hardcoded for 1889, but could be loaded from shared/1889_map.py)
const HEX_MAP_DATA = [
  // Major cities
  { coord: 'C6', type: 'city', name: 'Matsuyama', value: 30, x: 3, y: 6 },
  { coord: 'D4', type: 'city', name: 'Takamatsu', value: 30, x: 4, y: 4 },
  { coord: 'D5', type: 'city', name: 'Kotohira', value: 20, x: 4, y: 5 },
  { coord: 'E6', type: 'city', name: 'Kochi', value: 30, x: 5, y: 6 },
  { coord: 'E8', type: 'city', name: 'Tokushima', value: 30, x: 5, y: 8 },
  { coord: 'B7', type: 'city', name: 'Uwajima', value: 20, x: 2, y: 7 },

  // Plains
  { coord: 'B3', type: 'plain', x: 2, y: 3 },
  { coord: 'B4', type: 'plain', x: 2, y: 4 },
  { coord: 'B5', type: 'plain', x: 2, y: 5 },
  { coord: 'B6', type: 'plain', x: 2, y: 6 },
  { coord: 'C2', type: 'plain', x: 3, y: 2 },
  { coord: 'C3', type: 'plain', x: 3, y: 3 },
  { coord: 'C4', type: 'plain', x: 3, y: 4 },
  { coord: 'C7', type: 'plain', x: 3, y: 7 },
  { coord: 'D2', type: 'plain', x: 4, y: 2 },
  { coord: 'D3', type: 'plain', x: 4, y: 3 },
  { coord: 'D7', type: 'plain', x: 4, y: 7 },
  { coord: 'D8', type: 'plain', x: 4, y: 8 },
  { coord: 'E2', type: 'plain', x: 5, y: 2 },
  { coord: 'E3', type: 'plain', x: 5, y: 3 },
  { coord: 'E4', type: 'plain', x: 5, y: 4 },
  { coord: 'E7', type: 'plain', x: 5, y: 7 },

  // Mountains
  { coord: 'B2', type: 'mountain', x: 2, y: 2 },
  { coord: 'C5', type: 'mountain', x: 3, y: 5 },
  { coord: 'C8', type: 'mountain', x: 3, y: 8 },
  { coord: 'D6', type: 'mountain', x: 4, y: 6 },
  { coord: 'E5', type: 'mountain', x: 5, y: 5 },

  // Water
  { coord: 'A2', type: 'water', x: 1, y: 2 },
  { coord: 'A3', type: 'water', x: 1, y: 3 },
  { coord: 'A4', type: 'water', x: 1, y: 4 },
  { coord: 'A5', type: 'water', x: 1, y: 5 },
  { coord: 'D1', type: 'water', x: 4, y: 1 },
];

export class HexMap {
  private element: HTMLElement | null = null;
  private svg: SVGElement | null = null;
  private viewBox = { x: 0, y: 0, width: 1000, height: 800 };
  private scale = 1;
  private isPanning = false;
  private lastPanPoint = { x: 0, y: 0 };

  render(): HTMLElement {
    const container = document.createElement('div');
    container.className = 'hex-map-container';

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'hex-map-svg');
    svg.setAttribute('viewBox', `${this.viewBox.x} ${this.viewBox.y} ${this.viewBox.width} ${this.viewBox.height}`);

    // Render hexes
    HEX_MAP_DATA.forEach(hex => {
      const hexGroup = this.createHexElement(hex);
      svg.appendChild(hexGroup);
    });

    container.appendChild(svg);

    // Add zoom/pan controls
    this.setupZoomPan(container, svg);

    this.element = container;
    this.svg = svg;

    return container;
  }

  update(gameState: GameState) {
    // TODO: Update hex map with placed tokens, tracks, etc.
    console.log('Updating hex map with game state:', gameState);
  }

  private createHexElement(hex: any): SVGElement {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');

    // Calculate hex position (offset grid)
    const hexSize = 60;
    const hexWidth = hexSize * Math.sqrt(3);
    const hexHeight = hexSize * 2;
    const offsetX = 50;
    const offsetY = 50;

    const x = offsetX + hex.x * hexWidth * 0.75;
    const y = offsetY + hex.y * hexHeight * 0.5 + (hex.x % 2) * hexHeight * 0.25;

    // Create hexagon path
    const hexPath = this.createHexagonPath(x, y, hexSize);
    hexPath.setAttribute('class', `hex hex-${hex.type}`);
    group.appendChild(hexPath);

    // Add coord label
    const coordText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    coordText.setAttribute('x', x.toString());
    coordText.setAttribute('y', (y - hexSize * 0.5).toString());
    coordText.setAttribute('class', 'hex-label');
    coordText.textContent = hex.coord;
    group.appendChild(coordText);

    // Add city name and value if applicable
    if (hex.type === 'city') {
      const cityName = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      cityName.setAttribute('x', x.toString());
      cityName.setAttribute('y', y.toString());
      cityName.setAttribute('class', 'hex-text');
      cityName.textContent = hex.name;
      group.appendChild(cityName);

      const cityValue = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      cityValue.setAttribute('x', x.toString());
      cityValue.setAttribute('y', (y + 15).toString());
      cityValue.setAttribute('class', 'hex-text');
      cityValue.textContent = `¥${hex.value}`;
      group.appendChild(cityValue);
    }

    // Add click handler
    group.style.cursor = 'pointer';
    group.addEventListener('click', () => this.onHexClick(hex));

    return group;
  }

  private createHexagonPath(x: number, y: number, size: number): SVGElement {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

    const points: [number, number][] = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i;
      const px = x + size * Math.cos(angle);
      const py = y + size * Math.sin(angle);
      points.push([px, py]);
    }

    const pathData = `M ${points.map(p => p.join(',')).join(' L ')} Z`;
    path.setAttribute('d', pathData);

    return path;
  }

  private setupZoomPan(container: HTMLElement, svg: SVGElement) {
    // Mouse wheel zoom
    container.addEventListener('wheel', (e) => {
      e.preventDefault();

      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      this.scale *= delta;
      this.scale = Math.max(0.5, Math.min(3, this.scale)); // Limit zoom

      this.updateViewBox();
    });

    // Pan with mouse drag
    container.addEventListener('mousedown', (e) => {
      this.isPanning = true;
      this.lastPanPoint = { x: e.clientX, y: e.clientY };
      container.style.cursor = 'grabbing';
    });

    container.addEventListener('mousemove', (e) => {
      if (!this.isPanning) return;

      const dx = (this.lastPanPoint.x - e.clientX) / this.scale;
      const dy = (this.lastPanPoint.y - e.clientY) / this.scale;

      this.viewBox.x += dx;
      this.viewBox.y += dy;

      this.lastPanPoint = { x: e.clientX, y: e.clientY };
      this.updateViewBox();
    });

    container.addEventListener('mouseup', () => {
      this.isPanning = false;
      container.style.cursor = 'grab';
    });

    container.addEventListener('mouseleave', () => {
      this.isPanning = false;
      container.style.cursor = 'grab';
    });
  }

  private updateViewBox() {
    if (!this.svg) return;

    const width = 1000 / this.scale;
    const height = 800 / this.scale;

    this.svg.setAttribute('viewBox',
      `${this.viewBox.x} ${this.viewBox.y} ${width} ${height}`
    );
  }

  private onHexClick(hex: any) {
    console.log('Clicked hex:', hex);
    // TODO: Handle hex interaction (place token, etc.)
  }
}
