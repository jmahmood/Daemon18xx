from app.base import (
    PrivateCompany,
    PublicCompany,
    Train,
    Color,
    Cell,
    StockMarket,
    Band,
    Direction,
)


def starting_cash(num_players: int) -> int:
    """Starting cash for 1889 based on player count"""
    return int(2500 / num_players)


# 1889 uses 5 private companies based on Shikoku railways
PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Ehime Railway", "ER", 20, 5, "C6"),
    PrivateCompany.initiate(2, "Kotohira Railway", "KR", 40, 10, "D5"),
    PrivateCompany.initiate(3, "Awa Railway", "AR", 80, 15, "E8"),
    PrivateCompany.initiate(4, "Takamatsu Electric Tramway", "TET", 160, 20, "D4"),
    PrivateCompany.initiate(5, "Uwajima Railway", "UR", 200, 25, "B7"),
]

# 1889 has 7 public companies representing major Shikoku railways
PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="AR", name="Awa Railway", short_name="AR",
                           tokens_available=2, token_costs=[40, 100]),
    PublicCompany.initiate(id="IR", name="Iyo Railway", short_name="IR",
                           tokens_available=3, token_costs=[40, 100, 100]),
    PublicCompany.initiate(id="SR", name="Sanuki Railway", short_name="SR",
                           tokens_available=3, token_costs=[40, 100, 100]),
    PublicCompany.initiate(id="KO", name="Takamatsu & Kotohira Electric Railway", short_name="KO",
                           tokens_available=2, token_costs=[40, 100]),
    PublicCompany.initiate(id="TR", name="Tosa Electric Railway", short_name="TR",
                           tokens_available=2, token_costs=[40, 100]),
    PublicCompany.initiate(id="KU", name="Tosa Kuroshio Railway", short_name="KU",
                           tokens_available=3, token_costs=[40, 100, 100]),
    PublicCompany.initiate(id="UW", name="Uwajima Railway", short_name="UW",
                           tokens_available=2, token_costs=[40, 100]),
]

TOKEN_COUNTS = {
    "AR": 2,
    "IR": 3,
    "SR": 3,
    "KO": 2,
    "TR": 2,
    "KU": 3,
    "UW": 2,
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.GREEN: 0,
    Color.BROWN: 100,
    Color.RED: 200,
}

SPECIAL_HEX_RULES = {
    "C6": "Matsuyama - IR home hex",
    "D4": "Takamatsu - KO home hex",
    "D5": "Kotohira",
    "E8": "Tokushima - AR home hex",
    "B7": "Uwajima - UW home hex",
    "E6": "Kochi - TR/KU home hex",
}

# 1889 stock market: 10 columns x 2 rows (simplified version)
# Prices range from ¥60 to ¥500
STOCK_MARKET_GRID: list[list[Cell]] = [
    # Top row (higher prices)
    [
        Cell(100, Band.WHITE, None),
        Cell(110, Band.WHITE, None),
        Cell(120, Band.YELLOW, None),
        Cell(135, Band.YELLOW, None),
        Cell(150, Band.YELLOW, Direction.UP_RIGHT),
        Cell(165, Band.YELLOW, Direction.UP_RIGHT),
        Cell(180, Band.YELLOW, Direction.UP_RIGHT),
        Cell(200, Band.BROWN, Direction.UP_RIGHT),
        Cell(220, Band.BROWN, Direction.UP_RIGHT),
        Cell(245, Band.BROWN, Direction.UP_RIGHT),
        Cell(270, Band.BROWN, Direction.UP_RIGHT),
        Cell(300, Band.BROWN, Direction.UP_RIGHT),
    ],
    # Bottom row (lower prices)
    [
        Cell(60, Band.WHITE, None),
        Cell(67, Band.WHITE, None),
        Cell(76, Band.WHITE, None),
        Cell(82, Band.WHITE, None),
        Cell(90, Band.WHITE, None),
        Cell(100, Band.WHITE, None),
        Cell(110, Band.WHITE, None),
        Cell(120, Band.YELLOW, None),
        Cell(135, Band.YELLOW, None),
        Cell(150, Band.YELLOW, None),
        Cell(165, Band.YELLOW, None),
        Cell(180, Band.YELLOW, None),
    ],
]

STOCK_MARKET = StockMarket(STOCK_MARKET_GRID)

# 1889 trains: 2-trains rust when 4-trains are bought
TRAINS = [
    Train("2", 80, rusts_on="4"),
    Train("3", 180, rusts_on="6"),
    Train("4", 300, rusts_on="D"),
    Train("5", 450, rusts_on=None),
    Train("6", 630, rusts_on=None),
    Train("D", 1100, rusts_on=None),  # Diesel
]

OPERATING_ROUNDS = 2

