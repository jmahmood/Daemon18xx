Operating Round
---------------

During an operating round each public company may lay or upgrade a single track tile.
The cost of laying track depends on the tile colour and is defined by the active
configuration module via `TRACK_LAYING_COSTS`.

Track must be upgraded one step at a time following the colour progression
(Yellow → Brown → Red → Gray). A company may not skip directly from a yellow
 tile to a red tile, for example. The appropriate cost is deducted from the
company's cash whenever a tile is placed.
