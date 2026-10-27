"""Fairness analysis: summary statistics, the markdown report, and the charts.

Reads the CSVs written by ``simulation.simulate`` (so results can always be
re-analysed from the raw data) and measures, per setup (draft x board mode):
- mean payoff per seat A-D, with a 95% confidence interval (CI)
  - CI half-width = 1.96 * std / sqrt(games) -> "true mean is very likely within +/- this"
- fairness gap = highest seat mean - lowest seat mean (smaller = seats closer on average)
- within-game spread = best payoff - worst payoff in one game, averaged over games
- win share per seat (ties split 1/k)
- mean value of each seat's first and second pick (explains *why* seats differ)
- how often each vertex gets taken (for the board heatmap)

Note: the fairness gap is one measure of balance between seats, not a proof
that a draft is "fair" in every sense, and greedy CPUs are a heuristic, not
equilibrium play.
"""

from __future__ import annotations

import csv
import math
import statistics
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw straight to image files; no window needed
import matplotlib.pyplot as plt  # noqa: E402  (must come after choosing the backend)
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

from src.board import generate_board  # noqa: E402
from src.game import PLAYER_NAMES, draft_order  # noqa: E402
from src.simulation import simulate  # noqa: E402

# The four setups compared: (draft, board mode).
SETUPS = [("snake", "separated"), ("standard", "separated"), ("snake", "random"), ("standard", "random")]

# Chart colours (validated reference palette): blue = snake, orange = standard.
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
DRAFT_COLORS = {"snake": "#2a78d6", "standard": "#eb6834"}
PICK_COLORS = ("#1baf7a", "#eda100")  # 1st pick aqua, 2nd pick yellow (not blue/orange: those mean snake/standard)
# One-hue blue ramp (light -> dark) for the heatmap.
HEAT_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


# --- Statistics ------------------------------------------------------------------


def summarize(path: str | Path) -> dict:
    """Read one simulation CSV and return its statistics as a dict (see the file docstring)."""
    payoffs = {s: [] for s in PLAYER_NAMES}  # seat -> payoff in every game
    value_1 = {s: [] for s in PLAYER_NAMES}  # seat -> first-pick value in every game
    value_2 = {s: [] for s in PLAYER_NAMES}
    wins = dict.fromkeys(PLAYER_NAMES, 0.0)
    spreads, seeds = [], []  # per game, in sim_id order
    taken, first_pick = Counter(), Counter()  # vertex ID -> number of games
    draft = board_mode = None

    with Path(path).open(newline="") as f:
        game_payoffs = []
        for row in csv.DictReader(f):
            seat, payoff = row["player"], int(row["payoff"])
            draft, board_mode = row["draft"], row["board_mode"]
            payoffs[seat].append(payoff)
            value_1[seat].append(int(row["value_1"]))
            value_2[seat].append(int(row["value_2"]))
            wins[seat] += float(row["win_share"])
            taken.update((int(row["settlement_1"]), int(row["settlement_2"])))
            if seat == PLAYER_NAMES[0]:  # seat A always makes the very first pick
                first_pick[int(row["settlement_1"])] += 1
            game_payoffs.append(payoff)
            if seat == PLAYER_NAMES[-1]:  # last row of a game -> close it off
                spreads.append(max(game_payoffs) - min(game_payoffs))
                seeds.append(int(row["seed"]))
                game_payoffs = []

    games = len(spreads)
    mean = {s: statistics.fmean(payoffs[s]) for s in PLAYER_NAMES}
    std = {s: statistics.stdev(payoffs[s]) for s in PLAYER_NAMES}
    return {
        "draft": draft,
        "board_mode": board_mode,
        "games": games,
        "mean": mean,
        "std": std,
        "ci95": {s: 1.96 * std[s] / math.sqrt(games) for s in PLAYER_NAMES},
        "mean_value_1": {s: statistics.fmean(value_1[s]) for s in PLAYER_NAMES},
        "mean_value_2": {s: statistics.fmean(value_2[s]) for s in PLAYER_NAMES},
        "win_share": {s: wins[s] / games for s in PLAYER_NAMES},
        "fairness_gap": max(mean.values()) - min(mean.values()),
        "mean_spread": statistics.fmean(spreads),
        "spreads": spreads,
        "seeds": seeds,
        "payoffs": payoffs,
        "taken": taken,
        "first_pick": first_pick,
    }


def paired_spread_difference(a: dict, b: dict) -> tuple[float, float]:
    """Mean of (spread in a - spread in b) over the same seeds, and its 95% CI half-width.

    Same seeds = same boards, so each game is compared with its own twin. Negative
    -> setup ``a`` has smaller best-vs-worst gaps.
    """
    assert a["seeds"] == b["seeds"], "paired comparison needs the same seeds in the same order"
    diffs = [x - y for x, y in zip(a["spreads"], b["spreads"])]
    return statistics.fmean(diffs), 1.96 * statistics.stdev(diffs) / math.sqrt(len(diffs))


