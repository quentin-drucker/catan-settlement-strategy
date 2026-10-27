# Experiments: draft order and board layout

## Questions

1. **Draft position:** under the snake draft, does any seat (A, B, C, D) do better on average?
2. **Snake vs standard:** does the snake draft (A B C D D C B A) shrink the gap between seats
   compared with the standard draft (A B C D A B C D)?
3. **Board generation:** do boards with no 6/8 next to another 6/8 ("separated") give more
   balanced results than fully random boards?

## Setup

- 4 greedy CPUs. Each pick = the best legal spot right now (random tie-break with a seeded RNG).
  - Greedy is a simple heuristic, not equilibrium play. Results describe greedy players.
- Payoff = sum of the dice weights around a player's 2 settlements (expected production,
  not actual resources).
- 4 setups = {snake, standard} x {separated, random}.
- 100,000 games per setup, seeds 0 to 99,999.
  - Game `i` uses seed `i` in every setup.
  - Board depends only on (seed, board mode) -> snake and standard play the **same
    100,000 boards** -> the draft order is the only difference (paired comparison).
  - Separated and random boards are different boards (one mode rejects layouts the other allows).
- Reproduce everything: `python main.py experiments --games 100000 --seed 0`.
- Replay any single game: `python main.py play --seed <seed> --board <mode> --draft <draft>`.

## Measures

- **Mean payoff per seat** + 95% confidence interval (CI).
  - CI half-width = 1.96 x std / sqrt(games). At 100,000 games it's about +/- 0.006 to 0.01.
- **Fairness gap** = highest seat mean - lowest seat mean. Smaller -> seats closer on average.
- **Within-game spread** = best payoff - worst payoff in one game, averaged over all games.
  Catches imbalance inside games that averages can hide.
- **Win share** = share of games each seat wins; a k-way tie for first gives each 1/k.
- **1st / 2nd pick value** per seat -> shows *where* each seat's payoff comes from.
- **Board heatmap** = how often each vertex is taken -> which positions greedy players favour.

Caveat: the fairness gap is one measure of balance, not proof that a draft is fair in
every sense.

## Results (100,000 games per setup)

Full tables: [results/summary.md](../results/summary.md). Every 95% CI below is +/- 0.01 or
smaller, so all the differences listed are real (not noise) for greedy players.

| Setup | A | B | C | D | Fairness gap | Avg within-game spread |
|---|---|---|---|---|---|---|
| snake, separated | 20.71 | 20.55 | 20.53 | 20.52 | **0.19** | 1.48 |
| standard, separated | 22.44 | 21.14 | 19.94 | 18.80 | 3.64 | 3.64 |
| snake, random | 21.64 | 21.09 | 20.86 | 20.76 | 0.88 | 1.89 |
| standard, random | 23.43 | 21.69 | 20.26 | 18.97 | 4.46 | 4.46 |

(seat columns = mean payoff)

### 1. Draft position (snake)

![Where payoff comes from](../results/pick_values.png)

- Seats end up very close: 20.71 / 20.55 / 20.53 / 20.52 on separated boards.
- Why: snake reverses the order for the 2nd pick.
  - 1st pick: A 12.47 > B 11.75 > C 11.15 > D 10.55 (picking earlier = better spot)
  - 2nd pick: A 8.24 < B 8.80 < C 9.38 < D 9.97 (D picks twice in a row, A picks last)
- Not a perfect balance: A's 1st-pick lead over D (1.92) is a bit bigger than D's 2nd-pick
  lead over A (1.73) -> A keeps a small edge (+0.19).
- Win share still leans to A: A 34%, B 20%, C 20%, D 26% (ties split). A small average
  edge turns into noticeably more wins.

### 2. Snake vs standard

![Mean payoff by seat](../results/seat_payoffs.png)

- Standard draft: a strict ladder, A 22.44 > B 21.14 > C 19.94 > D 18.80. Gap 3.64 vs 0.19.
- Same boards, game by game: snake shrinks the best-vs-worst spread by **2.16 +/- 0.007**
  points per game (separated) and 2.57 +/- 0.008 (random).
- Standard + greedy: **A can never score below anyone**.
  - Greedy pick values never go up (good spots only disappear).
  - In A B C D A B C D, A's picks are each >= B's, B's >= C's, ... in every game.
  - -> A finishes first (alone or tied) in every game. With ties split, A's win share is 90%;
    D can never win outright.
- Key observation: with greedy players, **both drafts take the exact same 8 spots in the
  same order** (checked on 5,000 boards, and by a test). The draft order doesn't change *what* gets
  picked, only *who* gets each pick. That's why the 2nd-pick values in the two drafts are
  the same four numbers, just handed to opposite seats.

![Win share](../results/win_share.png)

### 3. Board generation (separated vs random)

![Fairness across setups](../results/fairness.png)

- Separating 6s and 8s cuts the snake fairness gap from 0.88 to 0.19 (about 4x smaller)
  and the within-game spread from 1.89 to 1.48.
- It also helps under standard (gap 4.46 -> 3.64), but standard stays far less balanced.
- Why (likely): on random boards, 6s and 8s can sit together and create one "super spot".
  A's first pick is worth 13.39 on random boards vs 12.47 on separated ones; the later
  seats' picks barely change. Separation flattens the top of the board, so going first
  matters less.
- Side effect: average payoffs are a bit lower on separated boards (fewer stacked
  high-value spots).

### Board heatmap

![Board heatmap](../results/heatmap.png)

- Coast corners (1-2 tiles) are almost never taken; inland corners (3 tiles) are.
- The most-taken spots form a ring around the centre hex (~37% of games each), rather than
  the centre hex's own corners. Worth a closer look: one possible reason is that the
  centre corners sit close together, so one settlement there blocks several others.

## Takeaways

- Snake drafting works: it cuts the seat gap from ~3.6-4.5 points to ~0.2-0.9 and turns a
  near-certain A win into a much more even split.
- It's not perfectly fair: A keeps a small, consistent edge, mostly in win share.
- Keeping 6s and 8s apart makes the snake draft much closer to even (gap 0.19).
- Limits: greedy CPUs only. Players that think ahead or block on purpose (Issue #6) could
  change the picture; the draft order would then also change *which* spots get taken.
