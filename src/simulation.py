"""Batch simulations: play many CPU-only games and save the results to CSV.

- Game ``i`` uses seed ``base_seed + i`` -> any row can be replayed with
  ``python main.py play --seed <seed> --board <mode> --draft <draft>``.
- Board depends only on (seed, board mode), so snake and standard runs with the
  same seeds play on the *same boards* -> the draft order is the only difference.
- Rows are written as each game finishes (streamed), so 100,000+ games don't
  need to fit in memory.

CSV = one row per player per game. Columns:
- ``sim_id``: game number in this run (0, 1, 2, ...)
- ``seed``, ``board_mode``, ``draft``: everything needed to replay the game
- ``player``: seat A-D; ``strategy``: e.g. "greedy"
- ``settlement_1``/``value_1``: first pick (vertex ID, value); same for ``_2``
- ``payoff``: value_1 + value_2
- ``win_share``: 1 for an outright win, 1/k when k players tie for first, else 0
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.game import new_game

CSV_COLUMNS = [
    "sim_id", "seed", "board_mode", "draft", "player", "strategy",
    "settlement_1", "value_1", "settlement_2", "value_2", "payoff", "win_share",
]


def simulate(n_games: int, path: str | Path, base_seed: int = 0, board_mode: str = "separated", draft: str = "snake") -> Path:
    """Play ``n_games`` greedy-CPU games and write them to a CSV file at ``path``.

    Creates the parent folder if needed. Returns the path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for sim_id in range(n_games):
            seed = base_seed + sim_id
            game = new_game(seed, board_mode, draft)
            game.play()
            winners = game.winners()
            for name, player in game.players.items():
                v1, v2 = player.settlements
                writer.writerow([
                    sim_id, seed, board_mode, draft, name, player.strategy.name,
                    v1, game.board.vertex_value(v1), v2, game.board.vertex_value(v2),
                    player.payoff(game.board),
                    1 / len(winners) if name in winners else 0,
                ])
    return path
