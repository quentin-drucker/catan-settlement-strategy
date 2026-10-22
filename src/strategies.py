"""CPU strategies: how a computer player picks its settlement.

A strategy only *chooses* a vertex. The game controller still validates the
choice through ``Game.place``, so a buggy strategy can never make an illegal
placement. New strategies (e.g. the blocking-aware CPU of Issue #6) subclass
``Strategy`` and implement ``choose``.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game import Game


class Strategy(ABC):
    """Interface for CPU players."""

    name: str

    @abstractmethod
    def choose(self, game: Game) -> int:
        """Return the vertex ID to settle on, given the current game state."""


class GreedyStrategy(Strategy):
    """Pick the legal vertex with the highest value right now.

    This is a heuristic that maximises immediate payoff. It ignores what its
    choice blocks and what opponents will do, so it is not an equilibrium
    strategy. Ties are broken uniformly at random with the given ``rng``, so a
    seeded ``rng`` makes every game reproducible.
    """

    name = "greedy"

    def __init__(self, rng: random.Random):
        self.rng = rng

    def choose(self, game: Game) -> int:
        legal = game.legal_vertices()
        best = max(game.board.vertex_value(v) for v in legal)
        return self.rng.choice([v for v in legal if game.board.vertex_value(v) == best])
