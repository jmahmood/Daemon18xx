"""
Custom serialization for Daemon18xx Game objects

The Game object contains module references that can't be pickled.
This module provides safe serialization/deserialization.
"""
import pickle
import base64
from typing import Dict, Any
from pathlib import Path
import sys

# Add parent directory to path to import Daemon18xx
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.state import Game
from app.config import load_config
from app.base import StockPurchaseSource


def serialize_game(game: Game) -> str:
    """
    Serialize a Game object to a base64-encoded string.

    This custom serialization handles module objects that can't be pickled.

    Args:
        game: The Game object to serialize

    Returns:
        Base64-encoded string representation
    """
    # Extract serializable data
    # NOTE: minigame is NOT stored - it's created on-demand via getMinigame()
    serializable_data = {
        'variant': getattr(game, 'variant', '1889'),
        'state': game.state,
        'minigame_class': getattr(game, 'minigame_class', None),
        'player_order_fn_list': getattr(game, 'player_order_fn_list', []),
        'operating_order': getattr(game, 'operating_order', []),
        'last_operating_order': getattr(game, 'last_operating_order', []),
        'current_player': getattr(game, 'current_player', None),
        'errors_list': getattr(game, 'errors_list', []),
    }

    # Pickle the serializable data
    pickled = pickle.dumps(serializable_data)

    # Base64 encode
    return base64.b64encode(pickled).decode('utf-8')


def deserialize_game(serialized: str) -> Game:
    """
    Deserialize a Game object from a base64-encoded string.

    Args:
        serialized: Base64-encoded string representation

    Returns:
        Reconstructed Game object
    """
    # Base64 decode
    pickled = base64.b64decode(serialized)

    # Unpickle the data
    data = pickle.loads(pickled)

    # Reconstruct the Game object
    game = Game()

    # Restore variant and reload config
    variant = data.get('variant', '1889')
    game.variant = variant
    game.config = load_config(variant)

    # Restore other attributes
    # NOTE: minigame is NOT restored - it's created on-demand via getMinigame()
    game.state = data['state']
    game.minigame_class = data.get('minigame_class')
    game.player_order_fn_list = data.get('player_order_fn_list', [])
    game.operating_order = data.get('operating_order', [])
    game.last_operating_order = data.get('last_operating_order', [])
    game.current_player = data.get('current_player')
    game.errors_list = data.get('errors_list', [])

    return game


