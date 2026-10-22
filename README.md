# catan-settlement-strategy

A Catan-inspired settlement placement game exploring strategic decision-making, draft
order fairness, and board layout through CPU simulations and interactive gameplay.

**Authors:** Quentin Drucker and Emmett Manning
**Course:** COM313 Algorithmic Game Theory, Professor Christine Chung

## Overview

We isolate one part of *Settlers of Catan*: placing the opening settlements. There are no
roads, trading, development cards or resource types. The board has 19 hex tiles numbered
like Catan's dice tokens, and settlements go on the 54 corners where tiles meet. A
settlement's value is the sum of the dice weights of the tiles it touches (how many of the
36 two-dice rolls produce each number: 6 and 8 are worth 5, 2 and 12 are worth 1, the desert
is 0).

Four players draft two settlements each. A settlement blocks its own corner and every
neighbouring corner, so each pick both scores points and takes options away from later
players. Our main question: **does the snake draft (A B C D D C B A) balance out the
advantage of picking first**, compared with the standard order (A B C D A B C D)? We also
test whether keeping 6s and 8s apart on the board makes outcomes fairer.

## Installation

Requires Python 3.10 or newer.

```
git clone https://github.com/quentin-drucker/catan-settlement-strategy.git
cd catan-settlement-strategy
python -m pip install -r requirements.txt
```

## Usage

| Command | What it does |
|---|---|
| `python main.py play --seed 42` | Four greedy CPUs play a full game; prints the board, turn log and payoffs |
| `python main.py play --seed 42 --draft standard` | Same board, standard draft order |
| `python main.py play --seed 42 --step` | Shows the board after every move; press Enter to advance |
| `python main.py play --seed 42 --human A` | You play seat A against three CPUs in the terminal |
| `python main.py explore --seed 42` | Place every settlement by hand (all seats human) |

Options for both commands:
- `--seed N`: the same seed always gives the same board and game. If you leave it out, a
  random seed is used and printed.
- `--board separated|random`: the default, `separated`, never puts a 6 or 8 next to
  another 6 or 8.
- `--draft snake|standard`: the default is `snake`.

In the terminal view, `22` places on vertex 22 on your turn, Enter lets a CPU move,
`i 22` inspects a vertex, `v` switches the labels between vertex IDs and values, `r`
restarts, and `q` quits.

Coming next: batch simulations with fairness charts (Issue #4) and a Pygame window (Issue #5).

## Tests

```
python -m pytest
```

## Repository layout

```
main.py              command-line entry point
src/board.py         hex board, vertex graph, dice weights, board generation
src/game.py          game controller: draft order, turns, placement rules, payoffs
src/player.py        player and their settlements
src/strategies.py    CPU strategies (greedy)
src/text_view.py     terminal board view
tests/               pytest suite
docs/                implementation plan and per-issue testing guides
results/             simulation output (Issue #4)
```

See [docs/implementation_plan.md](docs/implementation_plan.md) for the roadmap and
[docs/issues/](docs/issues/) for step-by-step guides to each completed issue.
