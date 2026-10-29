"""The board: 19 hex tiles, 54 settlement spots (vertices), and how they connect.

Key ideas:
- Hexes use axial coordinates ``(q, r)`` = a 2-number grid for hexes. Pointy-top
  hexes, ``r`` grows downward. Every hex within distance 2 of the centre ->
  rows of 3-4-5-4-3.
- Settlements go on hex corners (vertices), not on hexes.
- The geometry (IDs, positions, adjacency) is the same on every board. Only the
  number tokens move around between boards.

Vertex deduplication (why there are 54 vertices, not 114):
- Neighbouring hexes share corners. Making a new vertex for every corner of
  every hex would give 19 * 6 = 114 "vertices", with lots of duplicates.
- Fix: put every corner on an integer lattice (a grid of whole-number points).
  - centre of hex ``(q, r)`` -> lattice point ``(2q + r, 3r)``
  - its 6 corners -> centre + the offsets in ``CORNER_OFFSETS``
- One lattice step = sqrt(3)/2 of a hex side horizontally and 1/2 of a hex side
  vertically, so these really are the corners of regular hexagons, but with
  whole-number coordinates.
- Two hexes sharing a corner compute the exact same ``(x, y)`` for it ->
  deduplication is just a dict lookup. No floating-point rounding involved.

Vertex adjacency (which spots are "next to" each other):
- Two vertices are neighbours when they are consecutive corners of a hex,
  i.e. they share a hex edge.
- Walk each hex's corners in order and link each corner to the next one. Sets
  drop the duplicate links from edges that two hexes share.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Number of ways (out of 36) to roll each total with two dice. 7 is left out: no tile has it.
# e.g. 6 can be rolled 5 ways (1+5, 2+4, 3+3, 4+2, 5+1) -> weight 5.
DICE_WEIGHTS: dict[int, int] = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}

# The 18 standard Catan number tokens. The 19th tile is the desert (no number).
NUMBER_TOKENS: tuple[int, ...] = (2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12)

# The two most likely numbers (weight 5 each). "separated" boards keep these apart.
HIGH_PROBABILITY_NUMBERS = frozenset({6, 8})

# Board-generation modes: "random" = any layout, "separated" = no 6/8 next to another 6/8,
# "classic" = the rulebook's lettered tokens laid in a spiral (see CLASSIC_* below).
BOARD_MODES = ("random", "separated", "classic")

# Catan rulebook setup: tokens A-R (letter on the back) go out in alphabetical order,
# starting at a corner and spiralling counterclockwise towards the centre, skipping the desert.
CLASSIC_TOKENS: tuple[int, ...] = (5, 2, 6, 3, 8, 10, 9, 12, 11, 4, 8, 10, 9, 4, 5, 6, 3, 11)  # A-R
# Hex IDs in spiral order: outer ring counterclockwise from the top-left hex, then the
# inner ring the same way, then the centre.
CLASSIC_SPIRAL: tuple[int, ...] = (0, 3, 7, 12, 16, 17, 18, 15, 11, 6, 2, 1, 4, 8, 13, 14, 10, 5, 9)

# Hexes up to 2 steps from the centre -> the standard 19-hex board.
BOARD_RADIUS = 2

# Axial (q, r) offsets to the six neighbouring hexes.
AXIAL_DIRECTIONS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))

# Lattice offsets from a hex centre to its 6 corners, clockwise from the top corner.
CORNER_OFFSETS = ((0, -2), (1, -1), (1, 1), (0, 2), (-1, 1), (-1, -1))


class BoardGenerationError(RuntimeError):
    """Raised when a "separated" board can't be found within the attempt limit."""


@dataclass(frozen=True)
class Hex:
    """One hex tile.

    - ``id``: 0-18, in reading order (top row first, left to right)
    - ``q``, ``r``: axial coordinates
    - ``number``: dice-number token, or ``None`` for the desert
    - ``corners``: the 6 vertex IDs around it, clockwise from the top corner
    - ``neighbors``: IDs of the hexes touching it (3-6 of them)
    """

    id: int
    q: int
    r: int
    number: int | None
    corners: tuple[int, ...]
    neighbors: tuple[int, ...]

    @property
    def weight(self) -> int:
        """Dice weight of this tile's number (desert -> 0)."""
        return DICE_WEIGHTS.get(self.number, 0)


@dataclass(frozen=True)
class Vertex:
    """One settlement spot (a hex corner).

    - ``id``: 0-53, in reading order (top to bottom, left to right)
    - ``x``, ``y``: integer lattice position (see the file docstring)
    - ``hexes``: IDs of the 1-3 tiles touching this corner
    - ``neighbors``: IDs of the 2-3 vertices one edge away
    """

    id: int
    x: int
    y: int
    hexes: tuple[int, ...]
    neighbors: tuple[int, ...]


def standard_hex_coordinates() -> list[tuple[int, int]]:
    """Axial coordinates of the 19 standard hexes, in reading order (top row first)."""
    radius = BOARD_RADIUS
    # Keep (q, r) pairs within distance 2 of the centre. Looping r on the outside -> row by row.
    return [
        (q, r)
        for r in range(-radius, radius + 1)
        for q in range(-radius, radius + 1)
        if abs(q + r) <= radius
    ]


def _corner_point(q: int, r: int, offset: tuple[int, int]) -> tuple[int, int]:
    """Lattice point of one corner: hex centre (2q + r, 3r) + the corner's offset."""
    return (2 * q + r + offset[0], 3 * r + offset[1])


