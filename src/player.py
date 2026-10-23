"""A player: their name, who makes their moves (CPU or human), and their settlements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.board import Board

# Only needed for type hints. Importing it for real would be circular
# (strategies -> game -> player -> strategies).
if TYPE_CHECKING:
    from src.strategies import Strategy


@dataclass
class Player:
    """One seat in the draft (A, B, C or D).

    - ``strategy``: the CPU strategy that picks this player's moves; ``None`` = a human picks
    - ``settlements``: vertex IDs this player owns, in the order they were placed
    """

    name: str
    strategy: Strategy | None = None
    settlements: list[int] = field(default_factory=list)  # new empty list per player

    def payoff(self, board: Board) -> int:
        """Utility = sum of the values of this player's settlements."""
        return sum(board.vertex_value(v) for v in self.settlements)
