# Implementation Plan

Small, testable milestones in issue order. Each step ends with `python -m pytest`
passing and a commit. Nothing is pushed without the team's approval.

## Status

Each completed issue has a guide in [`docs/issues/`](issues/) explaining what was done
and the commands to test it yourself.

| Step | Issue | Status |
|---|---|---|
| 1 | #1 Board representation | **Done** – `src/board.py`, `tests/test_board.py` (24 tests passing) |
| 2 | #2 Placement rules + scoring | **Done** – `src/game.py`, `src/player.py`, `tests/test_game.py` (39 tests; 63 in total) |
| 3 | #3 Greedy CPU + draft | **Done** – `src/strategies.py`, `src/game.py`, `python main.py play` (123 tests in total) |
| 4 | #4 Simulations + fairness analysis | Not started |
| 5 | #5 Pygame interactive mode | Not started |
| 6 | #6 Blocking-aware CPU (optional) | Not started |
| – | Terminal board view (backup to the Pygame window) | **Done** – `src/text_view.py`; `play --step`, `play --human A`, `explore` |
| – | README, docs, `main.py` CLI | README written (install, usage, layout); grows with each step |

## Step 1 – Board (done)

- Axial hex coordinates; 19 hexes in reading order (IDs 0–18).
- Corners on an integer lattice, so shared corners deduplicate exactly → 54 vertices,
  72 edges. Vertex IDs 0–53 in reading order, identical on every board.
- `Hex` / `Vertex` frozen dataclasses; `Board(numbers)` builds the graph;
  `board.vertex_value(v)` = sum of adjacent tile dice weights (desert = 0).
- `generate_board(seed, mode)` with `"separated"` (default) and `"random"` (rejection sampling,
  bounded by `max_attempts`, raises `BoardGenerationError`). The board depends only on
  `(seed, mode)`.
- Measured: ~14% of random shuffles already satisfy the 6/8 separation rule, so
  separated mode needs ~7 attempts (~0.8 ms per board). Rejection sampling also gives
  every valid board equal probability, which keeps Experiment 3 unbiased.

## Step 2 – Placement rules and scoring (done)

- `Player` dataclass: `name`, `settlements`, `payoff(board)`.
- `Game` placement state: `owner` (vertex → player), `blocked` set (occupied vertices
  plus their neighbours), `is_legal(v)`, `legal_vertices()`, `place(player, v)`,
  `payoffs()`.
- `place()` raises `IllegalPlacementError` for occupied, adjacent or invalid vertices,
  says which rule was broken, and leaves the game unchanged.
- `place()` takes the player's name and does not check turn order yet; that is Step 3.

## Step 3 – Greedy CPU and draft (done)

- `draft_order(players, "snake" | "standard")` → `ABCDDCBA` / `ABCDABCD`.
- `Strategy` base class with `choose(game) -> vertex`; `GreedyStrategy(rng)` picks a
  max-value legal vertex and breaks ties with `rng.choice` over the (sorted) legal list.
- `Player.strategy` (`None` = human). `Game(board, strategies, draft)`.
- Turn tracking: `current_player`, `is_over`; `place()` rejects out-of-turn and post-game
  placements. `Move(turn, player, vertex, value)` log in `game.moves`.
- `play_turn()` asks the current CPU and validates through `place()`; `play()` runs to the
  end; `winners()` lists everyone tied for first.
- `new_game(seed, board_mode, draft, humans)`: board from `generate_board(seed, mode)`,
  greedy CPUs sharing `random.Random(seed)` for tie-breaks. Same seed ⇒ same board under
  both drafts, and an identical game on replay.
- `main.py play` prints the board, turn log and payoffs; `--step` advances with Enter;
  `--human A` lets you play a seat. Inspect in the terminal view is now `i 22`.
- Measured: ~1.4 ms per full game, so 10,000 games take about 15 s.

## Step 4 – Simulations and fairness (`src/simulation.py`, `src/analysis.py`)

- Each game comes from `new_game(seed, board_mode, draft)` (Step 3), so the same seed gives
  the **same board under both draft formats** (Experiment 2 isolation).
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

## Final deliverables (presentation)

Charts and demos to build once the simulations exist (Step 4 onward):

- **Board heatmap** (requested): the hex board coloured by how often each vertex is
  taken, overall and as the first pick. The most visual slide.
- **Mean payoff by seat A–D, snake vs standard,** side by side with error bars. The
  headline answer to the research question.
- **First vs second pick value by seat.** Explains the snake trade-off (A gets the best
  first pick but the worst second pick).
- **Fairness gap table:** snake/standard × random/separated boards.
- **Payoff spread per seat** (box plot): balanced averages can still hide luck.
- **Live demo:** human vs three greedy CPUs in the Pygame window (Step 5).
- **Optional:** blocking CPU vs greedy, payoff gain by seat (Step 6).
- **Docs:** README (install, run, reproduce), one-page background, architecture diagram.

## Decisions needing team approval

1. **Default board mode:** `separated` (decided by Emmett, PR #9).
2. **Desert placement:** random hex (like real Catan), not always the centre.
3. **Tie-break seeding:** tie-break RNG seeded from the game seed, independent of the board.
4. **Win rate with ties:** split credit (`1/k` to each of `k` tied players).
5. **Raw CSVs git-ignored**; summaries and plots committed.
6. **`src` as package name** (per the proposal's layout): imports read `from src.board import ...`.
