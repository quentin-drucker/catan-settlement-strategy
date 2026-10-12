"""A player and the settlements they own."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.board import Board


@dataclass
class Player:
    """One participant in the draft.

    ``settlements`` holds the vertex IDs of this player's settlements in the
    order they were placed.
    """

    name: str
    settlements: list[int] = field(default_factory=list)

    def payoff(self, board: Board) -> int:
        """Total utility: the sum of the values of this player's settlements."""
        return sum(board.vertex_value(v) for v in self.settlements)
