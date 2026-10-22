"""Tests for the terminal board view."""

import re

import pytest

from src.board import generate_board
from src.game import Game, new_game
from src.text_view import apply_command, describe_vertex, game_log, render, status


@pytest.fixture
def game():
    return Game(generate_board(seed=42, mode="random"))


def labels_in(text):
    """All vertex labels in a rendering, as (marker, number) pairs."""
    vertex_lines = [ln for ln in text.splitlines() if not re.search(r"[|/\\]", ln)]
    return [(m or " ", int(n)) for ln in vertex_lines for m, n in re.findall(r"([A-Dx]?)\s*(\d+)", ln)]


def test_render_shows_every_vertex_once_and_every_tile(game):
    text = render(game)
    assert len(text.splitlines()) == 23
    assert sorted(labels_in(text)) == [(" ", v) for v in range(54)]

    centre_lines = [ln for ln in text.splitlines() if "|" in ln]
    assert len(centre_lines) == 5
    shown = [t for ln in centre_lines for t in ln.replace("|", " ").split()]
    assert sorted(shown) == sorted("--" if n is None else str(n) for n in game.board.numbers)


def test_render_draws_one_mark_per_edge(game):
    text = render(game)
    assert sum(text.count(ch) for ch in "|/\\") == len(game.board.edges()) == 72


def test_render_marks_settlements_and_blocked_vertices(game):
    game.place("A", 22)
    game.place("B", 0)
    labels = labels_in(render(game))
    assert ("A", 22) in labels and ("B", 0) in labels
    assert {v for marker, v in labels if marker == "x"} == {16, 17, 28, 3, 4}
    assert {v for marker, v in labels if marker == " "} == set(game.legal_vertices())


def test_render_values_mode_shows_vertex_values(game):
    shown = sorted(n for _, n in labels_in(render(game, labels="values")))
    assert shown == sorted(game.board.vertex_value(v) for v in range(54))


def test_color_only_adds_escape_codes(game):
    game.place("A", 22)
    colored = render(game, color=True)
    assert "\033[" in colored
    assert re.sub(r"\033\[[0-9;]*m", "", colored) == render(game)


def test_status_shows_turn_settlements_and_payoffs(game):
    assert "Draft: snake (A B C D D C B A)    Turn 1 of 8: player A (human)" in status(game)
    game.place("A", 22)
    game.place("B", 53)
    text = status(game)
    assert "Turn 3 of 8: player C (human)" in text
    assert "Player A (human): vertex 22 (13)  ->  payoff 13" in text
    assert "Player C (human): no settlements  ->  payoff 0" in text
    assert f"Legal vertices left: {len(game.legal_vertices())} of 54" in text


def test_status_lists_both_settlements_and_the_winner_after_a_cpu_game():
    game = new_game(42, "random")
    game.play()
    text = status(game)
    assert "GAME OVER. Winner" in text or "GAME OVER. Tie for first" in text
    a = game.players["A"]
    v1, v2 = a.settlements
    b = game.board
    assert (
        f"Player A (greedy CPU): vertex {v1} ({b.vertex_value(v1)}) + vertex {v2} ({b.vertex_value(v2)})"
        f"  ->  payoff {a.payoff(b)}"
    ) in text


def test_game_log_lists_moves_payoffs_and_result():
    game = new_game(42, "random")
    game.play()
    lines = game_log(game).splitlines()
    assert lines[:8] == [
        f"Turn {m.turn}: Player {m.player} chooses vertex {m.vertex} (value {m.value})" for m in game.moves
    ]
    assert "Final payoffs:" in lines
    for name, payoff in game.payoffs().items():
        assert any(ln.startswith(f"  {name}: {payoff:>2}") for ln in lines)
    winners = game.winners()
    assert lines[-1] == (f"Winner: player {winners[0]}" if len(winners) == 1 else "Tie for first: players " + ", ".join(winners))


def test_describe_vertex(game):
    assert "touches tiles 8, 5, 9  ->  weights 5 + 4 + 4 = value 13" in describe_vertex(game, 22)
    assert "neighbours: 16, 17, 28   state: legal" in describe_vertex(game, 22)
    game.place("A", 22)
    assert "occupied by player A" in describe_vertex(game, 22)
    assert "blocked" in describe_vertex(game, 17)
    assert "not a vertex ID" in describe_vertex(game, 99)


@pytest.mark.parametrize("command", ["22", "a 22"])
def test_apply_command_places_for_the_human_whose_turn_it_is(game, command):
    message = apply_command(game, command)
    assert game.owner == {22: "A"}
    assert message.startswith("Turn 1: Player A chooses vertex 22 (value 13).")
    assert "neighbours: 16, 17, 28   state: occupied by player A" in message


@pytest.mark.parametrize(
    "command, expected",
    [
        ("22", "REJECTED: vertex 22 is already occupied by player A"),
        ("17", "REJECTED: vertex 17 is adjacent to player A's settlement on vertex 22"),
        ("99", "REJECTED: 99 is not a vertex ID (0-53)"),
        ("c 5", "REJECTED: it is player B's turn, not player C's"),
        ("e 5", "REJECTED: unknown player 'E'"),
    ],
)
def test_apply_command_reports_rejections_without_changing_the_game(game, command, expected):
    game.place("A", 22)
    assert apply_command(game, command) == expected
    assert game.owner == {22: "A"}


def test_enter_lets_the_cpu_move_and_waits_for_humans():
    game = new_game(42, "random", humans="B")
    message = apply_command(game, "")  # A is a greedy CPU
    assert message.startswith("Turn 1: Player A chooses vertex")
    assert len(game.moves) == 1
    assert apply_command(game, "") == "It is player B's turn (human): type a vertex number to place."
    assert len(game.moves) == 1


def test_human_cannot_move_for_a_cpu():
    game = new_game(42, "random", humans="B")
    assert apply_command(game, "22") == "REJECTED: player A is a CPU; press Enter to let it move."
    assert game.moves == []


def test_commands_after_the_game_is_over():
    game = new_game(42, "random")
    game.play()
    assert apply_command(game, "").startswith("The game is over.")
    assert apply_command(game, "5").startswith("The game is over.")
    assert apply_command(game, "i 22") == describe_vertex(game, 22)


def test_apply_command_inspects_and_handles_nonsense(game):
    assert apply_command(game, "i 22") == describe_vertex(game, 22)
    assert apply_command(game, "hello there friend").startswith("Did not understand")
    assert apply_command(game, "a b").startswith("Did not understand")
    assert game.owner == {}
