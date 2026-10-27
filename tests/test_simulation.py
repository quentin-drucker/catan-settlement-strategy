"""Tests for batch simulations and the fairness analysis (Issue #4).

- CSV: right rows/columns, values match the board, ties split, reproducible
- same seeds -> same boards under snake and standard
- summary statistics match a hand computation from the CSV
- standard draft + greedy CPUs: seat A can never score below anyone (see below)
- the full experiment run writes the report, charts and raw CSVs
"""

import csv
import statistics

import pytest

from src.analysis import paired_spread_difference, run_experiments, summarize
from src.game import PLAYER_NAMES, new_game
from src.simulation import CSV_COLUMNS, simulate


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def snake_csv(tmp_path):
    return simulate(40, tmp_path / "snake.csv", base_seed=100, board_mode="random", draft="snake")


@pytest.fixture
def standard_csv(tmp_path):
    return simulate(40, tmp_path / "standard.csv", base_seed=100, board_mode="random", draft="standard")


# --- CSV output ----------------------------------------------------------------


def test_csv_has_one_row_per_player_per_game(snake_csv):
    rows = read_rows(snake_csv)
    assert list(rows[0]) == CSV_COLUMNS
    assert len(rows) == 40 * 4
    # Rows come in blocks of 4 (A, B, C, D) per game, seeds counting up from base_seed.
    for i in range(40):
        block = rows[4 * i : 4 * i + 4]
        assert [r["player"] for r in block] == list(PLAYER_NAMES)
        assert {r["seed"] for r in block} == {str(100 + i)}
        assert {r["sim_id"] for r in block} == {str(i)}


def test_csv_values_match_a_replayed_game(snake_csv):
    # Replaying any seed with new_game must give exactly the CSV's settlements and values.
    rows = read_rows(snake_csv)
    for row in rows[:20]:
        game = new_game(int(row["seed"]), row["board_mode"], row["draft"])
        game.play()
        player = game.players[row["player"]]
        v1, v2 = player.settlements
        assert (int(row["settlement_1"]), int(row["settlement_2"])) == (v1, v2)
        assert int(row["value_1"]) == game.board.vertex_value(v1)
        assert int(row["value_2"]) == game.board.vertex_value(v2)
        assert int(row["payoff"]) == int(row["value_1"]) + int(row["value_2"])


def test_win_shares_add_up_to_one_per_game(snake_csv):
    rows = read_rows(snake_csv)
    for i in range(0, len(rows), 4):
        block = rows[i : i + 4]
        assert sum(float(r["win_share"]) for r in block) == pytest.approx(1)
        # Every share-holder has the top payoff.
        top = max(int(r["payoff"]) for r in block)
        assert all(int(r["payoff"]) == top for r in block if float(r["win_share"]) > 0)


def test_simulation_is_reproducible(tmp_path):
    a = simulate(25, tmp_path / "a.csv", base_seed=7)
    b = simulate(25, tmp_path / "b.csv", base_seed=7)
    assert a.read_bytes() == b.read_bytes()


def test_same_seeds_give_same_first_round_under_both_drafts(snake_csv, standard_csv):
    # Same board + same tie-break RNG -> turns 1-4 (A B C D in both drafts) are identical.
    snake, standard = read_rows(snake_csv), read_rows(standard_csv)
    assert [r["settlement_1"] for r in snake] == [r["settlement_1"] for r in standard]


def test_greedy_takes_the_same_spots_under_both_drafts():
    # Greedy only looks at the board, never at who is picking -> same board + same tie-break
    # RNG = same 8 vertices in the same order. The draft only changes who gets each pick.
    for mode in ("separated", "random"):
        for seed in range(50):
            snake = [m.vertex for m in new_game(seed, mode, "snake").play()]
            standard = [m.vertex for m in new_game(seed, mode, "standard").play()]
            assert snake == standard


# --- Summary statistics ----------------------------------------------------------


def test_summary_matches_a_hand_computation(snake_csv):
    s = summarize(snake_csv)
    rows = read_rows(snake_csv)
    assert s["games"] == 40 and (s["draft"], s["board_mode"]) == ("snake", "random")
    for seat in PLAYER_NAMES:
        payoffs = [int(r["payoff"]) for r in rows if r["player"] == seat]
        assert s["mean"][seat] == pytest.approx(statistics.fmean(payoffs))
        assert s["std"][seat] == pytest.approx(statistics.stdev(payoffs))
        assert s["mean"][seat] == pytest.approx(s["mean_value_1"][seat] + s["mean_value_2"][seat])
    assert s["fairness_gap"] == pytest.approx(max(s["mean"].values()) - min(s["mean"].values()))
    assert sum(s["win_share"].values()) == pytest.approx(1)
    # 8 settlements per game; exactly one very-first pick per game.
    assert sum(s["taken"].values()) == 8 * 40
    assert sum(s["first_pick"].values()) == 40
    assert s["seeds"] == list(range(100, 140))


def test_standard_draft_seat_a_never_scores_below_anyone(standard_csv):
    # Greedy picks never get better over time (options only shrink). In A B C D A B C D,
    # A's two picks are each >= B's, B's >= C's, ... -> A >= B >= C >= D in every game,
    # so the per-game spread always equals A - D and its average equals the fairness gap.
    rows = read_rows(standard_csv)
    for i in range(0, len(rows), 4):
        payoffs = [int(r["payoff"]) for r in rows[i : i + 4]]
        assert payoffs == sorted(payoffs, reverse=True)
    s = summarize(standard_csv)
    assert s["mean_spread"] == pytest.approx(s["fairness_gap"])


def test_paired_spread_difference(snake_csv, standard_csv, tmp_path):
    a, b = summarize(snake_csv), summarize(standard_csv)
    assert paired_spread_difference(a, a) == (0, 0)
    diff, ci = paired_spread_difference(a, b)
    assert diff == pytest.approx(a["mean_spread"] - b["mean_spread"]) and ci >= 0
    # Different seeds can't be paired.
    other = summarize(simulate(40, tmp_path / "other.csv", base_seed=999))
    with pytest.raises(AssertionError):
        paired_spread_difference(a, other)


# --- Full run -----------------------------------------------------------------------


def test_run_experiments_writes_report_charts_and_raw_data(tmp_path):
    summaries = run_experiments(20, base_seed=0, out_dir=tmp_path)
    assert len(summaries) == 4
    for name in ("seat_payoffs", "pick_values", "fairness", "win_share", "heatmap"):
        assert (tmp_path / f"{name}.png").stat().st_size > 10_000
    for name in ("separated_snake", "separated_standard", "random_snake", "random_standard"):
        assert len(read_rows(tmp_path / "raw" / f"{name}.csv")) == 20 * 4
    report = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| snake draft, separated boards |" in report
    assert "spread(snake) - spread(standard)" in report
