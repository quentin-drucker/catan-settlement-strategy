"""Tests for the website bridge (src/web.py), the Python side of the Watch/Play pages.

- new/step/place return valid JSON with the board and the state
- CPU games stepped through the bridge match the engine exactly
- human moves: legal ones apply, illegal ones come back as an error and change nothing
- greedy_payoff matches a full CPU game
"""

import json

from src import web
from src.game import new_game


def test_new_returns_board_and_state():
    data = json.loads(web.new("t", 42, "separated", "snake"))
    assert len(data["board"]["hexes"]) == 19
    assert len(data["board"]["vertices"]) == 54
    v22 = next(v for v in data["board"]["vertices"] if v["id"] == 22)
    assert v22["value"] == new_game(42).board.vertex_value(22)
    s = data["state"]
    assert s["current"] == "A" and s["moves"] == [] and not s["is_over"]
    assert s["order"] == list("ABCDDCBA")
    assert len(s["legal"]) == 54


def test_stepping_through_the_bridge_matches_the_engine():
    for draft in ("snake", "standard"):
        web.new("t", 7, "separated", draft)
        for _ in range(8):
            state = json.loads(web.step("t"))["state"]
        engine = new_game(7, "separated", draft)
        engine.play()
        assert [m["vertex"] for m in state["moves"]] == [m.vertex for m in engine.moves]
        assert {p["name"]: p["payoff"] for p in state["players"]} == engine.payoffs()
        assert state["is_over"] and state["winners"] == engine.winners()


def test_human_moves_apply_and_illegal_ones_are_rejected():
    s = json.loads(web.new("t", 42, "random", "snake", humans="A"))["state"]
    assert s["current_is_human"]
    after = json.loads(web.place("t", 22))
    assert "error" not in after
    assert after["state"]["owner"] == {"22": "A"}
    assert after["state"]["current"] == "B" and not after["state"]["current_is_human"]
    # B is a CPU; a human click now is rejected (not A's turn) and nothing changes.
    bad = json.loads(web.place("t", 0))
    assert "turn" in bad["error"]
    assert bad["state"]["owner"] == {"22": "A"}


def test_occupied_and_adjacent_spots_rejected_for_humans():
    web.new("t", 42, "random", "snake", humans="AB")
    web.place("t", 22)
    for vertex, reason in ((22, "occupied"), (17, "adjacent")):
        bad = json.loads(web.place("t", vertex))
        assert reason in bad["error"]
        assert bad["state"]["current"] == "B"


def test_place_after_game_over_is_an_error():
    web.new("t", 3)
    for _ in range(8):
        web.step("t")
    bad = json.loads(web.place("t", 0))
    assert bad["error"] == "the game is over"


def test_greedy_payoff_matches_a_cpu_game():
    game = new_game(11, "separated", "standard")
    game.play()
    assert web.greedy_payoff(11, "separated", "standard", "C") == game.players["C"].payoff(game.board)
