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
    """1846 starting cash: $600 for 2 players, $400 for 3-5 players"""
    if num_players == 2:
        return 600
    return 400


# 1846 has 12 private companies (including 2 minor corporations)
# Note: MS and BIG4 are special "minor corporations" with their own trains
PRIVATE_COMPANIES = [
    # Minor Corporations (operate like companies)
    PrivateCompany.initiate(1, "Michigan Southern", "MS", 60, 0, "C15"),  # Has own train
    PrivateCompany.initiate(2, "Big 4", "BIG4", 40, 0, "G9"),  # Has own train

    # Standard Private Companies
    PrivateCompany.initiate(3, "Chicago and Western Indiana", "C&WI", 60, 10, "D6"),
    PrivateCompany.initiate(4, "Mail Contract", "MAIL", 80, 0, "MAIL"),  # +$10 per city
    PrivateCompany.initiate(5, "Tunnel Blasting Company", "TBC", 60, 20, "TBC"),
    PrivateCompany.initiate(6, "Meat Packing Company", "MPC", 60, 15, "MPC"),
    PrivateCompany.initiate(7, "Steamboat Company", "SC", 40, 10, "SC"),
    PrivateCompany.initiate(8, "Lake Shore Line", "LSL", 40, 15, "LSL"),
    PrivateCompany.initiate(9, "Michigan Central", "MC", 40, 15, "B10/B12"),
    PrivateCompany.initiate(10, "Ohio & Indiana", "O&I", 40, 15, "F14/F16"),
    PrivateCompany.initiate(11, "Boomtown", "BT", 40, 10, "H12"),
    PrivateCompany.initiate(12, "Little Miami", "LM", 40, 15, "H12/F10"),
]

# 7 major corporations
TOKEN_COUNTS = {
    "PRR": 5,  # Pennsylvania Railroad
    "NYC": 4,  # New York Central Railroad
    "B&O": 4,  # Baltimore & Ohio Railroad
    "C&O": 4,  # Chesapeake & Ohio Railroad
    "ERIE": 4,  # Erie Railroad
    "GT": 3,  # Grand Trunk Railway
    "IC": 4,  # Illinois Central Railroad
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.GREEN: 0,
    Color.BROWN: 80,  # 1846 uses $80 for brown
    Color.RED: 0,  # No red tiles in 1846
}

# 1846 terrain multipliers (Tunnel Blasting Company reduces these)
TERRAIN_MULTIPLIERS = {
    TerrainType.NORMAL: 1.0,
    TerrainType.MOUNTAIN: 2.0,   # Mountains cost double
    TerrainType.BRIDGE: 1.5,     # Bridges cost 1.5x in 1846
    TerrainType.TUNNEL: 2.0,     # Tunnels cost double
}

SPECIAL_HEX_RULES = {
    "D6": "Chicago - C&WI reserves a token slot",
    "C15": "Detroit - MS starts here",
    "G9": "Indianapolis - BIG4 starts here",
    "B10": "Michigan Central reserved hex",
    "B12": "Michigan Central reserved hex",
    "F14": "Ohio & Indiana reserved hex",
    "F16": "Ohio & Indiana reserved hex",
    "H12": "Cincinnati - Boomtown adds $20 bonus",
    "F10": "Dayton - Little Miami connection point",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="PRR", name="Pennsylvania Railroad", short_name="PRR",
                           tokens_available=5, token_costs=[0, 40, 60, 80, 100]),
    PublicCompany.initiate(id="NYC", name="New York Central Railroad", short_name="NYC",
                           tokens_available=4, token_costs=[0, 40, 60, 80]),
    PublicCompany.initiate(id="B&O", name="Baltimore & Ohio Railroad", short_name="B&O",
                           tokens_available=4, token_costs=[0, 40, 60, 80]),
    PublicCompany.initiate(id="C&O", name="Chesapeake & Ohio Railroad", short_name="C&O",
                           tokens_available=4, token_costs=[0, 40, 60, 80]),
    PublicCompany.initiate(id="ERIE", name="Erie Railroad", short_name="ERIE",
                           tokens_available=4, token_costs=[0, 40, 60, 80]),
    PublicCompany.initiate(id="GT", name="Grand Trunk Railway", short_name="GT",
                           tokens_available=3, token_costs=[0, 40, 60]),
    PublicCompany.initiate(id="IC", name="Illinois Central Railroad", short_name="IC",
                           tokens_available=4, token_costs=[0, 40, 60, 80]),
]

# 1846 uses a ONE-DIMENSIONAL stock market (single row)
# Prices: $0, $10-$100 (by $10), then $112, $124, $137, $150, $165, $180,
# $195, $212, $230, $250, $270, $295, $320, $345, $375, $405, $440, $475, $510, $550
# Par prices available: $40-$100 (by $10) plus $112, $124, $137, $150
STOCK_MARKET_GRID: list[list[Cell]] = [
    [
        Cell(0, Band.WHITE),  # Company bankrupt
        Cell(10, Band.WHITE),
        Cell(20, Band.WHITE),
        Cell(30, Band.WHITE),
        Cell(40, Band.YELLOW),   # Par price
        Cell(50, Band.YELLOW),   # Par price
        Cell(60, Band.YELLOW),   # Par price
        Cell(70, Band.YELLOW),   # Par price
        Cell(80, Band.YELLOW),   # Par price
        Cell(90, Band.YELLOW),   # Par price
        Cell(100, Band.YELLOW),  # Par price
        Cell(112, Band.YELLOW),  # Par price
        Cell(124, Band.YELLOW),  # Par price
        Cell(137, Band.YELLOW),  # Par price
        Cell(150, Band.YELLOW),  # Par price
        Cell(165, Band.BROWN),
        Cell(180, Band.BROWN),
        Cell(195, Band.BROWN),
        Cell(212, Band.BROWN),
        Cell(230, Band.BROWN),
        Cell(250, Band.BROWN),
        Cell(270, Band.BROWN),
        Cell(295, Band.BROWN),
        Cell(320, Band.BROWN),
        Cell(345, Band.BROWN),
        Cell(375, Band.BROWN),
        Cell(405, Band.BROWN),
        Cell(440, Band.BROWN),
        Cell(475, Band.BROWN),
        Cell(510, Band.BROWN),
        Cell(550, Band.BROWN),
    ]
]

STOCK_MARKET = StockMarket(STOCK_MARKET_GRID)

# 1846 Train Roster
# 2 trains: $80, obsolete on 5, rust on 6
# 4 trains: $180, obsolete on 6 (also has 3+4 variant)
# 5 trains: $500 (also has 2+5 variant)
# 6 trains: $800 (also has 3+6 variant)
TRAINS = [
    Train("2", 80, rusts_on="6"),     # Obsolete on 5, rusts on 6
    Train("4", 180, rusts_on=None),   # Obsolete on 6
    Train("5", 500, rusts_on=None),
    Train("6", 800, rusts_on=None),
]

# 1846 uses 1-3 operating rounds per set depending on phase
OPERATING_ROUNDS = 2  # Default; actual count varies by phase