# --- Report ------------------------------------------------------------------------


def _label(s: dict) -> str:
    return f"{s['draft']} draft, {s['board_mode']} boards"


def write_report(summaries: dict, path: str | Path, base_seed: int) -> Path:
    """Markdown summary: one table per setup + the comparisons. Doubles as the charts' table view."""
    any_s = next(iter(summaries.values()))
    lines = [
        "# Simulation results",
        "",
        f"- {any_s['games']:,} games per setup, seeds {base_seed} to {base_seed + any_s['games'] - 1}"
        " (same seeds -> same boards in every setup with the same board mode)",
        "- Four greedy CPUs (A-D). Payoff = sum of the dice weights around a player's 2 settlements.",
        "- +/- = 95% confidence interval of the mean.",
        "- Regenerate: `python main.py experiments --games "
        f"{any_s['games']} --seed {base_seed}`",
        "",
        "## Overview",
        "",
        "| Setup | Fairness gap (max - min seat mean) | Avg within-game spread (best - worst) |",
        "|---|---|---|",
    ]
    for key in SETUPS:
        s = summaries[key]
        lines.append(f"| {_label(s)} | {s['fairness_gap']:.3f} | {s['mean_spread']:.3f} |")

    lines += ["", "## Paired comparisons (same boards)", ""]
    for mode in ("separated", "random"):
        diff, ci = paired_spread_difference(summaries[("snake", mode)], summaries[("standard", mode)])
        lines.append(
            f"- {mode} boards: spread(snake) - spread(standard) = {diff:+.3f} +/- {ci:.3f} points per game"
        )

    for key in SETUPS:
        s = summaries[key]
        lines += [
            "",
            f"## {_label(s)}",
            "",
            "| Seat | Mean payoff | Std | 1st pick value | 2nd pick value | Win share |",
            "|---|---|---|---|---|---|",
        ]
        for seat in PLAYER_NAMES:
            lines.append(
                f"| {seat} | {s['mean'][seat]:.3f} +/- {s['ci95'][seat]:.3f} | {s['std'][seat]:.2f}"
                f" | {s['mean_value_1'][seat]:.2f} | {s['mean_value_2'][seat]:.2f}"
                f" | {s['win_share'][seat]:.1%} |"
            )
    path = Path(path)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --- Charts ------------------------------------------------------------------------


