"""Command-line entry point: ``python main.py <command> [options]``.

Commands:
- ``play``: four greedy CPUs play one game -> prints the final board, turn log, payoffs.
  - ``--step``: show the board after every move instead (Enter = next move)
  - ``--human A``: play seat A in the terminal (``--human AC`` = two seats)
- ``explore``: same terminal view, but all four seats are human.
- ``experiments``: simulate all 4 setups (snake/standard x separated/random boards),
  then write ``results/summary.md`` + charts. ``--games N`` per setup (default 10,000).

Options for play/explore:
    --seed N                     same seed -> same board and game (default: random, printed)
    --board separated|random|classic  separated (default) = no 6/8 next to another 6/8;
                                 classic = rulebook lettered spiral, seed places the desert
    --draft snake|standard       snake (default) = A B C D D C B A
"""

import argparse
import random
import sys

from src.analysis import run_experiments
from src.board import BOARD_MODES
from src.game import DRAFT_FORMATS, PLAYER_NAMES, new_game
from src.text_view import game_log, interactive, render


def main() -> None:
    """Read the command-line options, then run the chosen command."""
    parser = argparse.ArgumentParser(description="Catan settlement-strategy project.")
    # Options shared by both commands (added to each through parents=[common]).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=None, help="game seed (default: random)")
    common.add_argument("--board", choices=BOARD_MODES, default="separated", help="board-generation mode (default: separated)")
    common.add_argument("--draft", choices=DRAFT_FORMATS, default="snake", help="draft order (default: snake)")
    commands = parser.add_subparsers(dest="command", required=True)

    play_parser = commands.add_parser("play", parents=[common], help="play a full game with greedy CPUs")
    play_parser.add_argument("--step", action="store_true", help="show the board after every move")
    play_parser.add_argument("--human", type=str.upper, default="", metavar="SEATS", help="seats you play, e.g. A or AC")
    commands.add_parser("explore", parents=[common], help="place every settlement by hand (all seats human)")
    exp_parser = commands.add_parser("experiments", help="simulate all setups and write the report + charts")
    exp_parser.add_argument("--games", type=int, default=10_000, help="games per setup (default: 10000)")
    exp_parser.add_argument("--seed", type=int, default=0, help="first seed; game i uses seed + i (default: 0)")
    exp_parser.add_argument("--out", default="results", help="output folder (default: results)")

    args = parser.parse_args()
    if args.command == "experiments":
        print(f"Running 4 setups x {args.games:,} games (seeds {args.seed}-{args.seed + args.games - 1})...")
        run_experiments(args.games, args.seed, args.out)
        print(f"Done: report in {args.out}/summary.md, charts in {args.out}/*.png, raw CSVs in {args.out}/raw/")
        return

    # No seed given -> pick one, so it can be printed and the game replayed later.
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    humans = "".join(PLAYER_NAMES) if args.command == "explore" else args.human
    if not set(humans) <= set(PLAYER_NAMES):
        parser.error(f"--human must only contain seats {', '.join(PLAYER_NAMES)}")

    title = f"Seed {seed}, board '{args.board}', draft '{args.draft}'."
    # Anything interactive -> terminal loop. The lambda rebuilds the same game on restart.
    if args.command == "explore" or args.step or humans:
        interactive(lambda: new_game(seed, args.board, args.draft, humans), title)
        return

    # Plain "play": run the whole game, then print it once.
    game = new_game(seed, args.board, args.draft)
    game.play()
    print(title + "\n")
    print(render(game, color=sys.stdout.isatty()))
    print()
    print(game_log(game))


if __name__ == "__main__":
    main()
