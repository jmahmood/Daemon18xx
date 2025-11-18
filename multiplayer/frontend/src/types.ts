/**
 * TypeScript type definitions for Daemon18xx multiplayer
 */

export interface Player {
  id: string;
  name: string;
  cash: number;
  order: number;
  certificates?: number;
  isCurrentPlayer?: boolean;
}

export interface Company {
  id: string;
  name: string;
  short_name: string;
  price: number;
  shares_owned: Record<string, number>;
  president?: string;
  cash: number;
  tokens: number;
  floated: boolean;
}

export interface StockMarketCell {
  price: number;
  band: 'WHITE' | 'YELLOW' | 'BROWN';
  arrow?: string;
}

export interface GameState {
  variant: string;
  phase: string;
  players: Player[];
  companies?: Company[];
  stock_market?: StockMarketCell[][];
  current_player?: {
    id: string;
    name: string;
  };
  private_companies?: any[];
  public_companies?: any[];
  operating_order?: string[];
  round_info?: {
    stock_round_count?: number;
    stock_round_play?: number;
    stock_round_passed?: number;
    operating_order?: string[];
    last_operating_order?: string[];
    track_laid?: string[];
  };
  raw?: any;
}

export interface PlayerAction {
  player_name: string;
  action: string;
  timestamp: string;
  is_system?: boolean;
}

export interface GameInfo {
  game_id: number;
  room_code: string;
  variant: string;
  status: string;
  max_players: number;
}

export interface HexCoord {
  row: string; // A, B, C, etc.
  col: number; // 1, 2, 3, etc.
}

export interface HexTile {
  coord: string;
  terrain_type: string;
  city_name?: string;
  city_value?: number;
  city_slots?: number;
  special?: string;
}

export type AuthType = 'creator' | 'player' | 'spectator';

export interface AuthState {
  authenticated: boolean;
  authType?: AuthType;
  playerName?: string;
  roomCode?: string;
  token?: string;
}
