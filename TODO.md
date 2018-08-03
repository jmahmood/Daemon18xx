Questions while building.

1. What is the cleanest way to make sure that the player order is properly modified during the private company bidding phase?

2. Should I use a factory method to transform Moves into specific subclasses, or does it not really matter?
    > Is this something I can do creatively with a static function?
    
3. There may need to be a state transitions for different types of turn orders.

    > Regular (Go in a circle)

    > Bidding turn (Go to people who already bid on a private company)

    > Offering turn (Go to all other players and get an offer for a player who wants to sell a private company)
        > Allow the originating player to reject them / ?
    


 