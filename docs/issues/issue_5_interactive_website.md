# Issue #5: Interactive Board Visualization and Human Player Mode

**Status: Done**, as a website on GitHub Pages instead of a Pygame window.
Live: https://quentin-drucker.github.io/catan-settlement-strategy/

## What was done

| File | Purpose |
|---|---|
| `site/index.html` | Introduction (home page): background, what the model includes, scoring, method |
| `site/dashboard.html` | Dashboard: question + answer, token strip, headline numbers, cards to every page |
| `site/watch.html` + `site/js/watch.js` | Two computer games on the same board, snake vs standard, step by step |
| `site/play.html` + `site/js/play.js` | One human seat against three greedy computer players |
| `site/results.html`, `site/about.html` | Charts/tables from the 100,000-game runs; background and method |
| `site/js/engine.js` | Loads the Python engine into the browser (Pyodide) |
| `site/js/board.js` | Draws the board as SVG (tiles, tokens with pips, spots, house pieces) |
| `src/web.py` + `tests/test_web.py` | Bridge between the pages and the engine (JSON in/out) |
| `site/css/styles.css` | The only stylesheet ("Board-game box" style) |
| `site/build_site.py`, `.github/workflows/pages.yml` | Build `_site/` and publish it on every push to `main` |

How the game runs in the browser:
- Pyodide = Python compiled to WebAssembly, so Python runs inside the page with no server.
- `engine.js` downloads Pyodide (~12 MB the first time, then cached), copies `src/board.py`,
  `player.py`, `strategies.py`, `game.py` and `web.py` into it, and imports `src.web`.
- The pages call `web.new` / `web.step` / `web.place`; every call returns the full state as JSON,
  and `board.js` redraws from it. No game rules are written in JavaScript.
- Same seed -> same board as the command line. A computer-only game (Watch) also gives the same
  moves as `python main.py play --seed <seed>`.

## How to test it yourself

**Live site:** open the link above. First visit: the Watch/Play status line says the engine is
loading for a few seconds.

**Locally:**

```
python site/build_site.py
python -m http.server --directory _site
```

Open http://localhost:8000.

**Watch page**
- Seed 42, separated board, press **Next move** 8 times.
- Expected snake log: spots 22, 29, 39, 8, 40, 18, 7, 25 for A B C D D C B A.
- Standard takes the same spots for A B C D A B C D.
- Compare: `python main.py play --seed 42` and `python main.py play --seed 42 --draft standard`.
- **Autoplay** steps on its own and stops at the end; **Restart** replays; **New board** picks a random seed.

**Play page**
- Default: seat A, snake, separated board, random seed.
- Your turn: open spots get a gold ring; hover shows `Spot N: value V`; click one.
- Computer turns play out with a short pause; the status line says who is choosing.
- **Show spot values** writes each open spot's value on it.
- Keyboard: Tab through open spots on your turn, Enter or Space to pick.
- End: the status line gives the winner, your score, and what a greedy player would have scored in
  your seat on the same board.

**Automated tests**

```
python -m pytest
```

Expected: `139 passed` (6 for the bridge in `tests/test_web.py`).

## What the tests and checks cover

- Bridge: board + state JSON; stepping through the bridge matches the engine exactly; human picks
  apply; occupied/adjacent picks come back as errors and change nothing; a click on a computer's
  turn is refused; picks after the end are refused; `greedy_payoff` matches a full game.
- Browser (Playwright, headless Chromium):
  - Watch: 8 steps match the Python engine move for move; Autoplay finishes
  - Play: mouse and keyboard picks; focus returns to the board after each move
  - All 5 pages at 1280px and 390px: no console errors, no broken images, no sideways scrolling

## Notes

- With a human playing, computer moves can differ from a computer-only game on the same seed:
  the human's pick doesn't use the tie-break random numbers, so later ties break differently.
- Pygame was dropped in favour of the website (decision recorded in the plan, Step 5).
