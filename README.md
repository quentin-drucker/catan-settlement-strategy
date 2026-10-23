# catan-settlement-strategy

A Catan-inspired settlement placement game for studying draft-order fairness, strategic
blocking and board layout, using CPU simulations and interactive play.

**Authors:** Quentin Drucker and Emmett Manning
**Course:** COM313 Algorithmic Game Theory, Professor Christine Chung

## Overview

- Only one part of *Settlers of Catan* is modelled: placing the opening settlements.
  No roads, trading, development cards or resource types.
- Board = 19 hex tiles with Catan's number tokens. Settlements go on the 54 corners where
  tiles meet.
- Settlement value = sum of the dice weights of the tiles it touches.
  - dice weight = how many of the 36 two-dice rolls give that number
  - 6 and 8 -> 5, 2 and 12 -> 1, desert -> 0
  - e.g. tiles 8, 5, 9 -> 5 + 4 + 4 = 13
- Four players (A-D) draft two settlements each. A settlement blocks its own corner and
  every neighbouring corner -> each pick scores points *and* takes options away from later
  players.

Research questions:
- Does the **snake draft** (A B C D D C B A) balance out the advantage of picking first,
  compared with the **standard** order (A B C D A B C D)?
- Does keeping 6s and 8s apart on the board make outcomes fairer?

## Installation

Needs Python 3.10 or newer.

```
git clone https://github.com/quentin-drucker/catan-settlement-strategy.git
cd catan-settlement-strategy
python -m pip install -r requirements.txt
```

## Usage

| Command | What it does |
|---|---|
| `python main.py play --seed 42` | Four greedy CPUs play a full game -> board, turn log, payoffs |
| `python main.py play --seed 42 --draft standard` | Same board, standard draft order |
| `python main.py play --seed 42 --step` | Board shown after every move; Enter = next move |
| `python main.py play --seed 42 --human A` | Play seat A against three CPUs in the terminal |
| `python main.py explore --seed 42` | Every settlement placed by hand (all seats human) |

Options (both commands):
- `--seed N`: same seed -> same board and same game. Left out -> random seed, printed at the top.
- `--board separated|random`: `separated` (default) = no 6 or 8 next to another 6 or 8.
- `--draft snake|standard`: `snake` is the default.

Terminal view commands:
- `22` -> place on vertex 22 (on a human's turn)
- Enter -> let the current CPU move
- `i 22` -> inspect vertex 22 (tiles, value, neighbours)
- `v` -> switch labels between vertex IDs and vertex values
- `r` -> restart the same game
- `q` -> quit

Still to come: batch simulations + fairness charts (Issue #4) and a Pygame window (Issue #5).

## Tests

```
python -m pytest
```

## Repository layout

```
main.py              command-line entry point
src/board.py         hex board, vertex graph, dice weights, board generation
src/game.py          game controller: draft order, turns, placement rules, payoffs
src/player.py        player + their settlements
src/strategies.py    CPU strategies (greedy)
src/text_view.py     terminal board view
tests/               pytest suite
docs/                implementation plan + per-issue testing guides
results/             simulation output (Issue #4)
```

More detail:
- [docs/implementation_plan.md](docs/implementation_plan.md): roadmap, status, open decisions
- [docs/issues/](docs/issues/): step-by-step testing guide for each finished issue