class Board:
    """The standard 19-hex board with one fixed set of number tokens.

    - ``numbers[i]`` = token on hex ``i`` (``None`` = desert)
    - ``hexes``: list of 19 ``Hex``, index = hex ID
    - ``vertices``: list of 54 ``Vertex``, index = vertex ID
    - Hex and vertex IDs are the same on every board; only the numbers differ.
    - Raises ``ValueError`` for the wrong number of tokens or a token that isn't 2-12 (no 7).
    """

    def __init__(self, numbers: list[int | None] | tuple[int | None, ...]):
        coords = standard_hex_coordinates()
        if len(numbers) != len(coords):
            raise ValueError(f"expected {len(coords)} numbers, got {len(numbers)}")
        for n in numbers:
            if n is not None and n not in DICE_WEIGHTS:
                raise ValueError(f"invalid number token: {n!r}")

        # Deduplicate corners: the set keeps each lattice point once. Sorting by (y, x)
        # numbers the vertices in reading order (top to bottom, left to right).
        points = sorted(
            {_corner_point(q, r, off) for q, r in coords for off in CORNER_OFFSETS},
            key=lambda p: (p[1], p[0]),
        )
        vertex_id = {p: i for i, p in enumerate(points)}  # lattice point -> vertex ID
        hex_id = {c: i for i, c in enumerate(coords)}  # (q, r) -> hex ID

        vertex_hexes: list[list[int]] = [[] for _ in points]  # vertex ID -> hexes touching it
        vertex_neighbors: list[set[int]] = [set() for _ in points]  # vertex ID -> neighbour IDs
        self.hexes: list[Hex] = []
        for i, (q, r) in enumerate(coords):
            corners = tuple(vertex_id[_corner_point(q, r, off)] for off in CORNER_OFFSETS)
            for k, v in enumerate(corners):
                vertex_hexes[v].append(i)
                # Consecutive corners share an edge -> link them both ways.
                nxt = corners[(k + 1) % 6]
                vertex_neighbors[v].add(nxt)
                vertex_neighbors[nxt].add(v)
            # Neighbouring hexes = the 6 axial directions that land on the board.
            neighbors = tuple(
                hex_id[(q + dq, r + dr)] for dq, dr in AXIAL_DIRECTIONS if (q + dq, r + dr) in hex_id
            )
            self.hexes.append(Hex(i, q, r, numbers[i], corners, neighbors))

        self.vertices: list[Vertex] = [
            Vertex(v, x, y, tuple(vertex_hexes[v]), tuple(sorted(vertex_neighbors[v])))
            for v, (x, y) in enumerate(points)
        ]
        # Vertex values are computed once here; the numbers never change after creation.
        self._values = [sum(self.hexes[h].weight for h in v.hexes) for v in self.vertices]

    @property
    def numbers(self) -> list[int | None]:
        """Number token on each hex, by hex ID (``None`` = desert)."""
        return [h.number for h in self.hexes]

    def vertex_value(self, vertex_id: int) -> int:
        """Value of a spot = sum of the dice weights of the tiles it touches (desert = 0).

        e.g. tiles 8, 5, 9 -> 5 + 4 + 4 = 13.
        """
        return self._values[vertex_id]

    def edges(self) -> set[tuple[int, int]]:
        """Every vertex-to-vertex connection once, as ``(smaller_id, larger_id)``. 72 in total."""
        return {(v.id, n) for v in self.vertices for n in v.neighbors if v.id < n}

    def has_adjacent_high_numbers(self) -> bool:
        """True if any 6 or 8 tile touches another 6 or 8 tile."""
        return any(
            h.number in HIGH_PROBABILITY_NUMBERS
            and any(self.hexes[n].number in HIGH_PROBABILITY_NUMBERS for n in h.neighbors)
            for h in self.hexes
        )


def generate_board(seed: int | None = None, mode: str = "separated", max_attempts: int = 1000) -> Board:
    """Make a board with the 18 standard tokens + 1 desert shuffled onto the 19 hexes.

    - ``mode="random"``: any shuffle is accepted.
    - ``mode="separated"`` (default): reshuffle until no 6/8 touches another 6/8
      (rejection sampling). Raises ``BoardGenerationError`` after ``max_attempts``
      instead of looping forever. ~14% of shuffles pass -> ~7 tries on average.
    - ``mode="classic"``: the seed only picks the desert tile; the tokens then follow
      the rulebook spiral (``classic_board``).
    - Same ``seed`` + ``mode`` -> same board every time.
    """
    if mode not in BOARD_MODES:
        raise ValueError(f"unknown board mode {mode!r}; expected one of {BOARD_MODES}")
    rng = random.Random(seed)
    if mode == "classic":
        return classic_board(rng.randrange(len(CLASSIC_SPIRAL)))
    tiles: list[int | None] = [*NUMBER_TOKENS, None]
    for _ in range(max_attempts):
        rng.shuffle(tiles)
        board = Board(tiles)
        if mode == "random" or not board.has_adjacent_high_numbers():
            return board
    raise BoardGenerationError(
        f"could not generate a {mode!r} board in {max_attempts} attempts (seed={seed})"
    )


def classic_board(desert: int = 9) -> Board:
    """Rulebook layout: tokens A-R along ``CLASSIC_SPIRAL``, skipping the ``desert`` hex.

    Desert in the centre (hex 9, the default) -> the rulebook's starting board.
    """
    if desert not in CLASSIC_SPIRAL:
        raise ValueError(f"desert must be a hex ID 0-18, got {desert!r}")
    numbers: list[int | None] = [None] * len(CLASSIC_SPIRAL)
    tokens = iter(CLASSIC_TOKENS)
    for hex_id in CLASSIC_SPIRAL:
        if hex_id != desert:
            numbers[hex_id] = next(tokens)
    return Board(numbers)
