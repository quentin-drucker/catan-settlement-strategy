// engine.js: loads the real Python game engine into the browser.
//
// Pyodide = Python compiled to WebAssembly, so Python runs inside the web page
// with no server. This file:
//   1. downloads Pyodide from a CDN (~12 MB the first time; the browser caches it)
//   2. copies the engine files (src/*.py, deployed next to the pages) into
//      Pyodide's in-memory file system
//   3. imports src/web.py and wraps its functions so pages get plain JS objects
// Same seed -> same board and same CPU moves as `python main.py play`.

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const ENGINE_FILES = ["__init__.py", "board.py", "player.py", "strategies.py", "game.py", "web.py"];
const HOME = "/home/pyodide";

let enginePromise = null; // loaded once per page, shared by every caller

// Load the engine (only the first call does the work) and return an object with:
//   newGame(key, seed, boardMode, draft, humans) -> {board, state}
//   step(key)        -> {state}            one CPU move
//   place(key, spot) -> {state} or {error, state}
//   greedyPayoff(seed, boardMode, draft, seat) -> number
export function loadEngine() {
  if (!enginePromise) {
    enginePromise = (async () => {
      const { loadPyodide } = await import(`${PYODIDE_URL}pyodide.mjs`);
      const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

      // Engine files -> /home/pyodide/src/ so `import src.web` works like it does locally.
      pyodide.FS.mkdirTree(`${HOME}/src`);
      for (const name of ENGINE_FILES) {
        const response = await fetch(`src/${name}`);
        if (!response.ok) throw new Error(`could not load src/${name} (HTTP ${response.status})`);
        pyodide.FS.writeFile(`${HOME}/src/${name}`, await response.text());
      }
      pyodide.runPython(`import sys\nif "${HOME}" not in sys.path: sys.path.insert(0, "${HOME}")`);
      const web = pyodide.pyimport("src.web");

      // Python returns JSON text; parse it here so pages only see plain objects.
      return {
        newGame: (key, seed, boardMode, draft, humans = "") =>
          JSON.parse(web.new(key, seed, boardMode, draft, humans)),
        step: (key) => JSON.parse(web.step(key)),
        place: (key, spot) => JSON.parse(web.place(key, spot)),
        greedyPayoff: (seed, boardMode, draft, seat) => web.greedy_payoff(seed, boardMode, draft, seat),
      };
    })();
  }
  return enginePromise;
}

// A random seed for "new board" buttons (same range as main.py).
export function randomSeed() {
  return Math.floor(Math.random() * 1000000);
}
