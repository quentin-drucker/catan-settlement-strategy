"""Tests for placement rules and payoffs (Issue #2) and the draft controller (Issue #3)."""

import random

import pytest

from src.board import NUMBER_TOKENS, Board, generate_board
from src.game import (
    DRAFT_FORMATS,
    PLAYER_NAMES,
    Game,
    IllegalPlacementError,
    Move,
    draft_order,
    new_game,
)


@pytest.fixture
def game():
    return Game(generate_board(seed=42, mode="random"))


def snapshot(game):
    return (
        dict(game.owner),
        set(game.blocked),
        {n: list(p.settlements) for n, p in game.players.items()},
        list(game.moves),
    )


def advance_to_d(game):
    """Play A, B, C on vertices far from 22 and each other, so it is D's turn (snake)."""
    for player, vertex in zip("ABC", (0, 53, 26)):
        game.place(player, vertex)
    assert game.current_player.name == "D"


def play_randomly(game, rng):
    """Play every remaining turn on a random legal vertex."""
    while not game.is_over:
        game.place(game.current_player.name, rng.choice(game.legal_vertices()))


# --- Issue #2: placement rules and payoffs ------------------------------------


def test_new_game_has_four_players_and_every_vertex_legal(game):
    assert tuple(game.players) == PLAYER_NAMES == ("A", "B", "C", "D")
    assert game.legal_vertices() == list(range(54))
    assert game.owner == {} and game.blocked == set() and game.moves == []
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


def test_place_returns_value_and_records_settlement_and_move(game):
    assert game.place("A", 22) == game.board.vertex_value(22) == 13
    assert game.players["A"].settlements == [22]
    assert game.players["B"].settlements == []
    assert game.moves == [Move(turn=1, player="A", vertex=22, value=13)]


def test_settlement_cannot_be_placed_twice_by_another_player(game):
    game.place("A", 22)
    before = snapshot(game)
    with pytest.raises(IllegalPlacementError, match="occupied by player A"):
        game.place("B", 22)
    assert snapshot(game) == before


def test_settlement_cannot_be_placed_twice_by_the_same_player(game):
    advance_to_d(game)
    game.place("D", 22)  # snake: D also has the next turn
    before = snapshot(game)
    with pytest.raises(IllegalPlacementError, match="occupied by player D"):
        game.place("D", 22)
    assert snapshot(game) == before


def test_adjacent_placement_rejected_for_another_player(game):
    game.place("A", 22)
    before = snapshot(game)
    for n in game.board.vertices[22].neighbors:
        with pytest.raises(IllegalPlacementError, match="adjacent to player A's settlement on vertex 22"):
            game.place("B", n)
    assert snapshot(game) == before


def test_adjacent_placement_rejected_for_the_same_player(game):
    advance_to_d(game)
    game.place("D", 22)
    before = snapshot(game)
    for n in game.board.vertices[22].neighbors:
        with pytest.raises(IllegalPlacementError, match="adjacent to player D's settlement on vertex 22"):
            game.place("D", n)
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
    assert snapshot(game) == ({}, set(), {n: [] for n in PLAYER_NAMES}, [])


def test_unknown_player_rejected(game):
    with pytest.raises(ValueError, match="unknown player"):
        game.place("E", 22)
    assert game.owner == {}


