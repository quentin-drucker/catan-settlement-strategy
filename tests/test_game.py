"""Tests for settlement placement rules and player payoffs (Issue #2)."""

import random

import pytest

from src.board import NUMBER_TOKENS, Board, generate_board
from src.game import PLAYER_NAMES, Game, IllegalPlacementError


@pytest.fixture
def game():
    return Game(generate_board(seed=42))


def snapshot(game):
    return (dict(game.owner), set(game.blocked), {n: list(p.settlements) for n, p in game.players.items()})


def test_new_game_has_four_players_and_every_vertex_legal(game):
    assert tuple(game.players) == PLAYER_NAMES == ("A", "B", "C", "D")
    assert game.legal_vertices() == list(range(54))
    assert game.owner == {} and game.blocked == set()
    assert game.payoffs() == {"A": 0, "B": 0, "C": 0, "D": 0}


@pytest.mark.parametrize("vertex", [0, 22, 53])  # coast corner, interior, last ID
def test_placement_blocks_vertex_and_all_neighbours_only(game, vertex):
    neighbors = set(game.board.vertices[vertex].neighbors)
    game.place("A", vertex)

    assert game.owner == {vertex: "A"}
    assert game.blocked == {vertex} | neighbors
    assert not game.is_legal(vertex)
    assert all(not game.is_legal(n) for n in neighbors)
    assert game.legal_vertices() == [v for v in range(54) if v not in {vertex} | neighbors]


def test_place_returns_value_and_records_settlement(game):
    assert game.place("B", 22) == game.board.vertex_value(22) == 13
    assert game.players["B"].settlements == [22]
    assert game.players["A"].settlements == []


@pytest.mark.parametrize("second_player", ["A", "B"])
def test_settlement_cannot_be_placed_twice(game, second_player):
    game.place("A", 22)
    before = snapshot(game)
    with pytest.raises(IllegalPlacementError, match="occupied by player A"):
        game.place(second_player, 22)
    assert snapshot(game) == before


@pytest.mark.parametrize("second_player", ["A", "B"])
def test_adjacent_placement_rejected_for_every_player(game, second_player):
    game.place("A", 22)
    before = snapshot(game)
    for n in game.board.vertices[22].neighbors:
        with pytest.raises(IllegalPlacementError, match="adjacent to player A's settlement on vertex 22"):
            game.place(second_player, n)
    assert snapshot(game) == before


def test_vertex_two_steps_away_is_still_legal(game):
    game.place("A", 22)
    two_away = {
        m for n in game.board.vertices[22].neighbors for m in game.board.vertices[n].neighbors
    } - {22}
    assert two_away and all(game.is_legal(v) for v in two_away)
    game.place("B", min(two_away))


@pytest.mark.parametrize("bad", [-1, 54, 1000, "22", 22.0, None])
def test_invalid_vertex_ids_rejected(game, bad):
    assert not game.is_legal(bad)
    with pytest.raises(IllegalPlacementError, match="not a vertex ID"):
        game.place("A", bad)
    assert snapshot(game) == ({}, set(), {n: [] for n in PLAYER_NAMES})


def test_unknown_player_rejected(game):
    with pytest.raises(ValueError, match="unknown player"):
        game.place("E", 22)
    assert game.owner == {}


def test_payoff_is_sum_of_settlement_values(game):
    board = game.board
    game.place("A", 22)
    game.place("B", 0)
    game.place("A", 53)
    assert game.players["A"].settlements == [22, 53]
    assert game.payoffs() == {
        "A": board.vertex_value(22) + board.vertex_value(53),
        "B": board.vertex_value(0),
        "C": 0,
        "D": 0,
    }


def test_manual_payoff_on_hand_built_board():
    # Hexes 0-18 in reading order; desert in the centre (hex 9).
    numbers = [10, 2, 9, 12, 6, 4, 10, 9, 11, None, 3, 8, 8, 3, 4, 5, 5, 6, 11]
    assert sorted(n for n in numbers if n) == sorted(NUMBER_TOKENS)
    game = Game(Board(numbers))
    board = game.board

    # Vertex shared by hexes 0 (10), 3 (12) and 4 (6): weights 3 + 1 + 5.
    v1 = (set(board.hexes[0].corners) & set(board.hexes[3].corners) & set(board.hexes[4].corners)).pop()
    # Vertex shared by hexes 8 (11), 9 (desert) and 13 (3): weights 2 + 0 + 2.
    v2 = (set(board.hexes[8].corners) & set(board.hexes[9].corners) & set(board.hexes[13].corners)).pop()

    assert game.place("C", v1) == 9
    assert game.place("C", v2) == 4
    assert game.payoffs()["C"] == 13


@pytest.mark.parametrize("seed", range(20))
def test_random_legal_placements_keep_rules_until_board_is_full(seed):
    rng = random.Random(seed)
    game = Game(generate_board(seed))
    board = game.board
    while game.legal_vertices():
        game.place(rng.choice(PLAYER_NAMES), rng.choice(game.legal_vertices()))

    occupied = set(game.owner)
    # No two settlements are adjacent.
    assert all(not occupied & set(board.vertices[v].neighbors) for v in occupied)
    # Blocked is exactly the settlements plus their neighbours, and now covers the board.
    assert game.blocked == occupied | {n for v in occupied for n in board.vertices[v].neighbors}
    assert game.blocked == set(range(54))
    # Every settlement is recorded for exactly one player.
    placed = [v for p in game.players.values() for v in p.settlements]
    assert sorted(placed) == sorted(occupied)
    assert all(game.owner[v] == p.name for p in game.players.values() for v in p.settlements)
    assert sum(game.payoffs().values()) == sum(board.vertex_value(v) for v in occupied)
