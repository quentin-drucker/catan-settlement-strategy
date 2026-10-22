"""Game controller for the settlement draft: turn order, placement rules, payoffs.

Turn order
----------
``draft_order`` turns the player list into the sequence of turns:

* snake:    A B C D D C B A
* standard: A B C D A B C D

Each player appears twice, so the game ends after 2 settlements per player
(8 placements for 4 players).

Placement rule
--------------
The Catan "distance rule" is enforced on the board's vertex graph: a
settlement may not go on an occupied vertex or on a vertex directly
connected to an occupied one. The game tracks this with two structures:

* ``owner``   -- maps each occupied vertex to the name of the player on it;
* ``blocked`` -- every vertex that can no longer be chosen: the occupied
  vertices plus all of their neighbours.

A vertex is legal exactly when it is a real vertex ID and not in ``blocked``,
so the legality check is a single set lookup.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.board import Board, generate_board
from src.player import Player
from src.strategies import GreedyStrategy, Strategy

PLAYER_NAMES = ("A", "B", "C", "D")
DRAFT_FORMATS = ("snake", "standard")


class IllegalPlacementError(ValueError):
    """Raised when a settlement placement breaks the rules."""


@dataclass(frozen=True)
class Move:
    """One completed placement. ``turn`` counts from 1."""

    turn: int
    player: str
    vertex: int
    value: int


def draft_order(players: tuple[str, ...], draft: str) -> list[str]:
    """The sequence of turns for a draft format: each player gets two turns."""
    if draft == "snake":
        return [*players, *reversed(players)]
    if draft == "standard":
        return [*players, *players]
    raise ValueError(f"unknown draft {draft!r}; expected one of {DRAFT_FORMATS}")


class Game:
    """A board, the players, whose turn it is, and the settlements placed so far.

    ``strategies`` maps each player name to its CPU strategy, or ``None`` for a
    human. By default all four players A-D are human (moves come from ``place``).
    """

    def __init__(
        self,
        board: Board,
        strategies: dict[str, Strategy | None] | None = None,
        draft: str = "snake",
    ):
        if strategies is None:
            strategies = dict.fromkeys(PLAYER_NAMES)
        self.board = board
        self.draft = draft
        self.players: dict[str, Player] = {name: Player(name, s) for name, s in strategies.items()}
        self.order = draft_order(tuple(self.players), draft)
        self.owner: dict[int, str] = {}
        self.blocked: set[int] = set()
        self.moves: list[Move] = []

    @property
    def is_over(self) -> bool:
        """True once every turn in the draft order has been played."""
        return len(self.moves) == len(self.order)

    @property
    def current_player(self) -> Player | None:
        """The player whose turn it is, or ``None`` when the game is over."""
        return None if self.is_over else self.players[self.order[len(self.moves)]]

    def is_legal(self, vertex: int) -> bool:
        """True if a settlement may currently be placed on ``vertex``."""
        return (
            isinstance(vertex, int)
            and 0 <= vertex < len(self.board.vertices)
            and vertex not in self.blocked
        )

    def legal_vertices(self) -> list[int]:
        """All currently legal vertex IDs, in increasing order."""
        return [v.id for v in self.board.vertices if v.id not in self.blocked]

    def place(self, player_name: str, vertex: int) -> int:
        """Place a settlement for a player and return the vertex's value.

        Raises ``IllegalPlacementError`` (leaving the game unchanged) if the
        game is over, it is not this player's turn, or the vertex is not a
        valid ID, is occupied, or is adjacent to a settlement.
        """
        if player_name not in self.players:
            raise ValueError(f"unknown player {player_name!r}")
        if self.is_over:
            raise IllegalPlacementError("the game is over")
        if player_name != self.current_player.name:
            raise IllegalPlacementError(
                f"it is player {self.current_player.name}'s turn, not player {player_name}'s"
            )
        if not self.is_legal(vertex):
            raise IllegalPlacementError(self._why_illegal(vertex))

        value = self.board.vertex_value(vertex)
        self.owner[vertex] = player_name
        self.blocked.add(vertex)
        self.blocked.update(self.board.vertices[vertex].neighbors)
        self.players[player_name].settlements.append(vertex)
        self.moves.append(Move(len(self.moves) + 1, player_name, vertex, value))
        return value

    def _why_illegal(self, vertex: int) -> str:
        """Human-readable reason an illegal vertex was rejected."""
        if not isinstance(vertex, int) or not 0 <= vertex < len(self.board.vertices):
            return f"{vertex!r} is not a vertex ID (0-{len(self.board.vertices) - 1})"
        if vertex in self.owner:
            return f"vertex {vertex} is already occupied by player {self.owner[vertex]}"
        neighbor = next(n for n in self.board.vertices[vertex].neighbors if n in self.owner)
        return (
            f"vertex {vertex} is adjacent to player {self.owner[neighbor]}'s "
            f"settlement on vertex {neighbor}"
        )

    def play_turn(self) -> Move:
        """Let the current CPU player choose, validate the choice, and return the move."""
        player = self.current_player
        if player is None:
            raise IllegalPlacementError("the game is over")
        if player.strategy is None:
            raise RuntimeError(f"player {player.name} is human; use place() for their move")
        self.place(player.name, player.strategy.choose(self))
        return self.moves[-1]

    def play(self) -> list[Move]:
        """Play CPU turns until the game ends and return all moves."""
        while not self.is_over:
            self.play_turn()
        return self.moves

    def payoffs(self) -> dict[str, int]:
        """Each player's total payoff from the settlements placed so far."""
        return {name: player.payoff(self.board) for name, player in self.players.items()}

    def winners(self) -> list[str]:
        """The player(s) with the highest payoff; more than one means a tie."""
        payoffs = self.payoffs()
        best = max(payoffs.values())
        return [name for name, p in payoffs.items() if p == best]


def new_game(
    seed: int,
    board_mode: str = "separated",
    draft: str = "snake",
    humans: str = "",
) -> Game:
    """Build a reproducible game: greedy CPUs in every seat not listed in ``humans``.

    The board comes from ``generate_board(seed, board_mode)`` and the CPUs share
    a tie-break RNG seeded with ``seed``. The board does not depend on the draft
    format, so the same seed gives the same board under snake and standard.
    """
    rng = random.Random(seed)
    strategies = {name: None if name in humans else GreedyStrategy(rng) for name in PLAYER_NAMES}
    return Game(generate_board(seed, board_mode), strategies, draft)
