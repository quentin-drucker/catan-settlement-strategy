"""A player and the settlements they own."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.board import Board

if TYPE_CHECKING:
    from src.strategies import Strategy


@dataclass
class Player:
    """One participant in the draft.

    ``strategy`` chooses this player's moves; ``None`` means a human chooses.
    ``settlements`` holds the vertex IDs of this player's settlements in the
    order they were placed.
    """

    name: str
    strategy: Strategy | None = None
    settlements: list[int] = field(default_factory=list)

    def payoff(self, board: Board) -> int:
        """Total utility: the sum of the values of this player's settlements."""
        return sum(board.vertex_value(v) for v in self.settlements)
