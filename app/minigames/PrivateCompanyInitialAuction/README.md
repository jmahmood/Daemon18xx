Private Company Initial Auction
-------------------------------

> The main interest of the owner is to sell the privates ... to the companies as fast and expensive as possible. 
> [*Martin Mathes*](https://boardgamegeek.com/article/16414653#16414653) 

Before beginning the game itself, you must auction off private companies.

Technical Explanation
----

The game has been initialized with a list of players, and a list of private companies that are loaded from the data
in the `/app/data` directory.

The `Game` class is set to `BuyPrivateCompany`.

BuyPrivateCompany
-----

This class goes "Clockwise" through the player list, allowing them to either `BUY`, `BID` or `PASS`.
 
`BUY`
When a player buys a company, the face value is immediately deducted from the player's cash reserves.

The system then goes through a list of all outstanding Private Companies (ordered by the "order" attribute).

If there is a company available and it has no bids, the next player will have an opportunity to `BUY` / `BID` / `PASS`

If there is a company available, but it has a bid on it, that company will be awarded to the player with the bid, 
and the cycle continues.

If there is a company available, and it has multiple bids, we transition into the `BiddingForPrivateCompany` minigame

`BID`
If the player chooses to `BID`, they can choose any company that has not been purchased and is not the "current" company
to place a bid on.

`PASS`
If the player chooses to `PASS`, the turn shifts to the next player.  If all the players choose to pass or bid rather than bid on a company, the current company
for sale has its price reduced by 5$.

BiddingForPrivateCompany
-------

This is an "interrupt" that occurs when 2 or more players have bid for the company that was supposed to be available for sale.
 
In this case, they can continue to `BID` or `PASS` until all parties have passed.  At that point, the person with the highest bid is awarded the private company.

There is a special turn order that is enforced for as long as `BiddingForPrivateCompany` continues. That turn order is 
removed once we transition to another minigame, or a `BiddingForPrivateCompany` for a different Private Company.

Transition to First Stock Round
-------
 
If no Private Companies are available for sale or bid, the `StockRound` begins.
  
Unit Tests
----------
`/unittests/PrivateCompanyMinigameTests.py` and `BiddingForPrivateCompanyMinigameTests.py` go through basic functionality tests
`/unittests/scenarios/SimulateFullPrivateCompanyRound` goes through a full round using the game object and covers tests related to player order.  