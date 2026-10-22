"""Tests for CPU strategies (Issue #3)."""

import random

import pytest

from src.board import generate_board
from src.game import DRAFT_FORMATS, Game, new_game
from src.strategies import GreedyStrategy, Strategy


def test_strategy_is_an_interface():
    with pytest.raises(TypeError):
        Strategy()


@pytest.mark.parametrize("draft", DRAFT_FORMATS)
def test_greedy_always_picks_a_legal_maximum_value_vertex(draft):
    for seed in range(100):
        game = new_game(seed, draft=draft)
        while not game.is_over:
            legal = set(game.legal_vertices())
            best = max(game.board.vertex_value(v) for v in legal)
            move = game.play_turn()
            assert move.vertex in legal
            assert move.value == best


def test_greedy_breaks_ties_randomly_among_the_best_only():
    # Seed-42 random board: vertices 17 and 22 tie for the best value (13).
    game = Game(generate_board(42, "random"))
    assert sorted(v for v in range(54) if game.board.vertex_value(v) == 13) == [17, 22]
    choices = {GreedyStrategy(random.Random(s)).choose(game) for s in range(50)}
    assert choices == {17, 22}


def test_greedy_tie_breaking_is_reproducible():
    game = Game(generate_board(42, "random"))
    for s in range(20):
        first = [GreedyStrategy(random.Random(s)).choose(game) for _ in range(5)]
        assert first == [GreedyStrategy(random.Random(s)).choose(game) for _ in range(5)]


def test_greedy_does_not_change_the_game():
    game = Game(generate_board(3))
    GreedyStrategy(random.Random(0)).choose(game)
    assert game.moves == [] and game.blocked == set()
