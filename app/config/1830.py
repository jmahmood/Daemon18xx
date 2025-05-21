from app.base import PrivateCompany, Train


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

# Placeholder data for future rules
STOCK_MARKET = []
TRAINS = [Train("2", 80, rusts_on="4"), Train("3", 180, rusts_on="5")]
OPERATING_ROUNDS = 2

