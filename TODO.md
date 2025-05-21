Questions while building.

1. What is the cleanest way to make sure that the player order is properly modified during the private company bidding phase?

2. Should I use a factory method to transform Moves into specific subclasses, or does it not really matter?
    > Is this something I can do creatively with a static function?
    
3. There may need to be a state transitions for different types of turn orders.

    > Regular (Go in a circle)

    > Bidding turn (Go to people who already bid on a private company)

    > Offering turn (Go to all other players and get an offer for a player who wants to sell a private company)
        > Allow the originating player to reject them / ?
    
 

# Rearchitecting Daemon18XX

## Split into multiple programs

1. Determine if a move (event) is valid and add it to a list of moves (events) that have been made
2. Generate the current state given a set of events
3. Alert people listening if there is a new state for a game available.
4. Alert people if they need to do something.

## Things that went wrong

- The correct move is hard because you can break out into an auction at any time.
- I shouldn't have been passing in JSON values
- I don't think actually saving the state should have mattered.  Saving the different events and generating the state each time probably makes mor esnse
- Dynamically calling different minigames looks cool but makes things confusing too.  It might make sense to make different mini apps that return bits and pieces for each request?

## Things that went right

- Actually calculating the state seems to work correctly, as does the connectivity graph and the 





# Can we split out the game state calculations and the move validations / "next move" messaging and salvage what we have?

