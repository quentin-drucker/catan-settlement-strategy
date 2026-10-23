"""Game controller: turn order, placement rules, payoffs.

Turn order:
- ``draft_order`` turns the player list into the sequence of turns.
  - snake:    A B C D D C B A
  - standard: A B C D A B C D
- Each player shows up twice -> 2 settlements each -> 8 placements total.

Placement rule (Catan's "distance rule"):
- No settlement on an occupied vertex, or on a vertex right next to one.
- Tracked with two structures:
  - ``owner``: dict, occupied vertex -> name of the player on it
  - ``blocked``: set of vertices that can't be chosen anymore
    = occupied vertices + all their neighbours
- Legal = a real vertex ID that isn't in ``blocked`` -> a single set lookup.

Who moves:
- Each player has a strategy (CPU) or ``None`` (human).
- CPU turns go through ``play_turn()``; human turns call ``place()`` directly.
- Either way, ``place()`` checks every rule, so nothing illegal gets through.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.board import Board, generate_board
from src.player import Player
from src.strategies import GreedyStrategy, Strategy

PLAYER_NAMES = ("A", "B", "C", "D")  # seat names, in first-round order
DRAFT_FORMATS = ("snake", "standard")


class IllegalPlacementError(ValueError):
    """Raised when a placement breaks a rule (wrong turn, occupied, adjacent, bad ID, game over)."""


@dataclass(frozen=True)
class Move:
    """One finished placement: turn number (from 1), player, vertex, and the vertex's value."""

    turn: int
    player: str
    vertex: int
    value: int


def draft_order(players: tuple[str, ...], draft: str) -> list[str]:
    """Turn sequence for a draft format, e.g. snake -> A B C D D C B A.

    Raises ``ValueError`` for an unknown draft name.
    """
    if draft == "snake":
        return [*players, *reversed(players)]
    if draft == "standard":
        return [*players, *players]
    raise ValueError(f"unknown draft {draft!r}; expected one of {DRAFT_FORMATS}")


class Game:
    """One game: the board, the players, whose turn it is, and what's been placed.

    - ``strategies``: player name -> CPU strategy, or ``None`` for a human.
      Leave it out -> all four players A-D are human.
    - ``draft``: "snake" (default) or "standard".

    Main state:
    - ``players``: name -> ``Player``
    - ``order``: the full turn sequence, e.g. ``["A", "B", "C", "D", "D", "C", "B", "A"]``
    - ``owner`` / ``blocked``: see the file docstring
    - ``moves``: list of ``Move``, in order. Its length = number of turns played so far.
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
        """Player whose turn it is (``None`` once the game is over)."""
        # Number of moves so far = index of the next turn in the draft order.
        return None if self.is_over else self.players[self.order[len(self.moves)]]

    def is_legal(self, vertex: int) -> bool:
        """True if a settlement can go on ``vertex`` right now (ignores whose turn it is)."""
        return (
            isinstance(vertex, int)
            and 0 <= vertex < len(self.board.vertices)
            and vertex not in self.blocked
        )

    def legal_vertices(self) -> list[int]:
        """Every vertex that's currently legal, lowest ID first."""
        return [v.id for v in self.board.vertices if v.id not in self.blocked]

    def place(self, player_name: str, vertex: int) -> int:
        """Place a settlement for a player and return the vertex's value.

        Checks, in order: known player, game not over, this player's turn, legal vertex.
        - Unknown player -> ``ValueError``.
        - Any other failed check -> ``IllegalPlacementError`` saying why.
        - All checks run before anything changes -> a rejected move leaves the game untouched.
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
        # The new settlement blocks its own spot and every neighbouring spot.
        self.blocked.add(vertex)
        self.blocked.update(self.board.vertices[vertex].neighbors)
        self.players[player_name].settlements.append(vertex)
        self.moves.append(Move(len(self.moves) + 1, player_name, vertex, value))
        return value

    def _why_illegal(self, vertex: int) -> str:
        """Readable reason a vertex was rejected: bad ID, occupied, or next to a settlement."""
        if not isinstance(vertex, int) or not 0 <= vertex < len(self.board.vertices):
            return f"{vertex!r} is not a vertex ID (0-{len(self.board.vertices) - 1})"
        if vertex in self.owner:
            return f"vertex {vertex} is already occupied by player {self.owner[vertex]}"
        # Not occupied but blocked -> some neighbour must be occupied; name it.
        neighbor = next(n for n in self.board.vertices[vertex].neighbors if n in self.owner)
        return (
            f"vertex {vertex} is adjacent to player {self.owner[neighbor]}'s "
            f"settlement on vertex {neighbor}"
        )

    def play_turn(self) -> Move:
        """Let the current CPU pick a vertex, place it (with all the usual checks), return the move.

        Raises ``IllegalPlacementError`` if the game is over, ``RuntimeError`` if it's a human's turn.
        """
        player = self.current_player
        if player is None:
            raise IllegalPlacementError("the game is over")
        if player.strategy is None:
            raise RuntimeError(f"player {player.name} is human; use place() for their move")
        self.place(player.name, player.strategy.choose(self))
        return self.moves[-1]

    def play(self) -> list[Move]:
        """Play CPU turns until the game ends; return every move."""
        while not self.is_over:
            self.play_turn()
        return self.moves

    def payoffs(self) -> dict[str, int]:
        """Player name -> total payoff so far (sum of their settlement values)."""
        return {name: player.payoff(self.board) for name, player in self.players.items()}

    def winners(self) -> list[str]:
        """Player(s) with the highest payoff. More than one name = a tie."""
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

    - ``humans``: seats a person plays, e.g. ``"A"`` or ``"AC"``. Default: all CPUs.
    - Board = ``generate_board(seed, board_mode)``, so it doesn't depend on the draft
      -> same seed = same board under snake and standard (needed for fair comparisons).
    - All CPUs share one tie-break RNG seeded with ``seed`` -> same seed = identical game.
    """
    rng = random.Random(seed)
    strategies = {name: None if name in humans else GreedyStrategy(rng) for name in PLAYER_NAMES}
    return Game(generate_board(seed, board_mode), strategies, draft)
