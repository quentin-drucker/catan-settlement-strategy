"""Tests for the terminal board view."""

import re

import pytest

from src.board import generate_board
from src.game import Game
from src.text_view import apply_command, describe_vertex, render, status


@pytest.fixture
def game():
    return Game(generate_board(seed=42))


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


def test_status_lists_settlements_and_payoffs(game):
    game.place("A", 22)
    game.place("A", 53)
    text = status(game)
    assert "Player A: vertex 22 (13) + vertex 53 (3)  ->  payoff 16" in text
    assert "Player B: no settlements  ->  payoff 0" in text
    assert f"Legal vertices left: {len(game.legal_vertices())} of 54" in text


def test_describe_vertex(game):
    assert "touches tiles 8, 5, 9  ->  weights 5 + 4 + 4 = value 13" in describe_vertex(game, 22)
    assert "neighbours: 16, 17, 28   state: legal" in describe_vertex(game, 22)
    game.place("A", 22)
    assert "occupied by player A" in describe_vertex(game, 22)
    assert "blocked" in describe_vertex(game, 17)
    assert "not a vertex ID" in describe_vertex(game, 99)


def test_apply_command_places_and_reports(game):
    message = apply_command(game, "a 22")
    assert game.owner == {22: "A"}
    assert "Player A placed on vertex 22; neighbours 16, 17, 28 are now blocked." in message


@pytest.mark.parametrize(
    "command, expected",
    [
        ("b 22", "REJECTED: vertex 22 is already occupied by player A"),
        ("b 17", "REJECTED: vertex 17 is adjacent to player A's settlement on vertex 22"),
        ("b 99", "REJECTED: 99 is not a vertex ID (0-53)"),
        ("e 5", "REJECTED: unknown player 'E'"),
    ],
)
def test_apply_command_reports_rejections_without_changing_the_game(game, command, expected):
    game.place("A", 22)
    assert apply_command(game, command) == expected
    assert game.owner == {22: "A"}


def test_apply_command_inspects_and_handles_nonsense(game):
    assert apply_command(game, "22") == describe_vertex(game, 22)
    assert apply_command(game, "hello there friend").startswith("Did not understand")
    assert apply_command(game, "").startswith("Did not understand")
    assert game.owner == {}
