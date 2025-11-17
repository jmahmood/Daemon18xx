/**
 * Main entry point for Daemon18xx multiplayer client
 */

import { App } from './app';
import './style.css';

// Initialize application
const app = new App();
app.initialize();

// Expose for debugging
(window as any).__app = app;