def _style(ax, ylabel: str | None = None) -> None:
    """Quiet chart chrome: no top/right borders, faint solid grid behind the bars."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TEXT_SECONDARY)
    ax.tick_params(colors=TEXT_SECONDARY)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_SECONDARY)


def _figure(ncols: int = 1, width: float = 8.0, height: float = 4.8):
    fig, axes = plt.subplots(1, ncols, figsize=(width, height), facecolor=SURFACE, squeeze=False)
    return fig, axes[0]


def _save(fig, path: Path, title: str, subtitle: str) -> Path:
    fig.suptitle(title, color=TEXT, fontsize=13, fontweight="bold", x=0.02, ha="left")
    fig.text(0.02, 0.905, subtitle, color=TEXT_SECONDARY, fontsize=9, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def plot_seat_payoffs(snake: dict, standard: dict, path: Path) -> Path:
    """Grouped bars: mean payoff per seat, snake vs standard, same boards. The headline chart."""
    fig, (ax,) = _figure()
    width = 0.38
    for i, s in enumerate((snake, standard)):
        xs = [k + (i - 0.5) * width for k in range(len(PLAYER_NAMES))]
        means = [s["mean"][seat] for seat in PLAYER_NAMES]
        ax.bar(xs, means, width, color=DRAFT_COLORS[s["draft"]], edgecolor=SURFACE, linewidth=2,
               label=f"{s['draft']} ({' '.join(draft_order(PLAYER_NAMES, s['draft']))})")
        ax.errorbar(xs, means, yerr=[s["ci95"][seat] for seat in PLAYER_NAMES], fmt="none",
                    ecolor=TEXT_SECONDARY, elinewidth=1, capsize=3)
        for x, m in zip(xs, means):
            ax.text(x, m + 0.25, f"{m:.2f}", ha="center", va="bottom", fontsize=8, color=TEXT_SECONDARY)
    lows = [min(s["mean"].values()) for s in (snake, standard)]
    highs = [max(s["mean"].values()) for s in (snake, standard)]
    ax.set_ylim(math.floor(min(lows)) - 2, math.ceil(max(highs)) + 1.5)  # zoomed: differences are < 2 points
    ax.set_xticks(range(len(PLAYER_NAMES)), [f"Seat {s}" for s in PLAYER_NAMES])
    _style(ax, "Mean payoff (dice weight, 2 settlements)")
    ax.legend(frameon=False, labelcolor=TEXT_SECONDARY, loc="upper right")
    return _save(fig, path, "Mean payoff by seat: snake vs standard draft",
                 f"{snake['games']:,} games each, same {snake['board_mode']} boards, 4 greedy CPUs."
                 " Error bars = 95% CI. Y-axis does not start at 0.")


def plot_pick_values(snake: dict, standard: dict, path: Path) -> Path:
    """Stacked bars per seat: first-pick value + second-pick value = payoff. Shows why seats differ."""
    fig, axes = _figure(ncols=2, width=10)
    top = max(max(s["mean"].values()) for s in (snake, standard))
    for ax, s in zip(axes, (snake, standard)):
        first = [s["mean_value_1"][seat] for seat in PLAYER_NAMES]
        second = [s["mean_value_2"][seat] for seat in PLAYER_NAMES]
        xs = range(len(PLAYER_NAMES))
        ax.bar(xs, first, 0.6, color=PICK_COLORS[0], edgecolor=SURFACE, linewidth=2, label="1st pick")
        ax.bar(xs, second, 0.6, bottom=first, color=PICK_COLORS[1], edgecolor=SURFACE, linewidth=2, label="2nd pick")
        for x, a, b in zip(xs, first, second):
            # Dark labels on every segment: aqua/yellow are light, so the numbers carry the reading.
            ax.text(x, a / 2, f"{a:.1f}", ha="center", va="center", fontsize=9, color=TEXT)
            ax.text(x, a + b / 2, f"{b:.1f}", ha="center", va="center", fontsize=9, color=TEXT)
            ax.text(x, a + b + 0.3, f"{a + b:.2f}", ha="center", va="bottom", fontsize=9, color=TEXT)
        ax.set_xticks(list(xs), [f"Seat {seat}" for seat in PLAYER_NAMES])
        ax.set_ylim(0, top * 1.12)
        ax.set_title(f"{s['draft']}: {' '.join(draft_order(PLAYER_NAMES, s['draft']))}", color=TEXT, fontsize=11)
        _style(ax, "Mean value (dice weight)" if ax is axes[0] else None)
    axes[1].legend(frameon=False, labelcolor=TEXT_SECONDARY, loc="upper right")
    return _save(fig, path, "Where each seat's payoff comes from",
                 f"Mean value of each seat's 1st and 2nd pick. {snake['games']:,} games each,"
                 f" {snake['board_mode']} boards, 4 greedy CPUs.")


def plot_fairness(summaries: dict, path: Path) -> Path:
    """Two small panels: fairness gap and within-game spread for all four setups."""
    fig, axes = _figure(ncols=2, width=10)
    modes = ("separated", "random")
    panels = [("fairness_gap", "Fairness gap (max - min seat mean)"),
              ("mean_spread", "Avg within-game spread (best - worst)")]
    width = 0.38
    for ax, (key, title) in zip(axes, panels):
        for i, draft in enumerate(("snake", "standard")):
            xs = [k + (i - 0.5) * width for k in range(len(modes))]
            vals = [summaries[(draft, mode)][key] for mode in modes]
            ax.bar(xs, vals, width, color=DRAFT_COLORS[draft], edgecolor=SURFACE, linewidth=2, label=draft)
            for x, v in zip(xs, vals):
                ax.text(x, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=TEXT_SECONDARY)
        top = max(summaries[key2][key] for key2 in SETUPS)
        ax.set_ylim(0, top * 1.3)  # headroom so the legend never sits on a bar
        ax.set_xticks(range(len(modes)), [f"{m} boards" for m in modes])
        ax.set_title(title, color=TEXT, fontsize=11)
        _style(ax, "Points (dice weight)" if ax is axes[0] else None)
    axes[0].legend(frameon=False, labelcolor=TEXT_SECONDARY, loc="upper left", ncols=2)
    games = next(iter(summaries.values()))["games"]
    return _save(fig, path, "Balance across setups (smaller = more balanced)",
                 f"{games:,} games per setup, 4 greedy CPUs. Same seeds for all setups.")


def plot_win_share(snake: dict, standard: dict, path: Path) -> Path:
    """Grouped bars: how often each seat finishes first (ties split 1/k), snake vs standard."""
    fig, (ax,) = _figure()
    width = 0.38
    for i, s in enumerate((snake, standard)):
        xs = [k + (i - 0.5) * width for k in range(len(PLAYER_NAMES))]
        shares = [100 * s["win_share"][seat] for seat in PLAYER_NAMES]
        ax.bar(xs, shares, width, color=DRAFT_COLORS[s["draft"]], edgecolor=SURFACE, linewidth=2, label=s["draft"])
        for x, v in zip(xs, shares):
            ax.text(x, v + 1, f"{v:.0f}%", ha="center", va="bottom", fontsize=8, color=TEXT_SECONDARY)
    # 25% = perfectly even split between 4 seats (named in the legend, not on the chart, to avoid label clashes).
    ax.axhline(25, color=TEXT_SECONDARY, linewidth=1, label="even split (25%)")
    ax.set_ylim(0, 100)
    ax.set_xticks(range(len(PLAYER_NAMES)), [f"Seat {s}" for s in PLAYER_NAMES])
    _style(ax, "Share of games won (%)")
    ax.legend(frameon=False, labelcolor=TEXT_SECONDARY, loc="upper right")
    return _save(fig, path, "Who wins: share of games won by seat",
                 f"Ties split evenly (e.g. 3-way tie = 1/3 win each). {snake['games']:,} games each,"
                 f" same {snake['board_mode']} boards.")


def plot_heatmap(s: dict, path: Path) -> Path:
    """Board heatmap: how often each vertex is taken (any pick) and taken first.

    Numbers differ on every board, so this shows which *positions* end up
    chosen most (e.g. inland corners touch 3 tiles, coast corners only 1-2).
    """
    board = generate_board(0)  # geometry only; same on every board
    cmap = LinearSegmentedColormap.from_list("heat", HEAT_RAMP)
    # Lattice -> real coordinates (1 step = sqrt(3)/2 wide, 1/2 tall); flip y so row 0 is on top.
    pos = {v.id: (v.x * math.sqrt(3) / 2, -v.y / 2) for v in board.vertices}
    fig, axes = _figure(ncols=2, width=11, height=5.6)
    panels = [(s["taken"], "Taken by any player"), (s["first_pick"], "Taken with the very first pick")]
    for ax, (counts, title) in zip(axes, panels):
        shares = [100 * counts[v] / s["games"] for v in range(len(board.vertices))]
        for h in board.hexes:
            ax.add_patch(Polygon([pos[c] for c in h.corners], closed=True, facecolor="#f0efec",
                                 edgecolor="#c9c8c2", linewidth=1))
        dots = ax.scatter([pos[v][0] for v in pos], [pos[v][1] for v in pos], c=shares, cmap=cmap,
                          vmin=0, vmax=max(shares), s=170, edgecolors=SURFACE, linewidths=1.5, zorder=3)
        for v, share in enumerate(shares):  # label only the 5 most-taken spots (selective labels)
            if share >= sorted(shares)[-5]:
                ax.annotate(f"{share:.0f}%", pos[v], xytext=(0, 10), textcoords="offset points",
                            ha="center", fontsize=8, color=TEXT)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, color=TEXT, fontsize=11)
        bar = fig.colorbar(dots, ax=ax, shrink=0.7, pad=0.02)
        bar.set_label("% of games", color=TEXT_SECONDARY)
        bar.ax.tick_params(colors=TEXT_SECONDARY)
    return _save(fig, path, "Which board positions get picked",
                 f"{s['games']:,} games, {s['draft']} draft, {s['board_mode']} boards."
                 " Numbers change every game, so this shows position, not specific numbers.")


# --- Everything at once ---------------------------------------------------------------


def run_experiments(n_games: int, base_seed: int = 0, out_dir: str | Path = "results") -> dict:
    """Simulate all four setups, then write the report and charts to ``out_dir``.

    - Raw CSVs -> ``out_dir/raw/<board>_<draft>.csv`` (large; git-ignored)
    - Report   -> ``out_dir/summary.md``
    - Charts   -> ``out_dir/*.png``
    """
    out = Path(out_dir)
    summaries = {}
    for draft, mode in SETUPS:
        start = time.perf_counter()
        csv_path = simulate(n_games, out / "raw" / f"{mode}_{draft}.csv", base_seed, mode, draft)
        summaries[(draft, mode)] = summarize(csv_path)
        print(f"  {draft:>8} draft, {mode:>9} boards: {n_games:,} games in {time.perf_counter() - start:.0f}s")

    snake, standard = summaries[("snake", "separated")], summaries[("standard", "separated")]
    write_report(summaries, out / "summary.md", base_seed)
    plot_seat_payoffs(snake, standard, out / "seat_payoffs.png")
    plot_pick_values(snake, standard, out / "pick_values.png")
    plot_fairness(summaries, out / "fairness.png")
    plot_win_share(snake, standard, out / "win_share.png")
    plot_heatmap(snake, out / "heatmap.png")
    return summaries
