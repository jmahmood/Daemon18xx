*18xx Game Engine*

The 18xx series of board games is of great fascination to me.  

However, the parts which are interesting are the human interaction; 
the actual physical actions (computing best paths, keeping tabs on other players and their cash) don't appeal to me.

This is a quiet experiment with implementing the rules as a daemon in Python. 
With some effort, I assume different front-ends will be able to hook into the Daemon, giving us much more flexibility
when creating front ends for the game.

## Token Availability

Public companies now track how many station tokens they have left using a
`tokens_available` counter. Each token can also have a different cost as defined
in the company configuration. When a token is purchased during an operating
round its cost is deducted from the company's cash and the available count is
reduced.
