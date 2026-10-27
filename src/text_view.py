"""Terminal (text) view of the board + the interactive play loop.

- Backup / learning view. The main visual is the planned project website (Issue #5).
- ``render``, ``status``, ``describe_*``, ``game_log``, ``apply_command`` = pure
  functions (game in, text out) -> easy to test.
- ``interactive`` = the loop that prints them and reads commands.
- No game rules live here; everything goes through ``Game``.

How the drawing is laid out:
- Vertices use the integer lattice from ``board.py``.
- 1 lattice column = 4 characters wide.
- Lattice rows come in groups of 3 (2 rows of corners, then a row of hex
  centres). Each group takes 4 text lines; the extra line holds the ``/`` and
  ``\\`` edges between the two corner rows.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from src.board import HIGH_PROBABILITY_NUMBERS
from src.game import Game, Move

# ANSI colour codes (terminal text colours). Colour is extra: every state also
# has a text marker, so the board still reads fine without colour.
PLAYER_COLORS = {"A": "1;91", "B": "1;94", "C": "1;92", "D": "1;95"}  # red, blue, green, magenta
BLOCKED_COLOR = "90"  # grey
HIGH_NUMBER_COLOR = "1;93"  # gold for 6s and 8s; must differ from every player colour

# Shown at the start and whenever a command isn't understood.
HELP = (
    "Commands:  Enter = let the CPU move  |  22 = place on vertex 22 (your turn)  |  i 22 = inspect vertex 22\n"
    "           v = switch labels (IDs / values)  |  r = restart on the same board  |  q = quit"
)


def render(game: Game, labels: str = "ids", color: bool = False) -> str:
    """Draw the board as text (a honeycomb of numbers and edges).

    - Vertex labels: ``" 22"`` = legal, ``"x22"`` = blocked, ``"A22"`` = player A's settlement.
    - The number is the vertex ID, or the vertex value if ``labels="values"``.
    - Hex centres show the number token (``--`` = desert).
    - ``color=True`` adds ANSI colour codes around the labels.
    """
    board = game.board
    min_x = min(v.x for v in board.vertices)
    min_y = min(v.y for v in board.vertices)

    def column(x: int) -> int:
        """Text column for lattice x (4 chars per step, +1 margin for a "/" on the left)."""
        return (x - min_x) * 4 + 1

    def line(y: int) -> int:
        """Text line for lattice y: each group of 3 lattice rows -> 4 text lines."""
        group, offset = divmod(y - min_y, 3)
        return 4 * group + (0, 2, 3)[offset]

    height = line(max(v.y for v in board.vertices)) + 1
    width = column(max(v.x for v in board.vertices)) + 3
    grid = [[" "] * width for _ in range(height)]  # one string per character cell

    def put(row: int, col: int, text: str, code: str = "") -> None:
        """Write text into the grid at (row, col), optionally coloured."""
        painted = f"\033[{code}m{text}\033[0m" if color and code else text
        # Whole (coloured) text goes in the first cell; the cells it covers become "".
        grid[row][col : col + len(text)] = [painted] + [""] * (len(text) - 1)

    # Edges: same x -> vertical "|"; otherwise a diagonal "\" or "/" on the in-between line.
    for a, b in board.edges():
        upper, lower = sorted((board.vertices[a], board.vertices[b]), key=lambda v: v.y)
        if upper.x == lower.x:
            put(line(upper.y) + 1, column(upper.x) + 1, "|")
        elif lower.x > upper.x:
            put(line(upper.y) + 1, column(upper.x) + 3, "\\")
        else:
            put(line(upper.y) + 1, column(upper.x) - 1, "/")

    # Hex numbers, centred under each hex's top corner.
    for h in board.hexes:
        top = board.vertices[h.corners[0]]  # the hex centre is 2 lattice rows below its top corner
        text = "--" if h.number is None else str(h.number)
        code = HIGH_NUMBER_COLOR if h.number in HIGH_PROBABILITY_NUMBERS else ""
        put(line(top.y + 2), column(top.x), f"{text:^3}", code)

    # Vertex labels: marker (owner letter / "x" / space) + ID or value.
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
    """"human" or "<strategy> CPU", e.g. "greedy CPU"."""
    strategy = game.players[name].strategy
    return "human" if strategy is None else f"{strategy.name} CPU"


def _result(game: Game) -> str:
    """"Winner: player X" or "Tie for first: players X, Y"."""
    winners = game.winners()
    if len(winners) == 1:
        return f"Winner: player {winners[0]}"
    return "Tie for first: players " + ", ".join(winners)


def status(game: Game) -> str:
    """Panel under the board: draft + whose turn, legend, each player's settlements and payoff."""
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
    """Explain one vertex: tiles touched, how its value adds up, neighbours, and legal/blocked/occupied."""
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
    """One line per move, e.g. "Turn 1: Player A chooses vertex 22 (value 12)"."""
    return f"Turn {move.turn}: Player {move.player} chooses vertex {move.vertex} (value {move.value})"


def game_log(game: Game) -> str:
    """All moves so far; once the game is over, also the final payoffs and the winner."""
    lines = [describe_move(m) for m in game.moves]
    if game.is_over:
        lines += ["", "Final payoffs:"]
        # e.g. "  A: 20   (vertices 22 = 12 + 25 = 8)"
        lines += [
            f"  {name}: {player.payoff(game.board):>2}   (vertices "
            + " + ".join(f"{v} = {game.board.vertex_value(v)}" for v in player.settlements)
            + ")"
            for name, player in game.players.items()
        ]
        lines += ["", _result(game)]
    return "\n".join(lines)


def apply_command(game: Game, command: str) -> str:
    """Run one typed command and return the message to show under the board.

    - ``""`` (Enter): the current CPU moves (or a reminder if it's a human's turn)
    - ``"22"``: place on vertex 22 for the human whose turn it is
    - ``"a 22"``: same, naming the player (still has to be their turn)
    - ``"i 22"``: inspect vertex 22 (works any time)
    - Illegal moves come back as "REJECTED: <reason>" and change nothing.
    """
    parts = command.replace(",", " ").split()
    if len(parts) == 2 and parts[0] == "i" and parts[1].isdigit():
        return describe_vertex(game, int(parts[1]))
    if game.is_over and len(parts) <= 2:
        return "The game is over.  r = play again on the same board,  q = quit."

    player = game.current_player
    if not parts:  # Enter on its own
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

    # A person can't make a CPU's move for it.
    if name in game.players and game.players[name].strategy is not None:
        return f"REJECTED: player {name} is a CPU; press Enter to let it move."
    try:
        game.place(name, vertex)
    except ValueError as error:  # includes IllegalPlacementError
        return f"REJECTED: {error}"
    return describe_move(game.moves[-1]) + ".\n" + describe_vertex(game, vertex)


def interactive(make_game: Callable[[], Game], title: str) -> None:
    """Loop: clear the screen, draw board + panel + last message, read a command, repeat.

    - ``make_game``: function that builds a fresh game. Called again on "r", so a
      seeded game replays exactly.
    - Colour and screen clearing only happen in a real terminal (not when output is piped).
    """
    game = make_game()
    tty = sys.stdout.isatty()  # True in a real terminal, False when piped/redirected
    color = tty and "NO_COLOR" not in os.environ  # NO_COLOR = common opt-out for coloured output
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
        except EOFError:  # input ran out (e.g. piped commands) -> stop
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
