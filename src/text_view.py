"""Plain-text view of the board for the terminal.

This is a backup / learning view, separate from the planned Pygame window.
``render``, ``status``, ``game_log`` and ``apply_command`` are pure functions
(game in, string out) so they can be tested; ``interactive`` is the loop
around them.

Layout
------
Vertices sit on the integer lattice from ``board.py``. Each lattice column
is 4 characters wide. Lattice rows repeat in groups of three (two rows of
corners, then a row of hex centres), and each group takes 4 text lines: the
extra line holds the ``/`` and ``\\`` edges between the two corner rows.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from src.board import HIGH_PROBABILITY_NUMBERS
from src.game import Game, Move

# ANSI colour codes. Colour is optional: every state also has a text marker.
PLAYER_COLORS = {"A": "1;91", "B": "1;94", "C": "1;92", "D": "1;95"}
BLOCKED_COLOR = "90"
HIGH_NUMBER_COLOR = "1;93"  # gold; must differ from every player colour

HELP = (
    "Commands:  Enter = let the CPU move  |  22 = place on vertex 22 (your turn)  |  i 22 = inspect vertex 22\n"
    "           v = switch labels (IDs / values)  |  r = restart on the same board  |  q = quit"
)


def render(game: Game, labels: str = "ids", color: bool = False) -> str:
    """Draw the board as text.

    Each vertex shows a marker and a number: ``" 22"`` is legal, ``"x22"`` is
    blocked and ``"A22"`` is player A's settlement. The number is the vertex
    ID, or the vertex value when ``labels="values"``. Hex centres show the
    number token (``--`` for the desert).
    """
    board = game.board
    min_x = min(v.x for v in board.vertices)
    min_y = min(v.y for v in board.vertices)

    def column(x: int) -> int:
        return (x - min_x) * 4 + 1

    def line(y: int) -> int:
        group, offset = divmod(y - min_y, 3)
        return 4 * group + (0, 2, 3)[offset]

    height = line(max(v.y for v in board.vertices)) + 1
    width = column(max(v.x for v in board.vertices)) + 3
    grid = [[" "] * width for _ in range(height)]

    def put(row: int, col: int, text: str, code: str = "") -> None:
        painted = f"\033[{code}m{text}\033[0m" if color and code else text
        grid[row][col : col + len(text)] = [painted] + [""] * (len(text) - 1)

    for a, b in board.edges():
        upper, lower = sorted((board.vertices[a], board.vertices[b]), key=lambda v: v.y)
        if upper.x == lower.x:
            put(line(upper.y) + 1, column(upper.x) + 1, "|")
        elif lower.x > upper.x:
            put(line(upper.y) + 1, column(upper.x) + 3, "\\")
        else:
            put(line(upper.y) + 1, column(upper.x) - 1, "/")

    for h in board.hexes:
        top = board.vertices[h.corners[0]]  # the hex centre is 2 lattice rows below its top corner
        text = "--" if h.number is None else str(h.number)
        code = HIGH_NUMBER_COLOR if h.number in HIGH_PROBABILITY_NUMBERS else ""
        put(line(top.y + 2), column(top.x), f"{text:^3}", code)

    for v in board.vertices:
        owner = game.owner.get(v.id)
        shown = board.vertex_value(v.id) if labels == "values" else v.id
        if owner:
            marker, code = owner, PLAYER_COLORS.get(owner, "1")
        elif v.id in game.blocked:
            marker, code = "x", BLOCKED_COLOR
        else:
            marker, code = " ", ""
        put(line(v.y), column(v.x), f"{marker}{shown:>2}", code)

    return "\n".join("".join(row).rstrip() for row in grid)


def _kind(game: Game, name: str) -> str:
    strategy = game.players[name].strategy
    return "human" if strategy is None else f"{strategy.name} CPU"


def _result(game: Game) -> str:
    winners = game.winners()
    if len(winners) == 1:
        return f"Winner: player {winners[0]}"
    return "Tie for first: players " + ", ".join(winners)


def status(game: Game) -> str:
    """Whose turn it is, a legend, and each player's settlements and payoff."""
    board = game.board
    draft = f"Draft: {game.draft} ({' '.join(game.order)})"
    if game.is_over:
        turn = f"GAME OVER. {_result(game)}"
    else:
        name = game.current_player.name
        turn = f"Turn {len(game.moves) + 1} of {len(game.order)}: player {name} ({_kind(game, name)})"
    lines = [
        f"{draft}    {turn}",
        "",
        "Legend:   22 = legal    x22 = blocked    A22 = player A's settlement    -- = desert",
        "Weights:  2,12 = 1   3,11 = 2   4,10 = 3   5,9 = 4   6,8 = 5   desert = 0",
        "",
    ]
    for name, player in game.players.items():
        placed = " + ".join(f"vertex {v} ({board.vertex_value(v)})" for v in player.settlements)
        lines.append(
            f"Player {name} ({_kind(game, name)}): {placed or 'no settlements'}  ->  payoff {player.payoff(board)}"
        )
    lines.append(f"Legal vertices left: {len(game.legal_vertices())} of {len(board.vertices)}")
    return "\n".join(lines)


