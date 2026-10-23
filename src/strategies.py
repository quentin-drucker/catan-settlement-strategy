"""CPU strategies: how a computer player picks its settlement.

- A strategy only *chooses* a vertex. ``Game.place`` still checks the choice,
  so even a buggy strategy can't make an illegal move.
- New strategies (e.g. a blocking-aware CPU for Issue #6) subclass ``Strategy``
  and write their own ``choose``. The game code doesn't need to change.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Only needed for type hints; a real import would be circular (game imports this file).
if TYPE_CHECKING:
    from src.game import Game


class Strategy(ABC):
    """Base class every CPU strategy follows: has a ``name``, implements ``choose``."""

    name: str  # short label shown in the terminal view, e.g. "greedy"

    @abstractmethod
    def choose(self, game: Game) -> int:
        """Return the vertex ID to settle on, given the current game state."""


class GreedyStrategy(Strategy):
    """Pick the legal vertex worth the most right now.

    - Heuristic: maximises the immediate payoff only. Ignores what the pick blocks
      and what opponents will do next -> NOT an equilibrium (game-theoretically
      optimal) strategy.
    - Ties: picks uniformly at random among the tied best vertices, using ``rng``.
      Seeded ``rng`` -> reproducible games.
    """

    name = "greedy"

    def __init__(self, rng: random.Random):
        self.rng = rng

    def choose(self, game: Game) -> int:
        """Best value among the legal vertices; random pick among ties. Doesn't change the game."""
        legal = game.legal_vertices()
        best = max(game.board.vertex_value(v) for v in legal)
        return self.rng.choice([v for v in legal if game.board.vertex_value(v) == best])
