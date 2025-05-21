from app.base import PrivateCompany, PublicCompany, Train, Color


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
    Color.BROWN: 100,
    Color.RED: 200,
}

SPECIAL_HEX_RULES = {
    "G15": "SVR base hex",
}

PUBLIC_COMPANIES = [
    PublicCompany.initiate(id="B&O", name="Baltimore & Ohio Railroad", short_name="B&O", token_count=TOKEN_COUNTS["B&O"]),
    PublicCompany.initiate(id="C&O", name="Chesapeake & Ohio Railway", short_name="C&O", token_count=TOKEN_COUNTS["C&O"]),
]

# Placeholder data for future rules
STOCK_MARKET = []
TRAINS = [Train("2", 80, rusts_on="4"), Train("3", 180, rusts_on="5")]
OPERATING_ROUNDS = 2