def serialize_game_state_only(game: Game) -> Dict[str, Any]:
    """
    Serialize only the game state for frontend display (not for saving/loading).

    Returns a plain dict that can be JSON serialized.
    """
    # Determine current player from various sources
    current_player = None
    if hasattr(game, 'current_player') and game.current_player:
        current_player = game.current_player
    elif hasattr(game, 'state') and hasattr(game.state, 'priority_deal_player') and game.state.priority_deal_player:
        # For private company auction, use priority_deal_player
        current_player = game.state.priority_deal_player

    state = {
        'variant': getattr(game, 'variant', '1889'),
        'phase': game.minigame_class if game.minigame_class else 'unknown',
        'current_player': {
            'id': current_player.id,
            'name': current_player.name,
        } if current_player else None,
        'players': [],
        'private_companies': [],
        'public_companies': [],
        'stock_market': None,
        'round_info': {},
        'available_trains': [],
        'game_phase': 'yellow',  # Track phase for tile color restrictions
    }

    # Serialize players
    if hasattr(game, 'state') and hasattr(game.state, 'players'):
        state['players'] = [
            {
                'id': p.id,
                'name': p.name,
                'cash': p.cash,
                'order': p.order,
                'certificates': p.getCertificateCount() if hasattr(p, 'getCertificateCount') else 0,
                'holdings': {
                    company.short_name: company.owners.get(p, 0)
                    for company in p.portfolio
                } if hasattr(p, 'portfolio') else {}
            }
            for p in game.state.players
        ]

    # Serialize private companies
    if hasattr(game, 'state') and hasattr(game.state, 'private_companies'):
        # Filter private companies based on player count (1889 rules)
        player_count = len(game.state.players) if hasattr(game.state, 'players') else 6
        all_privates = game.state.private_companies

        # Sort by cost to determine which to use
        sorted_privates = sorted(all_privates, key=lambda pc: pc.cost)

        # 1889 rules: 3 players=5 companies, 4 players=6 companies, 5-6 players=7 companies
        if player_count == 3:
            companies_to_use = sorted_privates[:5]  # Use 5 cheapest
        elif player_count == 4:
            companies_to_use = sorted_privates[:6]  # Use 6 cheapest
        else:
            companies_to_use = sorted_privates  # Use all 7

        state['private_companies'] = [
            {
                'name': pc.name,
                'short_name': getattr(pc, 'short_name', pc.name[:3]),
                'cost': pc.cost,
                'actual_cost': getattr(pc, 'actual_cost', pc.cost),
                'revenue': getattr(pc, 'revenue', 0),
                'owner': pc.belongs_to.name if pc.belongs_to else None,
                'owner_id': pc.belongs_to.id if pc.belongs_to else None,
                'order': getattr(pc, 'order', 0),
                'bids': [
                    {
                        'player_id': bid.player.id,
                        'player_name': bid.player.name,
                        'amount': bid.bid_amount
                    }
                    for bid in (getattr(pc, 'player_bids', None) or [])
                ],
                'highest_bid': max([bid.bid_amount for bid in (getattr(pc, 'player_bids', None) or [])], default=0)
            }
            for pc in companies_to_use
        ]

    # Serialize public companies
    if hasattr(game, 'state') and hasattr(game.state, 'public_companies'):
        state['public_companies'] = [
            {
                'id': c.id,
                'name': c.name,
                'short_name': c.short_name,
                'floated': c.isFloated() if c.isFloated() is not None else False,
                'ipo_price': c.stockPrice.get(StockPurchaseSource.IPO, 0) if hasattr(c, 'stockPrice') else 0,
                'market_price': c.stockPrice.get(StockPurchaseSource.BANK, 0) if hasattr(c, 'stockPrice') else 0,
                'ipo_shares': c.stocks.get(StockPurchaseSource.IPO, 0) if hasattr(c, 'stocks') else 0,
                'bank_shares': c.stocks.get(StockPurchaseSource.BANK, 0) if hasattr(c, 'stocks') else 0,
                'president': c.president.name if hasattr(c, 'president') and c.president else None,
                'president_id': c.president.id if hasattr(c, 'president') and c.president else None,
                'cash': c.cash if c.cash is not None else 0,
                'stock_position': getattr(c, 'stock_pos', (0, 0)),
                'shareholders': {
                    player.name: amount
                    for player, amount in (c.owners.items() if hasattr(c, 'owners') else {})
                },
                'outstanding_shares': getattr(c, 'outstanding_shares', 0),
                'bankrupt': getattr(c, 'bankrupt', False),
                # Operating Round specific fields
                'trains': [
                    {
                        'type': train.type,
                        'cost': train.cost,
                        'rusts_on': train.rusts_on
                    }
                    for train in (c.trains or [])
                ] if hasattr(c, 'trains') and c.trains else [],
                'tokens_available': getattr(c, 'tokens_available', 0),
                'token_costs': getattr(c, 'token_costs', []),
                'tokens_placed': [
                    {
                        'location': token.location,
                        'company_id': token.company.id if hasattr(token, 'company') else c.id
                    }
                    for token in (c.tokens or [])
                ] if hasattr(c, 'tokens') and c.tokens else [],
            }
            for c in game.state.public_companies
        ]

    # Serialize stock market grid
    if hasattr(game, 'config') and hasattr(game.config, 'STOCK_MARKET'):
        stock_market = game.config.STOCK_MARKET
        if hasattr(stock_market, 'grid'):
            state['stock_market'] = [
                [
                    {
                        'price': cell.price,
                        'band': cell.band.name if hasattr(cell.band, 'name') else str(cell.band),
                        'arrow': cell.arrow.name if cell.arrow and hasattr(cell.arrow, 'name') else None
                    }
                    for cell in row
                ]
                for row in stock_market.grid
            ]

    # Serialize round information
    if hasattr(game, 'state'):
        state['round_info'] = {
            'stock_round_count': getattr(game.state, 'stock_round_count', 0),
            'stock_round_play': getattr(game.state, 'stock_round_play', 0),
            'stock_round_passed': getattr(game.state, 'stock_round_passed', 0),
            'operating_order': getattr(game, 'operating_order', []),
            'last_operating_order': getattr(game, 'last_operating_order', []),
            'track_laid': list(getattr(game.state, 'track_laid', set())),
        }

    # Serialize available trains from config
    if hasattr(game, 'config') and hasattr(game.config, 'TRAINS'):
        state['available_trains'] = [
            {
                'type': train.type,
                'cost': train.cost,
                'rusts_on': train.rusts_on
            }
            for train in game.config.TRAINS
        ]

    return state
