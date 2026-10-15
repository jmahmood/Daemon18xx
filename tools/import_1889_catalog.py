"""Regenerate the static standard catalog from a pinned upstream lib/engine tree.

Usage: python tools/import_1889_catalog.py /path/to/18xx/lib/engine
Source revision: 46a592e40494368390c9a731978a577ac4ecb1e0 (MIT).
No upstream code is executed. Runtime games need only the generated Python data.
"""

import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
raw = (root / "game/g_1889/map.rb").read_text()
counts = {
    k: int(v)
    for k, v in re.findall(r"'([0-9]+)' => (\d+)", raw.split("LOCATION_NAMES")[0])
}
tiles = {}
config = (root / "config/tile.rb").read_text()
for color, body in re.findall(
    r"      (YELLOW|GREEN|BROWN|GRAY) = \{(.*?)\}.freeze", config, re.S
):
    for tid, code in re.findall(r"^        '([^']+)' => '([^']*)',", body, re.M):
        if tid in counts:
            tiles[tid] = {"color": color.lower(), "code": code, "count": counts[tid]}
assert len(tiles) == len(counts), counts.keys() - tiles.keys()
flat = re.sub(r"'\\\n\s*'", "", raw)
hexes = {}
hexbody = flat.split("HEXES = {")[1].split("LAYOUT")[0]
for color, body in re.findall(
    r"          (white|yellow|green|gray|red): \{(.*?)\n          \}", hexbody, re.S
):
    for words, array, code in re.findall(
        r"(?:%w\[([^]]+)\]|\[([^]]+)\]) => '([^']*)'", body
    ):
        coords = words.split() if words else re.findall("'([^']+)'", array)
        for coord in coords:
            hexes[coord] = {"code": code, "color": color}
assert len(hexes) > 50, len(hexes)
data = {
    "tiles": tiles,
    "hexes": hexes,
    "layout": "flat",
    "source_revision": "46a592e40494368390c9a731978a577ac4ecb1e0",
}
(Path(__file__).resolve().parents[1] / "app/engine1889/board_data.py").write_text(
    '"""Standard Shikoku 1889 catalog; tobymao/18xx, MIT (see UPSTREAM_LICENSE)."""\n\nDATA = '
    + repr(data)
    + "\n"
)
print(len(hexes), len(tiles), sum(counts.values()))
