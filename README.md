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
* `SPECIAL_HEX_RULES` – a dictionary mapping hex identifiers to rule
  dictionaries or messages. Rules can specify `no_lay`, `no_upgrade` or
  `allowed_colors` to fine tune what track placements are allowed.

## Token Availability

Public companies now track how many station tokens they have left using a
`tokens_available` counter. Each token can also have a different cost as defined
in the company configuration. When a token is purchased during an operating
round its cost is deducted from the company's cash and the available count is
reduced.
The total number of tokens a company begins with is stored in the
`token_count` attribute. At the start of a game `tokens_available` will equal
`token_count`. Purchasing station tokens decreases `tokens_available` but does
not change `token_count`. Each company also tracks whether it has already placed
a station token in the current operating round and the engine enforces the rule
that at most one token may be placed per round.

## Dividend Payouts

Operating round moves must explicitly state whether dividends will be paid with
the `pay_dividend` flag. This value must be `True` or `False` and a company can
only choose once it has calculated income by running routes. When creating an
`OperatingRoundMove` the flag defaults to `False` so tests and simple
integrations may omit it. When dividends are distributed that income is removed
from the company and credited directly to the players according to their share
percentage.

## Changelog

* Recent updates include initial handling of bankrupt companies when trains rust.
Public companies now track placed station tokens and expose a ``hasValidRoute``
helper used during operating rounds to determine whether a company can continue
operating once its trains are gone.
Token placement is now limited to one per operating round and the flag resets at
the start of each round.
Track placement now checks each variant's `SPECIAL_HEX_RULES`. Hex rules can
forbid initial placement (`no_lay`), upgrades (`no_upgrade`) or limit allowed
tile colours. Moves violating these restrictions are rejected.

* Routes are now checked against the capacity of the trains assigned to a company.
Each list of stops must form a continuous path across existing track tiles and
cannot exceed the length of any available train. Invalid routes are rejected
during the operating round.

* The presidency of a public company transfers only to the largest shareholder
  who holds at least 20% of its stock.
* Certificate limits now follow the 1830 rules. The maximum number of
  certificates depends on player count and includes both private and public
  holdings.
