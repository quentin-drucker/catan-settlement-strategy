# Issue #2: Settlement Placement Rules and Probability-Based Scoring

**Status: Done.** Its tests are the first section of `tests/test_game.py`.

> **Updated for Issue #3:** placements now follow the draft order (A B C D D C B A), so the
> examples below place for A, then B, then C. See `issue_3_greedy_cpu_and_draft.md`.

## What was done

| File | Purpose |
|---|---|
| `src/player.py` | `Player`: a name, the list of settlements they own, and `payoff(board)` |
| `src/game.py` | `Game`: the board plus everything placed on it; the placement rules; payoffs |
| `tests/test_game.py` | 39 automated tests |

- **Players.** A new `Game(board)` creates players A, B, C and D, each with an empty
  list of settlements.
- **Placement state.** The game keeps two structures:
  - `owner`: a dictionary from each occupied vertex to the player on it.
  - `blocked`: a set of every vertex that can no longer be chosen. It holds the
    occupied vertices plus all of their neighbours.
- **Legality.** `game.is_legal(v)` is true when `v` is a real vertex ID (0–53) and is
  not in `blocked`. `game.legal_vertices()` lists every legal vertex.
- **Placing.** `game.place(player, v)` records the settlement, blocks `v` and its
  neighbours, and returns the value of `v`.
- **Illegal moves.** `place` raises `IllegalPlacementError` and changes nothing when:
  - the vertex is already occupied;
  - the vertex is next to any settlement (the rule is the same for every player,
    including the one who owns the neighbouring settlement);
  - the value is not a vertex ID (for example `-1`, `54`, `"22"`).

  The error message says which of these happened.
- **Scoring.** A settlement's value is the sum of the dice weights of the tiles it
  touches (from Issue #1). `player.payoff(board)` adds up a player's settlements, and
  `game.payoffs()` returns the total for every player.

## See it in the terminal

```
python main.py explore --seed 42 --board random
```

All four seats are human here. Type a command and press Enter; the board redraws after
each one. The panel shows whose turn it is.

- `22` places a settlement on vertex 22 for the player whose turn it is (A first). It shows
  as `A22`, and its neighbours change to `x16`, `x17`, `x28` (blocked).
- `17` on B's turn is then rejected, with the reason shown under the board.
- `i 22` inspects a vertex; `v` switches labels between IDs and values.
- `r` restarts on the same board; `q` quits.

## How to test it yourself

Run these from the repository root.

**Run the automated tests:**

```
python -m pytest tests/test_game.py -v
```

Everything should pass. To run the whole project's tests, use `python -m pytest`.

**Place settlements and watch the state change:**

```
python -c "from src.board import generate_board; from src.game import Game; g = Game(generate_board(seed=42, mode='random')); print('legal before:', len(g.legal_vertices())); print('A places on 22, value', g.place('A', 22)); print('blocked now:', sorted(g.blocked)); print('legal after:', len(g.legal_vertices())); print('B places on 0, value', g.place('B', 0)); print('C places on 53, value', g.place('C', 53)); print('settlements:', {n: p.settlements for n, p in g.players.items()}); print('payoffs:', g.payoffs())"
```

Expected output:

```
legal before: 54
A places on 22, value 13
blocked now: [16, 17, 22, 28]
legal after: 50
B places on 0, value 3
C places on 53, value 3
settlements: {'A': [22], 'B': [0], 'C': [53], 'D': []}
payoffs: {'A': 13, 'B': 3, 'C': 3, 'D': 0}
```

Vertex 22 has neighbours 16, 17 and 28, so placing there blocks four vertices and
leaves 50 legal. Each payoff is the value of that player's one settlement so far.

**Try the three kinds of illegal move.** Each command should end with an
`IllegalPlacementError`; that error is the correct result.

Occupied vertex:

```
python -c "from src.board import generate_board; from src.game import Game; g = Game(generate_board(seed=42, mode='random')); g.place('A', 22); g.place('B', 22)"
```

Ends with: `IllegalPlacementError: vertex 22 is already occupied by player A`

Vertex next to a settlement:

```
python -c "from src.board import generate_board; from src.game import Game; g = Game(generate_board(seed=42, mode='random')); g.place('A', 22); g.place('B', 17)"
```

Ends with: `IllegalPlacementError: vertex 17 is adjacent to player A's settlement on vertex 22`

Not a vertex:

```
python -c "from src.board import generate_board; from src.game import Game; g = Game(generate_board(seed=42, mode='random')); g.place('A', 99)"
```

Ends with: `IllegalPlacementError: 99 is not a vertex ID (0-53)`

## What the tests cover

- A new game has players A–D, all 54 vertices legal, and every payoff at 0
- Placing blocks that vertex and all of its neighbours, and nothing else (checked on
  a coast corner, an interior vertex and the last vertex ID)
- `place` returns the vertex value and records the settlement for the right player
- A settlement cannot be placed twice, by the same player or a different one
- Every neighbour of a settlement is rejected, for the owner and for other players
- A vertex two steps away from a settlement is still legal
- Invalid IDs (`-1`, `54`, `1000`, `"22"`, `22.0`, `None`) are rejected
- An unknown player name is rejected
- A rejected placement leaves the game completely unchanged
- Payoffs equal the sum of settlement values, including a hand-built board where the
  expected numbers were worked out by hand (10 + 12 + 6 → 9, and 11 + desert + 3 → 4)
- On 20 boards × both draft orders, random legal games are played to the end; no two
  settlements are ever adjacent and every settlement has exactly one owner

## Not included

Turn order, the eight-placement limit and CPU players were added in Issue #3.
