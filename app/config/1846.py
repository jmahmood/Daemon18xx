from app.base import PrivateCompany, PublicCompany, Train, Color


def starting_cash(num_players: int) -> int:
    return int(3000 / num_players)


PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Mail Contract", "MC", 40, 5, "A1"),
    PrivateCompany.initiate(2, "Steamboat Company", "SB", 80, 10, "B2"),
    PrivateCompany.initiate(3, "Meat Packing", "MP", 120, 15, "C3"),
    PrivateCompany.initiate(4, "Lake Shore Line", "LSL", 200, 20, "D4"),
]

TOKEN_COUNTS = {
    "NYC": 5,
    "GT": 4,
}

TRACK_LAYING_COSTS = {
    Color.YELLOW: 0,
    Color.BROWN: 100,
    Color.RED: 200,
}

SPECIAL_HEX_RULES = {
    "A1": "Mail Contract base",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="NYC", name="New York Central", short_name="NYC", token_count=TOKEN_COUNTS["NYC"]),
    PublicCompany.initiate(id="GT", name="Grand Trunk", short_name="GT", token_count=TOKEN_COUNTS["GT"]),
]

# Placeholder data for future rules
STOCK_MARKET = []
TRAINS = [Train("2", 100, rusts_on="4"), Train("3", 200, rusts_on="6")]
OPERATING_ROUNDS = 2