def describe_vertex(game: Game, vertex: int) -> str:
    """Explain a vertex: the tiles it touches, its value, its neighbours and its state."""
    board = game.board
    if not 0 <= vertex < len(board.vertices):
        return f"{vertex} is not a vertex ID (0-{len(board.vertices) - 1})"
    v = board.vertices[vertex]
    tiles = [board.hexes[h] for h in v.hexes]
    numbers = ", ".join("desert" if t.number is None else str(t.number) for t in tiles)
    weights = " + ".join(str(t.weight) for t in tiles)
    if vertex in game.owner:
        state = f"occupied by player {game.owner[vertex]}"
    elif vertex in game.blocked:
        state = "blocked (next to a settlement)"
    else:
        state = "legal"
    return (
        f"Vertex {vertex} touches tiles {numbers}  ->  weights {weights} = value {board.vertex_value(vertex)}\n"
        f"  neighbours: {', '.join(map(str, v.neighbors))}   state: {state}"
    )


def describe_move(move: Move) -> str:
    """One line for a completed move."""
    return f"Turn {move.turn}: Player {move.player} chooses vertex {move.vertex} (value {move.value})"


def game_log(game: Game) -> str:
    """Every move so far, then the payoffs and the result if the game is over."""
    lines = [describe_move(m) for m in game.moves]
    if game.is_over:
        lines += ["", "Final payoffs:"]
        lines += [
            f"  {name}: {player.payoff(game.board):>2}   (vertices "
            + " + ".join(f"{v} = {game.board.vertex_value(v)}" for v in player.settlements)
            + ")"
            for name, player in game.players.items()
        ]
        lines += ["", _result(game)]
    return "\n".join(lines)


def apply_command(game: Game, command: str) -> str:
    """Run one typed command against the game and return the message to show.

    ``""`` (Enter) lets a CPU move, ``"22"`` places for the human whose turn
    it is, ``"a 22"`` places for a named human player, ``"i 22"`` inspects.
    """
    parts = command.replace(",", " ").split()
    if len(parts) == 2 and parts[0] == "i" and parts[1].isdigit():
        return describe_vertex(game, int(parts[1]))
    if game.is_over and len(parts) <= 2:
        return "The game is over.  r = play again on the same board,  q = quit."

    player = game.current_player
    if not parts:
        if player.strategy is None:
            return f"It is player {player.name}'s turn (human): type a vertex number to place."
        move = game.play_turn()
        return describe_move(move) + ".\n" + describe_vertex(game, move.vertex)

    if len(parts) == 1 and parts[0].isdigit():
        name, vertex = player.name, int(parts[0])
    elif len(parts) == 2 and parts[1].isdigit():
        name, vertex = parts[0].upper(), int(parts[1])
    else:
        return "Did not understand that.\n" + HELP

    if name in game.players and game.players[name].strategy is not None:
        return f"REJECTED: player {name} is a CPU; press Enter to let it move."
    try:
        game.place(name, vertex)
    except ValueError as error:  # includes IllegalPlacementError
        return f"REJECTED: {error}"
    return describe_move(game.moves[-1]) + ".\n" + describe_vertex(game, vertex)


def interactive(make_game: Callable[[], Game], title: str) -> None:
    """Interactive loop: redraw the board after every command.

    ``make_game`` builds a fresh game; it is called again on restart, so a
    seeded factory replays the identical game.
    """
    game = make_game()
    tty = sys.stdout.isatty()
    color = tty and "NO_COLOR" not in os.environ
    if color:
        os.system("")  # switches on ANSI colour support in the classic Windows console
    labels, message = "ids", HELP
    while True:
        if tty:
            os.system("cls" if os.name == "nt" else "clear")
        print(f"{title}  Vertex labels show: {labels}.\n")
        print(render(game, labels, color))
        print()
        print(status(game))
        print()
        print(message)
        try:
            command = input("> ").strip().lower()
        except EOFError:
            break
        if command in ("q", "quit", "exit"):
            break
        if command == "v":
            labels = "values" if labels == "ids" else "ids"
            message = f"Vertex labels now show {labels}."
        elif command == "r":
            game = make_game()
            message = "Restarted on the same board."
        else:
            message = apply_command(game, command)
