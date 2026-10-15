/**
 * URL parsing utilities for extracting room code and token
 */

export interface URLParams {
  roomCode: string | null;
  token: string | null;
  isSpectator: boolean;
}

export function parseGameURL(): URLParams {
  const url = new URL(window.location.href);
  const pathParts = url.pathname.split('/');

  // Expected format: /game/{room_code}/play or /game/{room_code}/spectate
  let roomCode: string | null = null;
  let isSpectator = false;

  if (pathParts[1] === 'game' && pathParts[2]) {
    roomCode = pathParts[2];
    isSpectator = pathParts[3] === 'spectate';
  }

  const token = url.searchParams.get('token');

  return {
    roomCode,
    token,
    isSpectator
  };
}

export function buildGameURL(roomCode: string, token: string, isSpectator: boolean = false): string {
  const path = isSpectator ? 'spectate' : 'play';
  return `/game/${roomCode}/${path}?token=${token}`;
}
