"""Catan-style board: hex tiles, settlement vertices and their adjacency graph.

Coordinate system
-----------------
Hexes use *axial* coordinates ``(q, r)`` with pointy-top orientation (``r``
grows downward). The standard board is every hex within distance 2 of the
centre hex, which produces rows of 3-4-5-4-3.

Vertex deduplication
--------------------
Neighbouring hexes share corners, so we must not create a new vertex for
every corner of every hex (that would give 19 * 6 = 114 "vertices" instead of
54). We place every corner on an *integer lattice*:

* the centre of hex ``(q, r)`` is lattice point ``(2q + r, 3r)``;
* its six corners are the centre plus the offsets in ``CORNER_OFFSETS``.

One lattice step is sqrt(3)/2 of a hex side horizontally and 1/2 of a hex side
vertically, so these really are the corners of regular hexagons -- but every
coordinate is an exact integer. Two hexes that share a corner compute exactly
the same integer pair for it, so deduplication is just a dictionary keyed on
``(x, y)``. No floating-point rounding is involved.

Vertex adjacency
----------------
Two settlement vertices are directly connected when they are consecutive
corners of some hex (i.e. they share a hex edge). Walking each hex's corners in
order and linking each corner to the next one finds every edge; storing the
links in sets removes the duplicates created by edges shared by two hexes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Number of ways (out of 36) to roll each total with two six-sided dice.
DICE_WEIGHTS: dict[int, int] = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}

# Standard Catan number-token multiset (18 tokens; the 19th tile is the desert).
NUMBER_TOKENS: tuple[int, ...] = (2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12)

HIGH_PROBABILITY_NUMBERS = frozenset({6, 8})

BOARD_MODES = ("random", "separated")

BOARD_RADIUS = 2

# Axial offsets to the six neighbouring hexes.
AXIAL_DIRECTIONS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))

# Lattice offsets from a hex centre to its corners, clockwise from the top corner.
CORNER_OFFSETS = ((0, -2), (1, -1), (1, 1), (0, 2), (-1, 1), (-1, -1))


class BoardGenerationError(RuntimeError):
    """Raised when a constrained board cannot be generated within the attempt limit."""


@dataclass(frozen=True)
class Hex:
    """A single hex tile.

    ``number`` is the dice-number token, or ``None`` for the desert.
    ``corners`` lists the six vertex IDs clockwise from the top corner.
    ``neighbors`` lists the IDs of adjacent hex tiles.
    """

    id: int
    q: int
    r: int
    number: int | None
    corners: tuple[int, ...]
    neighbors: tuple[int, ...]

    @property
    def weight(self) -> int:
        """Dice weight of this tile's number (0 for the desert)."""
        return DICE_WEIGHTS.get(self.number, 0)


@dataclass(frozen=True)
class Vertex:
    """A settlement location at a hex corner.

    ``(x, y)`` is the integer lattice position (see module docstring).
    ``hexes`` are the IDs of the 1-3 tiles touching this corner.
    ``neighbors`` are the IDs of directly connected settlement vertices.
    """

    id: int
    x: int
    y: int
    hexes: tuple[int, ...]
    neighbors: tuple[int, ...]


def standard_hex_coordinates() -> list[tuple[int, int]]:
    """Axial coordinates of the 19 standard hexes, in reading order (top row first)."""
    radius = BOARD_RADIUS
    return [
        (q, r)
        for r in range(-radius, radius + 1)
        for q in range(-radius, radius + 1)
        if abs(q + r) <= radius
    ]


def _corner_point(q: int, r: int, offset: tuple[int, int]) -> tuple[int, int]:
    return (2 * q + r + offset[0], 3 * r + offset[1])


