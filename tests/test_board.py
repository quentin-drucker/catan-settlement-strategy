"""Tests for board geometry, adjacency graph, scoring weights and generation (Issue #1)."""

from collections import Counter

import pytest

from src.board import (
    DICE_WEIGHTS,
    NUMBER_TOKENS,
    Board,
    BoardGenerationError,
    generate_board,
)


@pytest.fixture
def board():
    return generate_board(seed=1)


def test_dice_weights_are_ways_out_of_36():
    ways = Counter(a + b for a in range(1, 7) for b in range(1, 7))
    del ways[7]
    assert DICE_WEIGHTS == dict(ways)


def test_board_has_19_hexes_in_3_4_5_4_3_rows(board):
    assert len(board.hexes) == 19
    rows = Counter(h.r for h in board.hexes)
    assert [rows[r] for r in sorted(rows)] == [3, 4, 5, 4, 3]


def test_board_has_54_unique_vertices(board):
    assert len(board.vertices) == 54
    assert len({(v.x, v.y) for v in board.vertices}) == 54
    assert [v.id for v in board.vertices] == list(range(54))


def test_board_has_72_edges(board):
    assert len(board.edges()) == 72


def test_each_hex_has_six_distinct_corners(board):
    for h in board.hexes:
        assert len(h.corners) == 6
        assert len(set(h.corners)) == 6


def test_hex_and_vertex_references_agree(board):
    for h in board.hexes:
        for v in h.corners:
            assert h.id in board.vertices[v].hexes
    for v in board.vertices:
        for h in v.hexes:
            assert v.id in board.hexes[h].corners


def test_vertices_touch_one_to_three_hexes(board):
    counts = Counter(len(v.hexes) for v in board.vertices)
    assert set(counts) <= {1, 2, 3}
    # Standard board: 18 coast corners touch 1 hex, 12 touch 2, 24 interior touch 3.
    assert counts == {1: 18, 2: 12, 3: 24}


def test_vertex_adjacency_is_symmetric_and_irreflexive(board):
    for v in board.vertices:
        assert v.id not in v.neighbors
        for n in v.neighbors:
            assert v.id in board.vertices[n].neighbors


def test_vertex_degrees(board):
    # Coast corners touching one hex have 2 neighbours; all others have 3.
    for v in board.vertices:
        assert len(v.neighbors) == (2 if len(v.hexes) == 1 else 3)


def test_neighbouring_vertices_are_one_hex_side_apart(board):
    # Lattice step is sqrt(3)/2 horizontally and 1/2 vertically, so a real
    # distance of 1 means 3*dx^2 + dy^2 == 4.
    for a, b in board.edges():
        va, vb = board.vertices[a], board.vertices[b]
        assert 3 * (va.x - vb.x) ** 2 + (va.y - vb.y) ** 2 == 4


def test_neighbouring_vertices_are_consecutive_corners_of_a_shared_hex(board):
    for a, b in board.edges():
        shared = set(board.vertices[a].hexes) & set(board.vertices[b].hexes)
        assert any(
            {h_corners[k], h_corners[(k + 1) % 6]} == {a, b}
            for h_corners in (board.hexes[h].corners for h in shared)
            for k in range(6)
        )


def test_adjacent_hexes_share_exactly_two_corners(board):
    for h in board.hexes:
        assert 3 <= len(h.neighbors) <= 6
        for n in h.neighbors:
            assert h.id in board.hexes[n].neighbors
            assert len(set(h.corners) & set(board.hexes[n].corners)) == 2
        for other in board.hexes:
            if other.id != h.id and other.id not in h.neighbors:
                assert not set(h.corners) & set(other.corners)


def test_centre_hex_has_six_neighbours(board):
    centre = next(h for h in board.hexes if (h.q, h.r) == (0, 0))
    assert len(centre.neighbors) == 6


def test_geometry_is_identical_across_boards():
    a, b = generate_board(seed=1), generate_board(seed=2)
    assert [(v.x, v.y, v.hexes, v.neighbors) for v in a.vertices] == [
        (v.x, v.y, v.hexes, v.neighbors) for v in b.vertices
    ]
    assert [h.corners for h in a.hexes] == [h.corners for h in b.hexes]


@pytest.mark.parametrize("mode", ["random", "separated"])
def test_number_distribution_preserved(mode):
    for seed in range(50):
        numbers = generate_board(seed, mode).numbers
        assert numbers.count(None) == 1
        assert Counter(n for n in numbers if n is not None) == Counter(NUMBER_TOKENS)


def test_desert_contributes_zero_weight():
    board = generate_board(seed=3)
    desert = next(h for h in board.hexes if h.number is None)
    assert desert.weight == 0
    for v in desert.corners:
        expected = sum(board.hexes[h].weight for h in board.vertices[v].hexes if h != desert.id)
        assert board.vertex_value(v) == expected


def test_manual_vertex_scoring():
    # Put 6, 9 and 3 on the three hexes around one interior vertex.
    board = Board([*NUMBER_TOKENS, None])
    v = next(v for v in board.vertices if len(v.hexes) == 3)
    numbers = board.numbers
    for h in v.hexes:
        numbers[h] = None
    numbers[v.hexes[0]], numbers[v.hexes[1]], numbers[v.hexes[2]] = 6, 9, 3
    board = Board(numbers)
    assert board.vertex_value(v.id) == 5 + 4 + 2

    numbers[v.hexes[0]], numbers[v.hexes[1]], numbers[v.hexes[2]] = 2, 4, 12
    assert Board(numbers).vertex_value(v.id) == 1 + 3 + 1

    numbers[v.hexes[0]], numbers[v.hexes[1]], numbers[v.hexes[2]] = 8, None, 5
    assert Board(numbers).vertex_value(v.id) == 5 + 0 + 4


def test_vertex_values_sum_tile_weights(board):
    for v in board.vertices:
        assert board.vertex_value(v.id) == sum(board.hexes[h].weight for h in v.hexes)


def test_same_seed_same_board_different_seed_differs():
    assert generate_board(42).numbers == generate_board(42).numbers
    assert generate_board(42).numbers != generate_board(43).numbers


def test_separated_mode_has_no_adjacent_6_and_8():
    for seed in range(200):
        board = generate_board(seed, "separated")
        assert not board.has_adjacent_high_numbers()
        for h in board.hexes:
            if h.number in (6, 8):
                assert all(board.hexes[n].number not in (6, 8) for n in h.neighbors)


def test_random_mode_sometimes_has_adjacent_6_and_8():
    assert any(generate_board(seed).has_adjacent_high_numbers() for seed in range(200))


def test_separated_generation_fails_cleanly_when_attempts_exhausted():
    with pytest.raises(BoardGenerationError):
        # With a single attempt, some seed in this range must fail.
        for seed in range(200):
            generate_board(seed, "separated", max_attempts=1)


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        generate_board(0, "bogus")
    with pytest.raises(ValueError):
        Board([None] * 18)
    with pytest.raises(ValueError):
        Board([7] + [None] * 18)
