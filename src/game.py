"""Game state for the settlement draft: placement rules and payoffs.

The placement rule (the Catan "distance rule") is enforced on the board's
vertex graph: a settlement may not go on an occupied vertex or on a vertex
directly connected to an occupied one. The game tracks this with two
structures:

* ``owner``   -- maps each occupied vertex to the name of the player on it;
* ``blocked`` -- every vertex that can no longer be chosen: the occupied
  vertices plus all of their neighbours.

A vertex is legal exactly when it is a real vertex ID and not in ``blocked``,
so the legality check is a single set lookup.
"""

from __future__ import annotations

from src.board import Board
from src.player import Player

PLAYER_NAMES = ("A", "B", "C", "D")


class IllegalPlacementError(ValueError):
    """Raised when a settlement placement breaks the rules."""


class Game:
    """A board plus the settlements placed on it so far."""

    def __init__(self, board: Board, player_names: tuple[str, ...] = PLAYER_NAMES):
        self.board = board
        self.players: dict[str, Player] = {name: Player(name) for name in player_names}
        self.owner: dict[int, str] = {}
        self.blocked: set[int] = set()

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
        vertex is not a valid ID, is occupied, or is adjacent to a settlement.
        """
        if player_name not in self.players:
            raise ValueError(f"unknown player {player_name!r}")
        if not self.is_legal(vertex):
            raise IllegalPlacementError(self._why_illegal(vertex))

        self.owner[vertex] = player_name
        self.blocked.add(vertex)
        self.blocked.update(self.board.vertices[vertex].neighbors)
        self.players[player_name].settlements.append(vertex)
        return self.board.vertex_value(vertex)

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

    def payoffs(self) -> dict[str, int]:
        """Each player's total payoff from the settlements placed so far."""
        return {name: player.payoff(self.board) for name, player in self.players.items()}
