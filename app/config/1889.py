from app.base import (
    PrivateCompany,
    PublicCompany,
    Train,
    Color,
    Cell,
    StockMarket,
    Band,
    Direction,
    TerrainType,
)


def starting_cash(num_players: int) -> int:
    """1889 starting cash: 420¥ for 2-4 players, 390¥ for 5-6 players"""
    if num_players <= 4:
        return 420
    return 390


# 1889 Shikoku - 7 private companies
PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Takamatsu E-Railroad", "TR", 20, 5, "K4"),
    PrivateCompany.initiate(2, "Mitsubishi Ferry", "MF", 30, 5, "MF"),  # Port tile placement
    PrivateCompany.initiate(3, "Ehime Railway", "ER", 40, 10, "C4"),
    PrivateCompany.initiate(4, "Sumitomo Mines Railway", "SMR", 50, 15, "SMR"),  # Ignore mountain costs
    PrivateCompany.initiate(5, "Dougo Railway", "DR", 60, 15, "DR"),  # Exchange for IR share
    PrivateCompany.initiate(6, "South Iyo Railway", "SIR", 80, 20, "SIR"),
    PrivateCompany.initiate(7, "Uno-Takamatsu Ferry", "UTF", 150, 30, "UTF"),  # Revenue increases to 50 on first 5-train
]

# 7 corporations in 1889 Shikoku
TOKEN_COUNTS = {
    "AR": 2,  # Awa Railroad
    "IR": 2,  # Iyo Railway
    "SR": 2,  # Sanuki Railway
    "KO": 2,  # Takamatsu & Kotohira Electric Railway
    "TR": 3,  # Tosa Electric Railway
    "KU": 1,  # Tosa Kuroshio Railway (only 1 token!)
    "UR": 3,  # Uwajima Railway
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.GREEN: 0,
    Color.BROWN: 0,  # Brown tile upgrades are free in 1889
    Color.RED: 0,
}

# 1889 terrain multipliers (Sumitomo Mines Railway can ignore mountain costs)
# Note: Since track laying is free in 1889, multipliers have no effect unless
# future expansion adds terrain costs
TERRAIN_MULTIPLIERS = {
    TerrainType.NORMAL: 1.0,
    TerrainType.MOUNTAIN: 2.0,   # Mountains would cost double if base cost > 0
    TerrainType.BRIDGE: 1.5,     # Bridges would cost 1.5x if base cost > 0
    TerrainType.TUNNEL: 2.0,     # Tunnels would cost double if base cost > 0
}

SPECIAL_HEX_RULES = {
    "K4": "Takamatsu E-Railroad blocks while player-owned",
    "C4": "Ehime Railway blocks until sold to corporation",
    "MF": "Mitsubishi Ferry - port tile placement",
    "SMR": "Sumitomo Mines - ignore mountain costs (no rivers)",
    "DR": "Dougo Railway - exchangeable for 10% IR share",
    "UTF": "Uno-Takamatsu Ferry - revenue increases to 50¥",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="AR", name="Awa Railroad", short_name="AR",
                           tokens_available=2, token_costs=[0, 40]),
    PublicCompany.initiate(id="IR", name="Iyo Railway", short_name="IR",
                           tokens_available=2, token_costs=[0, 40]),
    PublicCompany.initiate(id="SR", name="Sanuki Railway", short_name="SR",
                           tokens_available=2, token_costs=[0, 40]),
    PublicCompany.initiate(id="KO", name="Takamatsu & Kotohira Electric Railway", short_name="KO",
                           tokens_available=2, token_costs=[0, 40]),
    PublicCompany.initiate(id="TR", name="Tosa Electric Railway", short_name="TR",
                           tokens_available=3, token_costs=[0, 40, 40]),
    PublicCompany.initiate(id="KU", name="Tosa Kuroshio Railway", short_name="KU",
                           tokens_available=1, token_costs=[0]),  # Only 1 token!
    PublicCompany.initiate(id="UR", name="Uwajima Railway", short_name="UR",
                           tokens_available=3, token_costs=[0, 40, 40]),
]

# 1889 uses a 15×11 stock market grid
# Rows: 10¥ to 350¥ (11 rows)
# Columns: 15 price points per row
# Par value is typically 100¥
STOCK_MARKET_GRID: list[list[Cell]] = []

# 1889 stock market is complex with varying prices per row
# Simplified version with representative prices
prices_by_row = [
    # Row 0 (bottom, yellow/orange zone)
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150],
    # Row 1
    [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 165],
    # Row 2
    [30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 155, 170, 185],
    # Row 3
    [40, 50, 60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 195, 210],
    # Row 4
    [50, 60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 195, 210, 230],
    # Row 5
    [60, 70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 195, 210, 230, 250],
    # Row 6
    [70, 80, 90, 100, 110, 120, 135, 150, 165, 180, 195, 210, 230, 250, 275],
    # Row 7
    [80, 90, 100, 110, 120, 135, 150, 165, 180, 195, 210, 230, 250, 275, 300],
    # Row 8
    [90, 100, 110, 120, 135, 150, 165, 180, 195, 210, 230, 250, 275, 300, 325],
    # Row 9
    [100, 110, 120, 135, 150, 165, 180, 195, 210, 230, 250, 275, 300, 325, 350],
    # Row 10 (top)
    [110, 120, 135, 150, 165, 180, 195, 210, 230, 250, 275, 300, 325, 350, 350],
]

for row_idx, row_prices in enumerate(prices_by_row):
    row = []
    for col_idx, price in enumerate(row_prices):
        # Yellow band for lower prices (rows 0-2), white for mid, brown for high
        if row_idx <= 2:
            band = Band.YELLOW
        elif row_idx >= 8:
            band = Band.BROWN
        else:
            band = Band.WHITE
        row.append(Cell(price, band))
    STOCK_MARKET_GRID.append(row)

STOCK_MARKET = StockMarket(STOCK_MARKET_GRID)

# 1889 Train Roster
# 2 trains: 80¥, rust on 4 (6 available)
# 3 trains: 180¥, rust on 6 (5 available)
# 4 trains: 300¥, rust on D (4 available)
# 5 trains: 450¥ (3 available)
# 6 trains: 630¥ (2 available)
# D trains: 1100¥ (unlimited, available in phase 6, -300¥ discount with trade-in)
TRAINS = [
    Train("2", 80, rusts_on="4"),
    Train("3", 180, rusts_on="6"),
    Train("4", 300, rusts_on="D"),
    Train("5", 450, rusts_on=None),
    Train("6", 630, rusts_on=None),
    Train("D", 1100, rusts_on=None),  # Diesel, unlimited quantity
]

# 1889 uses 1-2 operating rounds per set
OPERATING_ROUNDS = 2
