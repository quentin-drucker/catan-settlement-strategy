"""Bridge between the website (Watch/Play pages) and the game engine.

The pages run this Python code inside the browser with Pyodide (= Python
compiled to WebAssembly, so it runs in a web page with no server). JavaScript
calls the functions below and gets back JSON text (= plain data: lists,
numbers, strings) that it can draw. No game rules live here or in the
JavaScript; everything goes through ``Game``.

- Games are kept in ``GAMES`` under a name chosen by the page, e.g. "snake".
- Every call returns the full state, so the page just redraws from it.
- Same seed -> same board and same CPU moves as ``python main.py play``.
"""

from __future__ import annotations

import json

from src.game import Game, IllegalPlacementError, new_game

GAMES: dict[str, Game] = {}  # page-chosen name -> running game


def board_data(game: Game) -> dict:
    """Board geometry + numbers. Positions are the integer lattice from board.py."""
    b = game.board
    return {
        "hexes": [
            {"id": h.id, "number": h.number, "weight": h.weight, "corners": list(h.corners)}
            for h in b.hexes
        ],
        "vertices": [
            {"id": v.id, "x": v.x, "y": v.y, "hexes": list(v.hexes), "value": b.vertex_value(v.id)}
            for v in b.vertices
        ],
    }


def state_data(game: Game) -> dict:
    """Everything the page needs to draw one moment of the game."""
    current = game.current_player
    return {
        "draft": game.draft,
        "order": game.order,
        "current": current.name if current else None,
        "current_is_human": bool(current and current.strategy is None),
        "is_over": game.is_over,
        "owner": {str(v): name for v, name in game.owner.items()},  # JSON keys must be strings
        "blocked": sorted(game.blocked),
        "legal": game.legal_vertices(),
        "moves": [{"turn": m.turn, "player": m.player, "vertex": m.vertex, "value": m.value} for m in game.moves],
        "players": [
            {
                "name": name,
                "kind": "human" if p.strategy is None else f"{p.strategy.name} CPU",
                "settlements": p.settlements,
                "payoff": p.payoff(game.board),
            }
            for name, p in game.players.items()
        ],
        "winners": game.winners() if game.is_over else [],
    }


def new(key: str, seed: int, board_mode: str = "separated", draft: str = "snake", humans: str = "") -> str:
    """Start a game under ``key`` (greedy CPUs except the ``humans`` seats); return board + state."""
    game = GAMES[key] = new_game(int(seed), board_mode, draft, humans)
    return json.dumps({"board": board_data(game), "state": state_data(game)})


def step(key: str) -> str:
    """Let the current CPU make one move; return the new state."""
    game = GAMES[key]
    game.play_turn()
    return json.dumps({"state": state_data(game)})


def place(key: str, vertex: int) -> str:
    """Place for the human whose turn it is. Illegal moves come back as {"error": reason}."""
    game = GAMES[key]
    player = game.current_player
    if player is None:
        error = "the game is over"
    elif player.strategy is not None:  # a click must never make a CPU's move for it
        error = f"it is player {player.name}'s turn (computer), not yours"
    else:
        try:
            game.place(player.name, int(vertex))
            return json.dumps({"state": state_data(game)})
        except IllegalPlacementError as e:
            error = str(e)
    return json.dumps({"error": error, "state": state_data(game)})


def greedy_payoff(seed: int, board_mode: str, draft: str, seat: str) -> int:
    """What a greedy CPU would have scored in ``seat`` on the same board (for comparison)."""
    game = new_game(int(seed), board_mode, draft)
    game.play()
    return game.players[seat].payoff(game.board)
