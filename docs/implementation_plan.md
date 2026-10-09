# Implementation Plan

Small, testable milestones in issue order. Each step ends with `python -m pytest`
passing and a commit. Nothing is pushed without the team's approval.

## Status

Each completed issue has a guide in [`docs/issues/`](issues/) explaining what was done
and the commands to test it yourself.

| Step | Issue | Status |
|---|---|---|
| 1 | #1 Board representation | **Done** – `src/board.py`, `tests/test_board.py` (24 tests passing) |
| 2 | #2 Placement rules + scoring | Not started |
| 3 | #3 Greedy CPU + draft | Not started |
| 4 | #4 Simulations + fairness analysis | Not started |
| 5 | #5 Pygame interactive mode | Not started |
| 6 | #6 Blocking-aware CPU (optional) | Not started |
| – | README, docs, `main.py` CLI | Grows with each step |

## Step 1 – Board (done)

- Axial hex coordinates; 19 hexes in reading order (IDs 0–18).
- Corners on an integer lattice, so shared corners deduplicate exactly → 54 vertices,
  72 edges. Vertex IDs 0–53 in reading order, identical on every board.
- `Hex` / `Vertex` frozen dataclasses; `Board(numbers)` builds the graph;
  `board.vertex_value(v)` = sum of adjacent tile dice weights (desert = 0).
- `generate_board(seed, mode)` with `"random"` and `"separated"` (rejection sampling,
  bounded by `max_attempts`, raises `BoardGenerationError`). The board depends only on
  `(seed, mode)`.
- Measured: ~14% of random shuffles already satisfy the 6/8 separation rule, so
  separated mode needs ~7 attempts (~0.8 ms per board). Rejection sampling also gives
  every valid board equal probability, which keeps Experiment 3 unbiased.

## Step 2 – Placement rules and scoring (`src/game.py`, `src/player.py`)

- `Player` dataclass: `name`, `strategy` (`None` = human), `settlements`, `payoff(board)`.
- `Game` placement state: `owner` (vertex → player), `blocked` set (occupied vertices
  plus their neighbours), `is_legal(v)`, `legal_vertices()`, `place(v)`.
- `place()` raises `IllegalPlacementError` for occupied, adjacent, out-of-range, or
  post-game placements. It never accepts an illegal placement without raising.
- Tests: blocking of vertex + neighbours, rejection of each illegal case, payoff sums.

## Step 3 – Greedy CPU and draft (`src/strategies.py`, `src/game.py`)

- `draft_order(players, "snake" | "standard")` → `ABCDDCBA` / `ABCDABCD`.
- `Strategy` base class with `choose(game) -> vertex`; `GreedyStrategy(rng)` picks a
  max-value legal vertex and breaks ties with `rng.choice` over sorted candidates.
- `Game.play_turn()` asks the current player's strategy, then validates through `place()`.
  `Game.play()` runs to completion. `Move` records (turn, player, vertex, value).
- `main.py play --seed N --draft snake --board random` prints the turn log + payoffs.
- Tests: 8 placements, 2 settlements each, CPUs never illegal, same seed ⇒ same game.

## Step 4 – Simulations and fairness (`src/simulation.py`, `src/analysis.py`)

- `run_game(seed, board_mode, draft)`: board from `generate_board(seed, mode)`, and
  tie-breaks from a separate `random.Random(seed)`. The same seed therefore gives the
  **same board under both draft formats** (Experiment 2 isolation).
- `simulate(n, base_seed, ...)`: game *i* uses seed `base_seed + i`, so any row can be
  replayed with `main.py play --seed`.
- CSV, one row per (game, player): `sim_id, seed, board_mode, draft, player, strategy,
  settlement_1, value_1, settlement_2, value_2, payoff, win_share` (ties split 1/k).
- Summary per configuration: mean ± 95% CI by position, per-position std, fairness gap
  (max mean − min mean), mean within-game spread (max − min payoff), win share.
- Experiments (one command, fixed base seed): 1) snake/random by position;
  2) snake vs standard on identical seeds; 3) random vs separated boards under snake.
  Output: `results/summary.md` + one labelled Matplotlib PNG per experiment; raw CSVs go
  to `results/raw/` (git-ignored).

## Step 5 – Pygame interactive mode (`src/visualization.py`)

- Only reads/writes through the `Game` API; the simulation never imports Pygame.
- Draw hexes and tokens; vertices shown as legal / blocked / occupied (player colour).
  Hover shows a vertex's value. Click a legal vertex on the human's turn. CPU turns
  advance with a short delay. Side panel shows the turn, the current player and scores.
  `R` = new board, `Esc` = quit.
- Test headlessly (`SDL_VIDEODRIVER=dummy`): pixel→vertex hit-testing and a scripted game.

## Step 6 – Blocking-aware CPU (optional, only after 1–5)

- `score(v) = value(v) + λ · blocking(v)`, where `blocking(v)` = drop in the **best
  value still available to the next opponent** caused by placing `v` (not the sum of
  every blocked vertex, which would over-count options nobody would take).
- Compare against greedy in each seat on identical seeds.

## Decisions needing team approval

1. **Branch:** work is on local branch `core-implementation` (not pushed).
2. **Desert placement:** random hex (like real Catan), not always the centre.
3. **Tie-break seeding:** tie-break RNG seeded from the game seed, independent of the board.
4. **Win rate with ties:** split credit (`1/k` to each of `k` tied players).
5. **Raw CSVs git-ignored**; summaries and plots committed.
6. **`src` as package name** (per the proposal's layout): imports read `from src.board import ...`.
