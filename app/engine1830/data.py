"""1830 component data. Rule numbers refer to docs/rules1830.rtf.

Token supplies below exclude the marker on the stock market (Table 2).
The six Diesels follow the uploaded edition, rather than unlimited modern supply.
"""

from .board_data import DATA as BOARD_DATA

PAR_PRICES = (67, 71, 76, 82, 90, 100)
CERT_LIMITS = {2: 28, 3: 20, 4: 16, 5: 13, 6: 11}
CORPORATIONS = {
    "PRR": ("Pennsylvania Railroad", "H12", 4),
    "NYC": ("New York Central Railroad", "E19", 4),
    "CPR": ("Canadian Pacific Railroad", "A19", 4),
    "B&O": ("Baltimore & Ohio Railroad", "I15", 3),
    "C&O": ("Chesapeake & Ohio Railroad", "F6", 3),
    "ERIE": ("Erie Railroad", "E11", 3),
    "NYNH": ("New York, New Haven & Hartford Railroad", "G19", 2),
    "B&M": ("Boston & Maine Railroad", "E23", 2),
}
PRIVATES = {
    "SV": ("Schuylkill Valley", 20, 5, ["G15"]),
    "CS": ("Champlain & St. Lawrence", 40, 10, ["B20"]),
    "DH": ("Delaware & Hudson", 70, 15, ["F16"]),
    "MH": ("Mohawk & Hudson", 110, 20, ["D18"]),
    "CA": ("Camden & Amboy", 160, 25, ["H18"]),
    "BO": ("Baltimore & Ohio", 220, 30, ["I13", "I15"]),
}
TRAIN_TYPES = {
    "2": (6, 80, 2),
    "3": (5, 180, 3),
    "4": (4, 300, 4),
    "5": (3, 450, 5),
    "6": (2, 630, 6),
    "D": (6, 1100, 999),
}
PHASES = {
    "2": (4, ["yellow"], 1),
    "3": (4, ["yellow", "green"], 2),
    "4": (3, ["yellow", "green"], 2),
    "5": (2, ["yellow", "green", "brown"], 3),
    "6": (2, ["yellow", "green", "brown"], 3),
    "D": (2, ["yellow", "green", "brown"], 3),
}
RUSTS = {"4": "2", "6": "3", "D": "4"}
# Table 6, with 28 -> 46 correcting the printed 28 -> 45 conflict
# with track preservation in section 18.1. See RULE_COVERAGE.md.
# Blank entries are deliberately not upgradeable.
UPGRADES = {
    "7": ["18", "26", "27", "28", "29"],
    "8": ["16", "19", "23", "24", "25", "28", "29"],
    "9": ["18", "19", "20", "23", "24", "26", "27"],
    "57": ["14", "15"],
    "14": ["63"],
    "15": ["63"],
    "16": ["43", "70"],
    "18": ["43"],
    "19": ["45", "46"],
    "20": ["44", "47"],
    "23": ["41", "43", "45", "47"],
    "24": ["42", "43", "46", "47"],
    "25": ["40", "45", "46"],
    "26": ["42", "44", "45"],
    "27": ["41", "44", "46"],
    "28": ["39", "43", "46", "70"],
    "29": ["39", "43", "45", "70"],
    "53": ["61"],
    "54": ["62"],
    "59": ["64", "65", "66", "67", "68"],
}
MARKET_TEXT = [
    "60y 67 71 76 82 90 100p 112 126 142 160 180 200 225 250 275 300 325 350",
    "53y 60y 66 70 76 82 90p 100 112 126 142 160 180 200 220 240 260 280 300",
    "46y 55y 60y 65 70 76 82p 90 100 111 125 140 155 170 185 200",
    "39o 48y 54y 60y 66 71 76p 82 90 100 110 120 130",
    "32o 41o 48y 55y 62 67 71p 76 82 90 100",
    "25b 34o 42o 50y 58y 65 67p 71 75 80",
    "18b 27b 36o 45o 54y 63 67 69 70",
    "10b 20b 30b 40o 50y 60y 67 68",
    "- 10b 20b 30b 40o 50y 60y",
    "- - 10b 20b 30b 40o 50y",
    "- - - 10b 20b 30b 40o",
]
MARKET = []
for row in MARKET_TEXT:
    cells = []
    for cell in row.split():
        if cell == "-":
            cells.append(None)
        else:
            suffix = cell[-1] if cell[-1].isalpha() else ""
            cells.append(
                {
                    "price": int(cell.rstrip("yobp")),
                    "zone": suffix if suffix in "yob" and suffix else "white",
                    "par": suffix == "p",
                }
            )
    MARKET.append(cells)
PAR_POSITIONS = {
    cell["price"]: [r, c]
    for r, row in enumerate(MARKET)
    for c, cell in enumerate(row)
    if cell and cell["par"]
}

TRAIN_SPECS = TRAIN_TYPES
CERT_LIMIT = CERT_LIMITS
