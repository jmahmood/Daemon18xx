"""
1889 Hex Map Data for Shikoku Island

This file contains the hex map layout for 1889: History of Shikoku Railways.
The map represents the island of Shikoku, Japan with its four provinces:
- Ehime (west)
- Kagawa (north)
- Tokushima (east)
- Kochi (south)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class HexData:
    """Represents a single hex on the board"""
    coord: str  # e.g., "C6"
    terrain_type: str  # "plain", "mountain", "water", "city"
    city_name: Optional[str] = None
    city_value: Optional[int] = None  # Revenue value
    city_slots: int = 1  # Number of token slots
    special: Optional[str] = None  # Special rules or notes
    connections: List[str] = None  # Neighboring hex coordinates

    def __post_init__(self):
        if self.connections is None:
            self.connections = []


# 1889 uses a simplified map focused on Shikoku's rail network
# The map is approximately 6 rows (A-F) by 9 columns (1-9)
MAP_HEXES = [
    # Row A - Northern coast
    HexData("A2", "water"),
    HexData("A3", "water"),
    HexData("A4", "water"),
    HexData("A5", "water"),

    # Row B - Northwest region (Ehime)
    HexData("B1", "plain"),
    HexData("B2", "mountain"),
    HexData("B3", "plain", connections=["A3", "B2", "B4", "C3", "C4"]),
    HexData("B4", "plain", connections=["A4", "B3", "B5", "C4", "C5"]),
    HexData("B5", "plain", connections=["A5", "B4", "B6", "C5", "C6"]),
    HexData("B6", "plain", connections=["B5", "B7", "C6", "C7"]),
    HexData("B7", "city", city_name="Uwajima", city_value=20, city_slots=1,
            special="UW home", connections=["B6", "C7"]),

    # Row C - Central northern region
    HexData("C2", "plain", connections=["B2", "C3", "D2", "D3"]),
    HexData("C3", "plain", connections=["B3", "C2", "C4", "D3", "D4"]),
    HexData("C4", "plain", connections=["B3", "B4", "C3", "C5", "D4", "D5"]),
    HexData("C5", "mountain", connections=["B4", "B5", "C4", "C6", "D5"]),
    HexData("C6", "city", city_name="Matsuyama", city_value=30, city_slots=2,
            special="IR home", connections=["B5", "B6", "C5", "C7", "D6"]),
    HexData("C7", "plain", connections=["B6", "B7", "C6", "D6", "D7"]),
    HexData("C8", "mountain"),

    # Row D - Central region (Kagawa)
    HexData("D1", "water"),
    HexData("D2", "plain", connections=["C2", "D3", "E2"]),
    HexData("D3", "plain", connections=["C2", "C3", "D2", "D4", "E3"]),
    HexData("D4", "city", city_name="Takamatsu", city_value=30, city_slots=2,
            special="KO home", connections=["C3", "C4", "D3", "D5", "E4"]),
    HexData("D5", "city", city_name="Kotohira", city_value=20, city_slots=1,
            connections=["C4", "C5", "D4", "D6", "E5"]),
    HexData("D6", "mountain", connections=["C6", "C7", "D5", "D7", "E6"]),
    HexData("D7", "plain", connections=["C7", "D6", "D8", "E7"]),
    HexData("D8", "plain", connections=["D7", "E8"]),

    # Row E - Southern central region (Tokushima/Kochi)
    HexData("E2", "plain", connections=["D2", "E3", "F2"]),
    HexData("E3", "plain", connections=["D3", "E2", "E4", "F3"]),
    HexData("E4", "plain", connections=["D4", "E3", "E5", "F4"]),
    HexData("E5", "mountain", connections=["D5", "E4", "E6", "F5"]),
    HexData("E6", "city", city_name="Kochi", city_value=30, city_slots=2,
            special="TR/KU home", connections=["D6", "E5", "E7", "F6"]),
    HexData("E7", "plain", connections=["D7", "E6", "E8", "F7"]),
    HexData("E8", "city", city_name="Tokushima", city_value=30, city_slots=2,
            special="AR home", connections=["D8", "E7", "F8"]),

    # Row F - Southern coast
    HexData("F2", "plain", connections=["E2", "F3"]),
    HexData("F3", "plain", connections=["E3", "F2", "F4"]),
    HexData("F4", "plain", connections=["E4", "F3", "F5"]),
    HexData("F5", "mountain", connections=["E5", "F4", "F6"]),
    HexData("F6", "plain", connections=["E6", "F5", "F7"]),
    HexData("F7", "plain", connections=["E7", "F6", "F8"]),
    HexData("F8", "plain", connections=["E8", "F7"]),
]


# Create a lookup dictionary for quick access
MAP_DICT = {hex_data.coord: hex_data for hex_data in MAP_HEXES}


def get_hex(coord: str) -> Optional[HexData]:
    """Get hex data by coordinate"""
    return MAP_DICT.get(coord)


def get_neighboring_hexes(coord: str) -> List[HexData]:
    """Get all neighboring hexes for a given coordinate"""
    hex_data = get_hex(coord)
    if not hex_data:
        return []
    return [MAP_DICT[neighbor] for neighbor in hex_data.connections if neighbor in MAP_DICT]


def get_cities() -> List[HexData]:
    """Get all city hexes"""
    return [hex_data for hex_data in MAP_HEXES if hex_data.terrain_type == "city"]


def get_home_hexes() -> dict[str, str]:
    """Get mapping of company IDs to their home hex coordinates"""
    home_hexes = {}
    for hex_data in MAP_HEXES:
        if hex_data.special and "home" in hex_data.special:
            # Extract company ID from special field (e.g., "IR home" -> "IR")
            company_id = hex_data.special.split()[0]
            home_hexes[company_id] = hex_data.coord
    return home_hexes


# Export map dimensions for rendering
MAP_ROWS = 6  # A through F
MAP_COLS = 9  # 1 through 9
