# Simulation results

- 100,000 games per setup, seeds 0 to 99999 (same seeds -> same boards in every setup with the same board mode)
- Four greedy CPUs (A-D). Payoff = sum of the dice weights around a player's 2 settlements.
- +/- = 95% confidence interval of the mean.
- Regenerate: `python main.py experiments --games 100000 --seed 0`

## Overview

| Setup | Fairness gap (max - min seat mean) | Avg within-game spread (best - worst) |
|---|---|---|
| snake draft, separated boards | 0.187 | 1.477 |
| standard draft, separated boards | 3.640 | 3.640 |
| snake draft, random boards | 0.881 | 1.889 |
| standard draft, random boards | 4.455 | 4.455 |

## Paired comparisons (same boards)

- separated boards: spread(snake) - spread(standard) = -2.164 +/- 0.007 points per game
- random boards: spread(snake) - spread(standard) = -2.566 +/- 0.008 points per game

## snake draft, separated boards

| Seat | Mean payoff | Std | 1st pick value | 2nd pick value | Win share |
|---|---|---|---|---|---|
| A | 20.710 +/- 0.005 | 0.86 | 12.47 | 8.24 | 33.9% |
| B | 20.548 +/- 0.006 | 0.89 | 11.75 | 8.80 | 20.2% |
| C | 20.530 +/- 0.006 | 0.98 | 11.15 | 9.38 | 19.8% |
| D | 20.523 +/- 0.007 | 1.14 | 10.55 | 9.97 | 26.0% |

## standard draft, separated boards

| Seat | Mean payoff | Std | 1st pick value | 2nd pick value | Win share |
|---|---|---|---|---|---|
| A | 22.437 +/- 0.006 | 0.91 | 12.47 | 9.97 | 90.1% |
| B | 21.136 +/- 0.006 | 0.93 | 11.75 | 9.38 | 9.2% |
| C | 19.942 +/- 0.006 | 0.93 | 11.15 | 8.80 | 0.6% |
| D | 18.796 +/- 0.006 | 0.92 | 10.55 | 8.24 | 0.0% |

## snake draft, random boards

| Seat | Mean payoff | Std | 1st pick value | 2nd pick value | Win share |
|---|---|---|---|---|---|
| A | 21.640 +/- 0.007 | 1.13 | 13.39 | 8.25 | 49.3% |
| B | 21.092 +/- 0.007 | 1.06 | 12.28 | 8.82 | 18.8% |
| C | 20.857 +/- 0.007 | 1.09 | 11.45 | 9.41 | 14.0% |
| D | 20.759 +/- 0.008 | 1.26 | 10.72 | 10.04 | 18.0% |

## standard draft, random boards

| Seat | Mean payoff | Std | 1st pick value | 2nd pick value | Win share |
|---|---|---|---|---|---|
| A | 23.428 +/- 0.007 | 1.16 | 13.39 | 10.04 | 93.4% |
| B | 21.686 +/- 0.007 | 1.09 | 12.28 | 9.41 | 6.3% |
| C | 20.264 +/- 0.006 | 1.04 | 11.45 | 8.82 | 0.3% |
| D | 18.972 +/- 0.006 | 1.02 | 10.72 | 8.25 | 0.0% |