def test_payoff_is_sum_of_settlement_values(game):
    board = game.board
    for player, vertex in zip("ABCD", (22, 0, 53, 31)):
        game.place(player, vertex)
    game.place("D", 2)
    assert game.players["D"].settlements == [31, 2]
    assert game.payoffs() == {
        "A": board.vertex_value(22),
        "B": board.vertex_value(0),
        "C": board.vertex_value(53),
        "D": board.vertex_value(31) + board.vertex_value(2),
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

    assert game.place("A", v1) == 9
    assert game.place("B", v2) == 4
    assert game.payoffs() == {"A": 9, "B": 4, "C": 0, "D": 0}


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("draft", DRAFT_FORMATS)
def test_random_legal_games_keep_every_rule(seed, draft):
    game = Game(generate_board(seed), draft=draft)
    board = game.board
    play_randomly(game, random.Random(seed))

    occupied = set(game.owner)
    assert len(occupied) == 8
    # No two settlements are adjacent.
    assert all(not occupied & set(board.vertices[v].neighbors) for v in occupied)
    # Blocked is exactly the settlements plus their neighbours.
    assert game.blocked == occupied | {n for v in occupied for n in board.vertices[v].neighbors}
    # Every settlement is recorded for exactly one player.
    assert all(game.owner[v] == p.name for p in game.players.values() for v in p.settlements)
    assert sum(game.payoffs().values()) == sum(board.vertex_value(v) for v in occupied)


# --- Issue #3: draft order and turns ------------------------------------------


def test_draft_orders():
    assert draft_order(PLAYER_NAMES, "snake") == list("ABCDDCBA")
    assert draft_order(PLAYER_NAMES, "standard") == list("ABCDABCD")
    with pytest.raises(ValueError, match="unknown draft"):
        draft_order(PLAYER_NAMES, "bogus")
    with pytest.raises(ValueError, match="unknown draft"):
        Game(generate_board(1), draft="bogus")


@pytest.mark.parametrize("draft, expected", [("snake", "ABCDDCBA"), ("standard", "ABCDABCD")])
def test_turns_follow_the_draft_order(draft, expected):
    game = Game(generate_board(7), draft=draft)
    seen = []
    while not game.is_over:
        seen.append(game.current_player.name)
        game.place(game.current_player.name, game.legal_vertices()[0])
    assert "".join(seen) == expected
    assert [m.player for m in game.moves] == list(expected)
    assert [m.turn for m in game.moves] == list(range(1, 9))


def test_out_of_turn_placement_rejected(game):
    with pytest.raises(IllegalPlacementError, match="it is player A's turn, not player B's"):
        game.place("B", 22)
    game.place("A", 22)
    with pytest.raises(IllegalPlacementError, match="it is player B's turn, not player A's"):
        game.place("A", 0)
    assert snapshot(game)[0] == {22: "A"}


def test_game_ends_after_eight_placements_with_two_each(game):
    play_randomly(game, random.Random(0))
    assert game.is_over and game.current_player is None
    assert len(game.moves) == 8
    assert all(len(p.settlements) == 2 for p in game.players.values())
    before = snapshot(game)
    with pytest.raises(IllegalPlacementError, match="the game is over"):
        game.place("A", game.legal_vertices()[0])
    with pytest.raises(IllegalPlacementError, match="the game is over"):
        game.play_turn()
    assert snapshot(game) == before


def test_play_turn_refuses_to_move_for_a_human():
    game = new_game(seed=1, humans="A")
    with pytest.raises(RuntimeError, match="player A is human"):
        game.play_turn()
    game.place("A", game.legal_vertices()[0])
    move = game.play_turn()  # B is a CPU
    assert move.player == "B" and move.turn == 2


@pytest.mark.parametrize("draft", DRAFT_FORMATS)
@pytest.mark.parametrize("board_mode", ["separated", "random"])
def test_full_cpu_games_are_complete_and_consistent(draft, board_mode):
    for seed in range(50):
        game = new_game(seed, board_mode, draft)
        moves = game.play()
        assert game.is_over and len(moves) == 8
        assert [m.player for m in moves] == draft_order(PLAYER_NAMES, draft)
        assert all(len(p.settlements) == 2 for p in game.players.values())
        for name, payoff in game.payoffs().items():
            assert payoff == sum(m.value for m in moves if m.player == name)
        assert all(m.value == game.board.vertex_value(m.vertex) for m in moves)


def test_same_seed_gives_identical_game():
    for seed in range(20):
        assert new_game(seed).play() == new_game(seed).play()
    assert len({tuple(new_game(seed).play()) for seed in range(20)}) > 1


def test_same_seed_gives_same_board_under_both_drafts():
    for seed in range(20):
        snake, standard = new_game(seed, draft="snake"), new_game(seed, draft="standard")
        assert snake.board.numbers == standard.board.numbers


def test_new_game_board_mode_and_seats():
    game = new_game(5, board_mode="separated", humans="AC")
    assert not game.board.has_adjacent_high_numbers()
    assert [name for name, p in game.players.items() if p.strategy is None] == ["A", "C"]
    assert game.board.numbers == generate_board(5, "separated").numbers


def test_winners_reports_single_winner_and_ties(game):
    for player, vertex in zip("ABC", (12, 28, 0)):
        game.place(player, vertex)
    assert game.payoffs() == {"A": 12, "B": 12, "C": 3, "D": 0}
    assert game.winners() == ["A", "B"]
    game.place("D", 31)
    game.place("D", 2)
    assert game.payoffs()["D"] == 15
    assert game.winners() == ["D"]
