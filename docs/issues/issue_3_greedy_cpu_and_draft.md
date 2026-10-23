# Issue #3: Greedy CPU Players and Settlement Draft System

**Status: Done.** 123 tests pass in total (`tests/test_game.py` 73, `tests/test_strategies.py` 6,
`tests/test_text_view.py` 20, `tests/test_board.py` 24).

## What was done

| File | Purpose |
|---|---|
| `src/strategies.py` | `Strategy` interface and `GreedyStrategy` |
| `src/game.py` | Draft order, turn tracking, move log, `play_turn()`, `play()`, `winners()`, `new_game()` |
| `src/player.py` | `Player` gained a `strategy` field (`None` = human) |
| `src/text_view.py` | Turn-aware terminal view; `game_log()` for the printed result |
| `main.py` | New `play` command; `explore` is now turn-based |
| `tests/test_game.py`, `tests/test_strategies.py`, `tests/test_text_view.py` | Draft, CPU and view tests |

- **Draft orders.** `draft_order(players, draft)` gives the sequence of turns:
  - snake: `A B C D D C B A`
  - standard: `A B C D A B C D`

  Each player appears twice, so a game is exactly 8 placements with 2 settlements each.
- **Turns.** `game.current_player` is whose turn it is (`None` once the game is over).
  `place()` now also rejects a move by the wrong player or after the game is over. As
  before, a rejected move changes nothing.
- **Move log.** Every placement is recorded in `game.moves` as a `Move(turn, player,
  vertex, value)`.
- **Greedy CPU.** `GreedyStrategy.choose(game)` looks at every legal vertex, finds the
  highest value, and picks one of the vertices with that value at random using a seeded
  random number generator. It only *chooses*; `Game.place` still validates the choice,
  so a CPU can never make an illegal move.
- **Running a game.**
  - `game.play_turn()` asks the current CPU for its choice and places it.
  - `game.play()` repeats until the game ends.
  - `game.payoffs()` and `game.winners()` give the result. `winners()` lists every
    player tied for first.
- **Reproducible games.** `new_game(seed, board_mode, draft, humans)` builds a game with
  greedy CPUs in every seat not listed in `humans`. The board depends only on the seed and
  the board mode, so **the same seed gives the same board under snake and standard**,
  which Issue #4 needs to compare the two fairly. The CPUs share one tie-break generator
  seeded with the same seed, so the same seed always replays the identical game.
- **Board mode.** Boards default to `separated` (no 6 or 8 next to another 6 or 8), as
  set by Emmett in PR #9. Use `--board random` to allow them to touch.

## How to test it yourself

Run these from the repository root.

**Run the automated tests:**

```
python -m pytest
```

Expected: `123 passed`.

### 1. Watch a full CPU game

```
python main.py play --seed 42
```

This prints the finished board, the turn log and the result. Expected log:

```
Turn 1: Player A chooses vertex 22 (value 12)
Turn 2: Player B chooses vertex 29 (value 12)
Turn 3: Player C chooses vertex 39 (value 12)
Turn 4: Player D chooses vertex 8 (value 10)
Turn 5: Player D chooses vertex 40 (value 9)
Turn 6: Player C chooses vertex 18 (value 8)
Turn 7: Player B chooses vertex 7 (value 8)
Turn 8: Player A chooses vertex 25 (value 8)

Final payoffs:
  A: 20   (vertices 22 = 12 + 25 = 8)
  B: 20   (vertices 29 = 12 + 7 = 8)
  C: 20   (vertices 39 = 12 + 18 = 8)
  D: 19   (vertices 8 = 10 + 40 = 9)

Tie for first: players A, B, C
```

Things to notice:
- The turns go A B C D **D** C B A: D picks twice in a row.
- Each pick is the best value still legal at that moment. The values only go down
  (12, 12, 12, 10, 9, 8, 8, 8) because good spots get taken or blocked.
- Same command again -> identical game.

### 2. Same board, standard draft

```
python main.py play --seed 42 --draft standard
```

Expected result:

```
  A: 21   (vertices 22 = 12 + 40 = 9)
  B: 20   (vertices 29 = 12 + 18 = 8)
  C: 20   (vertices 39 = 12 + 7 = 8)
  D: 18   (vertices 8 = 10 + 25 = 8)

Winner: player A
```

- Same board, same first four picks.
- Standard order -> A takes the 9 on turn 5 (D got it under snake).
- Spread (best minus worst): snake 20/20/20/19 -> 1 point; standard 21 ... 18 -> 3 points.
- Only one game, so not evidence. Issue #4 repeats this over thousands of boards.

### 3. Step through a game move by move

```
python main.py play --seed 42 --step
```

- The board shows up before the first move.
- **Enter** -> next CPU move. The board redraws with the new settlement (`A22`, ...) and the
  spots it blocked (`x16`, ...).
- The panel shows whose turn it is, e.g. `Turn 5 of 8: player D (greedy CPU)`, and
  `GAME OVER` + the winner at the end.
- `q` quits.

### 4. Play a seat yourself against three CPUs

```
python main.py play --seed 42 --human A
```

Seat A is human, so the game starts on the human's turn.

- **Type a vertex number** and press Enter to place there. Try `22`, one of four spots
  worth 12, the most on this board. Type `v` first to see every spot's value.
- **Press Enter** to let each CPU move.
- An illegal choice is rejected with the reason, and nothing changes. For example, on A's
  second turn try a spot marked `x`.
- `i 22` inspects a spot, `r` restarts the same game, and `q` quits.

Use `--human AC` to play two seats, or `python main.py explore` to place every move by
hand (all four seats human).

### 5. Try the options

```
python main.py play --seed 7
python main.py play --seed 7 --board random
python main.py play
python main.py play --human E
```

- A different seed gives a different board and game.
- `--board random` allows 6s and 8s to touch.
- No `--seed` picks a random one and prints it at the top so the game can be replayed.
- `--human E` is rejected: `--human must only contain seats A, B, C, D`.

## What the tests cover

- Snake order is `ABCDDCBA` and standard is `ABCDABCD`; unknown drafts are rejected
- Turns follow the draft order; turn numbers run 1–8
- Out-of-turn placements are rejected and change nothing
- The game ends after 8 placements with exactly 2 settlements per player; any further
  placement is rejected
- `play_turn()` refuses to move for a human seat; CPUs move after the human places
- Complete CPU games on 50 seeds × both drafts × both board modes: correct order, 2
  settlements each, payoffs equal the sum of move values
- The greedy CPU always picks a legal vertex with the highest available value (100 seeds ×
  both drafts, checked before every move)
- Tie-breaking only chooses among the tied best vertices (17 and 22 on the seed-42
  random board), and actually uses both, so it is not always the lowest ID
- The same seed gives an identical game; different seeds give different games
- The same seed gives the same board under snake and standard
- `winners()` reports a single winner and ties
- The rules from Issue #2 still hold for both players and for the same player (D's
  back-to-back snake turns)
- The terminal view: Enter moves a CPU, a number places for a human, a human cannot move
  for a CPU, and the game-over messages and final log are right

Check that the tests catch real bugs: making greedy pick the *worst* spot -> 3 tests fail;
removing the turn check -> 2 tests fail.

## Not included

- Running thousands of games, CSV export, fairness statistics and charts: Issue #4.
- The Pygame window: Issue #5.
- The blocking-aware CPU: Issue #6. The `Strategy` interface is ready for it.