class Board:
    """The standard 19-hex board with a fixed number assignment.

    ``numbers[i]`` is the token on hex ``i`` (``None`` for the desert). Hex IDs
    and vertex IDs are both assigned in reading order (top to bottom, then
    left to right), so they are identical for every board; only the numbers
    differ between generated boards.
    """

    def __init__(self, numbers: list[int | None] | tuple[int | None, ...]):
        coords = standard_hex_coordinates()
        if len(numbers) != len(coords):
            raise ValueError(f"expected {len(coords)} numbers, got {len(numbers)}")
        for n in numbers:
            if n is not None and n not in DICE_WEIGHTS:
                raise ValueError(f"invalid number token: {n!r}")

        # Deduplicate corners: identical lattice points are the same vertex.
        points = sorted(
            {_corner_point(q, r, off) for q, r in coords for off in CORNER_OFFSETS},
            key=lambda p: (p[1], p[0]),
        )
        vertex_id = {p: i for i, p in enumerate(points)}
        hex_id = {c: i for i, c in enumerate(coords)}

        vertex_hexes: list[list[int]] = [[] for _ in points]
        vertex_neighbors: list[set[int]] = [set() for _ in points]
        self.hexes: list[Hex] = []
        for i, (q, r) in enumerate(coords):
            corners = tuple(vertex_id[_corner_point(q, r, off)] for off in CORNER_OFFSETS)
            for k, v in enumerate(corners):
                vertex_hexes[v].append(i)
                nxt = corners[(k + 1) % 6]
                vertex_neighbors[v].add(nxt)
                vertex_neighbors[nxt].add(v)
            neighbors = tuple(
                hex_id[(q + dq, r + dr)] for dq, dr in AXIAL_DIRECTIONS if (q + dq, r + dr) in hex_id
            )
            self.hexes.append(Hex(i, q, r, numbers[i], corners, neighbors))

        self.vertices: list[Vertex] = [
            Vertex(v, x, y, tuple(vertex_hexes[v]), tuple(sorted(vertex_neighbors[v])))
            for v, (x, y) in enumerate(points)
        ]
        self._values = [sum(self.hexes[h].weight for h in v.hexes) for v in self.vertices]

    @property
    def numbers(self) -> list[int | None]:
        """The number token on each hex, indexed by hex ID."""
        return [h.number for h in self.hexes]

    def vertex_value(self, vertex_id: int) -> int:
        """Sum of the dice weights of the tiles touching a vertex (desert counts 0)."""
        return self._values[vertex_id]

    def edges(self) -> set[tuple[int, int]]:
        """All vertex-to-vertex connections as ``(smaller_id, larger_id)`` pairs."""
        return {(v.id, n) for v in self.vertices for n in v.neighbors if v.id < n}

    def has_adjacent_high_numbers(self) -> bool:
        """True if any 6 or 8 tile touches another 6 or 8 tile."""
        return any(
            h.number in HIGH_PROBABILITY_NUMBERS
            and any(self.hexes[n].number in HIGH_PROBABILITY_NUMBERS for n in h.neighbors)
            for h in self.hexes
        )


def generate_board(seed: int | None = None, mode: str = "random", max_attempts: int = 1000) -> Board:
    """Generate a board with the standard tokens and one desert on random hexes.

    ``mode="random"`` shuffles all 19 tiles freely. ``mode="separated"`` uses
    rejection sampling: reshuffle until no 6/8 tile is adjacent to another
    6/8 tile, giving up with ``BoardGenerationError`` after ``max_attempts``.
    The result depends only on ``seed`` and ``mode``, so a board can always be
    regenerated from them.
    """
    if mode not in BOARD_MODES:
        raise ValueError(f"unknown board mode {mode!r}; expected one of {BOARD_MODES}")
    rng = random.Random(seed)
    tiles: list[int | None] = [*NUMBER_TOKENS, None]
    for _ in range(max_attempts):
        rng.shuffle(tiles)
        board = Board(tiles)
        if mode == "random" or not board.has_adjacent_high_numbers():
            return board
    raise BoardGenerationError(
        f"could not generate a {mode!r} board in {max_attempts} attempts (seed={seed})"
    )
