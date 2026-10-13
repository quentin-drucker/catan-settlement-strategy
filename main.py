"""Command-line entry point.

Usage:
    python main.py explore [--seed N] [--board random|separated]
"""

import argparse
import random

from src.board import BOARD_MODES
from src.text_view import explore


def main() -> None:
    parser = argparse.ArgumentParser(description="Catan settlement-strategy project.")
    commands = parser.add_subparsers(dest="command", required=True)

    explore_parser = commands.add_parser(
        "explore", help="show a board in the terminal and place settlements by hand"
    )
    explore_parser.add_argument("--seed", type=int, default=None, help="board seed (default: random)")
    explore_parser.add_argument("--board", choices=BOARD_MODES, default="random", help="board-generation mode")

    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    explore(seed, args.board)


if __name__ == "__main__":
    main()
