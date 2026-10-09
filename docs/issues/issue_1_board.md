# Issue #1: Hexagonal Board Representation and Settlement Vertices

**Status: Done.** All 24 tests pass.

## What was done

| File | Purpose |
|---|---|
| `src/board.py` | Board geometry, vertex graph, dice weights, board generation |
| `tests/test_board.py` | 24 automated tests |

- **19 hexes** in rows of 3-4-5-4-3, using axial coordinates `(q, r)`. Hex IDs 0–18 go
  in reading order (top row first, left to right).
- **54 settlement vertices** with IDs 0–53, also in reading order. The geometry is
  identical on every board; only the numbers move.
- **No duplicate corners.** Every corner gets exact whole-number coordinates (the hex
  centre is at `(2q + r, 3r)` plus a fixed offset per corner). Two hexes that share a
  corner compute the same coordinates for it, so merging duplicates is a dictionary
  lookup with no floating-point rounding. The module docstring explains this in detail.
- **Adjacency.** Each `Hex` stores its number, its 6 corner vertex IDs and its
  neighbouring hex IDs. Each `Vertex` stores the 1–3 hexes it touches and its 2–3
  neighbouring vertices. Two vertices are neighbours when they are consecutive corners
  of a hex, which gives 72 edges in total.
- **Scoring helper.** `board.vertex_value(v)` adds up the dice weights of the tiles a
  vertex touches (2→1, 3→2, …, 6/8→5, …, 12→1). The desert counts as 0.
- **Board generation.** `generate_board(seed, mode)`:
  - `"random"`: shuffles the 18 standard tokens plus the desert across the 19 hexes.
  - `"separated"`: reshuffles until no 6 or 8 touches another 6 or 8. After
    `max_attempts` (default 1000) it raises `BoardGenerationError` instead of looping
    forever. About 14% of random boards already qualify, so it takes ~7 tries.
  - The same `(seed, mode)` always gives the same board.

## How to test it yourself

Run these from the repository root.

**Run the automated tests:**

```
python -m pytest tests/test_board.py -v
```

You should see `24 passed`.

**Count hexes, vertices and edges:**

```
python -c "from src.board import generate_board; b = generate_board(seed=42); print(len(b.hexes), 'hexes,', len(b.vertices), 'vertices,', len(b.edges()), 'edges')"
```

Expected output: `19 hexes, 54 vertices, 72 edges`

**Print the board as text** (`--` is the desert):

```
python -c "from src.board import generate_board; b = generate_board(seed=42); [print(' ' * 3 * abs(r) + '  '.join(str(h.number or '--').rjust(4) for h in b.hexes if h.r == r)) for r in range(-2, 3)]"
```

Expected output for seed 42:

```
        10    10     4
      8     5    11    12
   5     9    11     8     3
      9     3    --     6
         6     2     4
```

Change `seed=42` to another number and you get a different board. Run the same seed
again and you get the same board.

**Inspect one vertex** (its hexes, their numbers, its value and its neighbours):

```
python -c "from src.board import generate_board; b = generate_board(seed=42); v = b.vertices[22]; print('vertex', v.id, 'touches hexes', v.hexes, 'with numbers', [b.hexes[h].number for h in v.hexes], '-> value', b.vertex_value(v.id), '| neighbors', v.neighbors)"
```

Expected output: `vertex 22 touches hexes (3, 7, 8) with numbers [8, 5, 9] -> value 13 | neighbors (16, 17, 28)`.
Check it by hand: 8 → 5, 5 → 4, 9 → 4, so 5 + 4 + 4 = 13.

**Compare the two generation modes:**

```
python -c "from src.board import generate_board; print('random:', generate_board(42, 'random').has_adjacent_high_numbers(), '| separated:', generate_board(42, 'separated').has_adjacent_high_numbers())"
```

Expected output: `random: True | separated: False`. In the seed-42 board printed above,
the 8 in the middle row sits directly above the 6.

## What the tests cover

- 19 hexes in rows of 3-4-5-4-3; 54 unique vertices; 72 edges
- 6 distinct corners per hex; hex→vertex and vertex→hex references agree
- Each vertex touches 1–3 hexes (18 touch one, 12 touch two, 24 touch three)
- Vertex neighbours point at each other, sit exactly one hex side apart, and share a hex edge
- Adjacent hexes share exactly 2 corners; non-adjacent hexes share none
- The dice weights equal the number of ways to roll each total out of 36
- The token set is preserved in both modes; exactly one desert
- The desert contributes 0; hand-checked scores (6+9+3 = 11, 2+4+12 = 5, 8+desert+5 = 9)
- The same seed gives the same board; different seeds give different boards
- Separated mode never puts a 6/8 next to a 6/8; random mode sometimes does
- Generation fails cleanly when attempts run out; invalid input is rejected

## Not included

No placement rules or players yet. Those belong to Issue #2.
