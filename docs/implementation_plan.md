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
| 4 | #4 Simulations + fairness analysis | **Done** – `src/simulation.py`, `src/analysis.py`, `python main.py experiments` (132 tests in total) |
| 5 | #5 Interactive website (GitHub Pages): play + watch games in the browser | **In progress** – step 1 done: Dashboard, Results, About, deploy workflow (replaces the Pygame plan) |
| 6 | #6 Blocking-aware CPU (optional) | Not started |
| – | Terminal board view (backup to the website) | **Done** – `src/text_view.py`; `play --step`, `play --human A`, `explore` |
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
  `--human A` = a person plays seat A. Inspect in the terminal view is now `i 22`.
- Measured: ~1.4 ms per full game, so 10,000 games take about 15 s.

## Step 4 – Simulations and fairness (done)

- Each game comes from `new_game(seed, board_mode, draft)` (Step 3), so the same seed gives
  the **same board under both draft formats** (Experiment 2 isolation).
- `simulate(n, base_seed, ...)`: game *i* uses seed `base_seed + i`, so any row can be
  replayed with `main.py play --seed`.
- CSV, one row per (game, player): `sim_id, seed, board_mode, draft, player, strategy,
  settlement_1, value_1, settlement_2, value_2, payoff, win_share` (ties split 1/k).
- CSV rows are streamed to disk as games finish -> 100,000+ games don't need to fit in memory.
- `summarize(csv)` re-reads a CSV: mean ± 95% CI per seat, std, 1st/2nd pick value, win share,
  fairness gap (max mean − min mean), mean within-game spread (max − min payoff), vertex
  pick counts. `paired_spread_difference` compares snake vs standard game-by-game on the same seeds.
- `run_experiments(n, seed, out)`: 4 setups (snake/standard × separated/random), then
  `results/summary.md` + 5 charts: `seat_payoffs`, `pick_values`, `fairness`, `win_share`,
  `heatmap`. Raw CSVs go to `results/raw/` (git-ignored).
- Final run: 100,000 games per setup (seeds 0–99,999). Design + findings in `docs/experiments.md`.
- Box plot of payoff spread dropped: payoffs are whole numbers, so the boxes collapse;
  replaced by win share per seat.

## Step 5 – Project website on GitHub Pages (replaces the Pygame window)

Final presentation = one website with a main dashboard; each card opens a page.

Pages:
- **Dashboard** (`index.html`): one-line summary, headline numbers, cards linking to the pages below.
- **Play**: click spots on a drawn board against 3 greedy CPUs. Legal / blocked / taken
  spots shown; hover = spot value; options for seed, draft, board mode, which seat to play.
- **Watch**: CPU game step by step (Next / Autoplay). Snake and standard side by side on the
  same board -> shows "same spots, different owners".
- **Results**: the 100,000-game findings: headline table, the 5 charts, short explanations
  (content from `docs/experiments.md` and `results/summary.md`).
- **About**: background on the topic (course needs >= 1 page), rules, scoring, method, limits.
- **Strategies** (only if Issue #6 is done): blocking CPU vs greedy. No card until it exists.

How the game runs in the browser:
- **Pyodide** (Python compiled to WebAssembly) runs the existing `src/board.py`,
  `player.py`, `strategies.py`, `game.py` unchanged; they only use the standard library.
  - Same seed -> same board and same game as the CLI and the CSVs.
  - One tested rule set; no JavaScript copy of the game logic to keep in sync.
  - Cost: ~5-10 MB download, a few seconds to load once (shown with a loading message).
- JavaScript only draws the board (SVG) and handles clicks/buttons, calling the Python `Game` API.
- Results page is static: charts from `results/*.png`, numbers from `results/summary.md`.

Hosting:
- Website files in `site/`. A GitHub Actions workflow publishes `site/` + `src/` + `results/`
  to GitHub Pages on every push to `main`.
- One-time setup: repo Settings -> Pages -> Source: "GitHub Actions". The repo is public,
  so Pages is free.

Build order (each step leaves a working site):
1. Dashboard + Results + About (static) + deploy workflow -> site live with the findings. **Done.**
   - `site/css/styles.css` = all styling; design values as CSS variables at the top.
   - Style: **"Board-game box"** (chosen from 4 options): warm grey card stock, warm dark ink,
     wheat-gold tokens, Zilla Slab headings + Archivo text. Charts use the same colours and font.
   - Fonts in `site/fonts/` (Zilla Slab, Archivo; open licence).
   - `site/build_site.py` assembles `_site/` (pages + charts) for the workflow and local preview.
   - Board drawing component (`.board`) already in styles.css for steps 2-3.
   - The other 3 style options stay only in the local, git-ignored `theme-previews/` folder.
2. Watch page (Pyodide + SVG board).
3. Play page (same board drawing + clicks).
4. Strategies page if Issue #6 happens.

Checks: Python tests still cover all game logic; each page opened in a browser and checked
by hand (board draws, clicks, no console errors) before merging.

## Step 6 – Blocking-aware CPU (optional, only after 1–5)

- `score(v) = value(v) + λ · blocking(v)`, where `blocking(v)` = drop in the **best
  value still available to the next opponent** caused by placing `v` (not the sum of
  every blocked vertex, which would over-count options nobody would take).
- Compare against greedy in each seat on identical seeds.
- If done: gets its own "Strategies" page on the website (Step 5).

## Final deliverables (presentation)

Charts and demos to build once the simulations exist (Step 4 onward):

- **Board heatmap** (requested): the hex board coloured by how often each vertex is
  taken, overall and as the first pick. The most visual slide.
- **Mean payoff by seat A–D, snake vs standard,** side by side with error bars. The
  headline answer to the research question.
- **First vs second pick value by seat.** Explains the snake trade-off (A gets the best
  first pick but the worst second pick).
- **Fairness gap table:** snake/standard × random/separated boards.
- **Win share per seat** (replaced the box plot): balanced averages can still hide who actually wins.
- **Website** (Step 5): dashboard -> Play / Watch / Results / About, hosted on GitHub Pages.
  The charts above live on the Results page.
- **Optional:** blocking CPU vs greedy, payoff gain by seat (Step 6).
- **Docs:** README (install, run, reproduce, website link), one-page background (also the
  website's About page), architecture diagram.

## Decisions needing team approval

1. **Default board mode:** `separated` (set in PR #9).
2. **Desert placement:** random hex (like real Catan), not always the centre.
3. **Tie-break seeding:** tie-break RNG seeded from the game seed, independent of the board.
4. **Win rate with ties:** split credit (`1/k` to each of `k` tied players).
5. **Raw CSVs git-ignored**; summaries and plots committed.
6. **`src` as package name** (per the proposal's layout): imports read `from src.board import ...`.
