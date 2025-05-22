*18xx Game Engine*

The 18xx series of board games is of great fascination to me.  

However, the parts which are interesting are the human interaction; 
the actual physical actions (computing best paths, keeping tabs on other players and their cash) don't appeal to me.

This is a quiet experiment with implementing the rules as a daemon in Python. 
With some effort, I assume different front-ends will be able to hook into the Daemon, giving us much more flexibility
when creating front ends for the game.

## Configuration Modules

Each game variant under `app/config/` exposes a configuration module. In
addition to the lists of private and public companies, the modules now provide:

* `TOKEN_COUNTS` – mapping of public company IDs to their starting token supply.
  Each `PublicCompany` instance created from the module also has a
  `token_count` attribute populated from this mapping.
* `TRACK_LAYING_COSTS` – the cost in currency for laying track tiles by
  `Color`.
* `SPECIAL_HEX_RULES` – a dictionary of hex identifiers to any special rules
  that may apply when validating moves.

## Token Availability

Public companies now track how many station tokens they have left using a
`tokens_available` counter. Each token can also have a different cost as defined
in the company configuration. When a token is purchased during an operating
round its cost is deducted from the company's cash and the available count is
reduced.
The total number of tokens a company begins with is stored in the
`token_count` attribute. At the start of a game `tokens_available` will equal
`token_count`. Purchasing station tokens decreases `tokens_available` but does
not change `token_count`.

## Changelog

Recent updates include initial handling of bankrupt companies when trains rust.
Public companies now track placed station tokens and expose a ``hasValidRoute``
helper used during operating rounds to determine whether a company can continue
operating once its trains are gone.

## Running Tests

All unit tests live under `app/unittests/`. After cloning the repository run

```bash
python -m unittest discover
```

from the repository root to execute the entire test suite.

