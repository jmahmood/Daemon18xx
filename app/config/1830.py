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
    return int(2400 / num_players)


PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Schuylkill Valley Railroad & Navigation Company", "SVR", 20, 5, "G15"),
    PrivateCompany.initiate(2, "Champlain & St.Lawrence Railway", "C&StL", 40, 10, "B20"),
    PrivateCompany.initiate(3, "Delaware & Hudson Railroad", "D&H", 70, 15, "F16"),
    PrivateCompany.initiate(4, "Mohawk & Hudson Railroad", "M&H", 110, 20, "D18"),
    PrivateCompany.initiate(5, "Camden & Amboy Railroad", "C&A", 160, 25, "H18"),
    PrivateCompany.initiate(6, "Baltimore & Ohio Railroad", "B&O", 220, 30, "I13/I15"),
]

TOKEN_COUNTS = {
    "B&O": 4,
    "C&O": 3,
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.GREEN: 0,
    Color.BROWN: 100,
    Color.RED: 200,
}

SPECIAL_HEX_RULES = {
    "G15": "SVR base hex",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="B&O", name="Baltimore & Ohio Railroad", short_name="B&O",
                           tokens_available=4, token_costs=[40, 60, 80, 100]),
    PublicCompany.initiate(id="C&O", name="Chesapeake & Ohio Railway", short_name="C&O",
                           tokens_available=4, token_costs=[40, 60, 80, 100]),
]

# Simplified 12x5 stock market grid with a few coloured cells
STOCK_MARKET_GRID: list[list[Cell]] = []
for r in range(5):
    row = []
    for c in range(12):
        band = Band.WHITE
        arrow = None
        if (r, c) == (2, 2):
            band = Band.YELLOW
        if (r, c) == (1, 1):
            band = Band.BROWN
            arrow = Direction.UP_RIGHT
        row.append(Cell(10 * (c + 1), band, arrow))
    STOCK_MARKET_GRID.append(row)

STOCK_MARKET = StockMarket(STOCK_MARKET_GRID)
TRAINS = [Train("2", 80, rusts_on="4"), Train("3", 180, rusts_on="5")]
OPERATING_ROUNDS = 2

