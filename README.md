*18xx Game Engine*

The 18xx series of board games is of great fascination to me.  

However, the parts which are interesting are the human interaction; 
the actual physical actions (computing best paths, keeping tabs on other players and their cash) don't appeal to me.

This is a quiet experiment with implementing the rules as a daemon in Python. 
With some effort, I assume different front-ends will be able to hook into the Daemon, giving us much more flexibility
when creating front ends for the game.

Tests
-----
You can run test cases which should cover the full gamut of potential game scenarios.  

Corner cases should be laid out in the /unittests/scenarios directory.  
Additional cases can be added there; there should be a .md file with a descriptive name that explains the scenario.

 

Version History:
0.1: Private Company auctions enabled