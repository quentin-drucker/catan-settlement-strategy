"""Command-line entry point.

Usage:
    python main.py play    [--seed N] [--board separated|random] [--draft snake|standard] [--step] [--human SEATS]
    python main.py explore [--seed N] [--board separated|random] [--draft snake|standard]

``play`` runs a game with greedy CPUs and prints the result. ``--step`` shows
the board after every move (press Enter to advance); ``--human A`` lets you
play seat A yourself. ``explore`` is the same view with all four seats human.
"""

import argparse
import random
import sys

from src.board import BOARD_MODES
from src.game import DRAFT_FORMATS, PLAYER_NAMES, new_game
from src.text_view import game_log, interactive, render


def main() -> None:
    parser = argparse.ArgumentParser(description="Catan settlement-strategy project.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=None, help="game seed (default: random)")
    common.add_argument("--board", choices=BOARD_MODES, default="separated", help="board-generation mode (default: separated)")
    common.add_argument("--draft", choices=DRAFT_FORMATS, default="snake", help="draft order (default: snake)")
    commands = parser.add_subparsers(dest="command", required=True)

    play_parser = commands.add_parser("play", parents=[common], help="play a full game with greedy CPUs")
    play_parser.add_argument("--step", action="store_true", help="show the board after every move")
    play_parser.add_argument("--human", type=str.upper, default="", metavar="SEATS", help="seats you play, e.g. A or AC")
    commands.add_parser("explore", parents=[common], help="place every settlement by hand (all seats human)")

    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    humans = "".join(PLAYER_NAMES) if args.command == "explore" else args.human
    if not set(humans) <= set(PLAYER_NAMES):
        parser.error(f"--human must only contain seats {', '.join(PLAYER_NAMES)}")

    title = f"Seed {seed}, board '{args.board}', draft '{args.draft}'."
    if args.command == "explore" or args.step or humans:
        interactive(lambda: new_game(seed, args.board, args.draft, humans), title)
        return

    game = new_game(seed, args.board, args.draft)
    game.play()
    print(title + "\n")
    print(render(game, color=sys.stdout.isatty()))
    print()
    print(game_log(game))


if __name__ == "__main__":
    main()
