# Issue #4: Randomized Game Simulations and Fairness Analysis

**Status: Done.** 133 tests pass in total (10 new in `tests/test_simulation.py`).
Final run: 100,000 games per setup. Findings: [docs/experiments.md](../experiments.md).

## What was done

| File | Purpose |
|---|---|
| `src/simulation.py` | `simulate()`: play N greedy-CPU games, stream one CSV row per player per game |
| `src/analysis.py` | `summarize()` statistics, `paired_spread_difference()`, report, 5 charts, `run_experiments()` |
| `main.py` | New `experiments` command |
| `results/summary.md` | Tables for all 4 setups + comparisons (the charts' table view) |
| `results/*.png` | `seat_payoffs`, `pick_values`, `fairness`, `win_share`, `heatmap` |
| `results/raw/*.csv` | Raw data, ~22 MB per setup (git-ignored; regenerate with the command below) |
| `docs/experiments.md` | Experiment design + findings write-up |

- **Setups:** {snake, standard} draft x {separated, random} boards, 4 greedy CPUs each.
- **Seeds:** game `i` uses seed `i` -> snake and standard play the *same boards*; any game can
  be replayed with `python main.py play`.
- **Streaming:** rows go to disk as games finish, so 100,000+ games don't need to fit in memory.
- **Measures:** mean payoff per seat ± 95% CI, std, 1st/2nd pick value, win share (ties split
  1/k), fairness gap (max − min seat mean), within-game spread (best − worst), vertex pick counts.
- **Paired comparison:** snake vs standard compared game by game on the same seeds.
- **Charts** use a colour-blind-checked palette: blue = snake, orange = standard everywhere.

## Headline results (100,000 games per setup)

| Setup | Fairness gap | Avg within-game spread | Win share A / B / C / D |
|---|---|---|---|
| snake, separated | 0.19 | 1.48 | 34% / 20% / 20% / 26% |
| standard, separated | 3.64 | 3.64 | 90% / 9% / 1% / 0% |
| snake, random | 0.88 | 1.89 | 49% / 19% / 14% / 18% |
| standard, random | 4.46 | 4.46 | 93% / 6% / 0% / 0% |

- Snake cuts the seat gap massively; A keeps a small edge.
- Separated boards make snake much closer to even (0.88 -> 0.19).
- Greedy players take the same 8 spots in both drafts; the draft only decides who gets them.

## How to test it yourself

Run these from the repository root.

**1. Automated tests**

```
python -m pytest
```

Expected: `133 passed`.

**2. Quick experiment run (a few seconds)**

```
python main.py experiments --games 2000 --out results_test
```

- Prints one line per setup, then where the files went.
- Open `results_test/summary.md` and the PNGs. Numbers are close to the 100,000-game ones,
  with wider ± ranges.
- Delete the `results_test` folder afterwards (it isn't git-ignored).

**3. Full run (about 5 minutes)**

```
python main.py experiments --games 100000 --seed 0
```

- Rewrites `results/summary.md` and `results/*.png` with identical numbers (same seeds ->
  same games), plus the raw CSVs in `results/raw/`.

**4. Replay one game from the raw data**

- Open `results/raw/separated_snake.csv`, pick any row, note its `seed`, `board_mode`, `draft`.
- Example: seed 0 ->

```
python main.py play --seed 0 --board separated --draft snake
```

- The settlements and payoffs printed match the CSV rows for `sim_id` 0.

**5. See the "same spots, different owners" effect on one board**

```
python main.py play --seed 42 --draft snake
python main.py play --seed 42 --draft standard
```

- Same 8 vertices in the same order in both logs; only the player names next to turns 5-8 change.

## What the tests cover

- CSV: header, 4 rows per game in seat order, seeds counting up from the base seed
- CSV values match replaying the same seed with `new_game` (settlements, values, payoff)
- Win shares add to 1 per game and only go to players with the top payoff
- Same seed -> byte-identical CSV
- Same seeds -> same first round under both drafts; greedy takes the same 8 spots in both
  drafts (50 seeds x 2 board modes)
- `summarize()` matches a hand computation (means, std, fairness gap, pick counts, seeds)
- Standard draft: A >= B >= C >= D in every game, so spread = fairness gap
- Paired comparison: zero against itself, refuses mismatched seeds
- `run_experiments()` writes the report, all 5 charts and all 4 raw CSVs

## Notes / decisions

- **Default board for the headline charts = separated** (the project default since PR #9).
  Random boards appear in the fairness chart and the tables.
- **Box plot dropped:** payoffs are whole numbers, so the boxes collapsed into flat bars.
  Replaced by the win-share chart (win rates were optional in the proposal).
- **100,000 vs 10,000 games:** 10,000 already answers snake vs standard clearly; 100,000
  shrinks the ± ranges ~3x, which matters for the small effects (e.g. A's 0.19 edge).
