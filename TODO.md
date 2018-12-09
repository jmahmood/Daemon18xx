Questions while building.

1. What is the cleanest way to make sure that the player order is properly modified during the private company bidding phase?

2. Should I use a factory method to transform Moves into specific subclasses, or does it not really matter?
    > Is this something I can do creatively with a static function?
    
3. There may need to be a state transitions for different types of turn orders.

    > Regular (Go in a circle)

    > Bidding turn (Go to people who already bid on a private company)

    > Offering turn (Go to all other players and get an offer for a player who wants to sell a private company)
        > Allow the originating player to reject them / ?
    


 4. How to handle Albany & Eerie
    - From BGG:
    > Two others (NYC and Erie) do not have pre-existing track and a tile must be placed in the starting hex according to the rules for tile placement. NYC starts in Albany and needs an appropriate yellow tile to be placed to get you started and in that case you transfer the station marker to the top of the tile you've built. In the case of the Erie you need to place an "OO" tile in the hex to get started and the station marker goes in the circle you choose (either Dunkirk or Buffalo). The thing there is that the earliest OO tile is green so you have to wait until the greens become available (and is the one of the reasons the Erie never floats early). But even so, if the Erie floats before the greens are available, the marker is just placed in the hex anywhere as its final location does not need to be specified until the green tile is able to be built. No-one else is able to place a tile or a station marker in the Erie hex until after President of the Erie has started the line. The NYC and Erie station markers can be placed in their hexes as soon as they float but will actually end up on top of the tile that gets placed in their respective hexes, and most players just keep the base station on the Company card until the tile goes down. 
 