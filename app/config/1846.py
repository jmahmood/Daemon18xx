from app.base import PrivateCompany, Train


def starting_cash(num_players: int) -> int:
    return int(3000 / num_players)


PRIVATE_COMPANIES = [
    PrivateCompany.initiate(1, "Mail Contract", "MC", 40, 5, "A1"),
    PrivateCompany.initiate(2, "Steamboat Company", "SB", 80, 10, "B2"),
    PrivateCompany.initiate(3, "Meat Packing", "MP", 120, 15, "C3"),
    PrivateCompany.initiate(4, "Lake Shore Line", "LSL", 200, 20, "D4"),
]

# Placeholder data for future rules
STOCK_MARKET = []
TRAINS = [Train("2", 100, rusts_on="4"), Train("3", 200, rusts_on="6")]
OPERATING_ROUNDS = 2

