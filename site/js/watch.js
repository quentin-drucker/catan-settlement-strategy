// watch.js: the Watch page. Two CPU games on the same board, snake vs standard,
// stepped together one move at a time (Next) or automatically (Autoplay).
//
// Key parts:
//   start()     - new pair of games for the chosen seed + board type
//                 ("Catan: Classic Scenario" = rulebook token spiral; the seed only places the desert)
//   next()      - one CPU move in both games, then redraw
//   autoplay    - repeats next() on a timer until both games end
//   render()    - boards, scoreboards, move logs

import { loadEngine, randomSeed } from "./engine.js";
import { drawBoard, renderScores, describeMove, resultText } from "./board.js";

const DRAFTS = ["snake", "standard"];
const AUTOPLAY_MS = 1100;   // pause between automatic moves: slow enough to follow

const $ = (id) => document.getElementById(id);
const ui = {
  status: $("watch-status"),
  seedSource: $("watch-seed-source"),
  seed: $("watch-seed"),
  mode: $("watch-board"),
  next: $("watch-next"),
  auto: $("watch-auto"),
  restart: $("watch-restart"),
  newBoard: $("watch-new"),
};

let engine = null;
let board = null;                         // same board for both games
const states = { snake: null, standard: null };
let timer = null;                         // autoplay interval id (null = paused)

// Start a fresh pair of games from the seed + board type in the controls.
function start() {
  stopAutoplay();
  const seed = Math.max(0, parseInt(ui.seed.value, 10) || 0);
  ui.seed.value = seed;                   // show the seed actually used (e.g. "abc" -> 0)
  const classic = ui.seedSource.value === "classic";
  ui.mode.disabled = classic;             // the classic layout is fixed, so board type doesn't apply
  const mode = classic ? "classic" : ui.mode.value;
  for (const draft of DRAFTS) {
    const data = engine.newGame(draft, seed, mode, draft);
    board = data.board;
    states[draft] = data.state;
  }
  render();
}

// One move in both games. Same board + same tie-break seed -> both take the same
// spot each turn; only the player who gets it can differ.
function next() {
  if (states.snake.is_over) return;
  for (const draft of DRAFTS) states[draft] = engine.step(draft).state;
  render();
  if (states.snake.is_over) stopAutoplay();
}

function startAutoplay() {
  if (states.snake.is_over) start();      // Autoplay on a finished game replays it
  timer = setInterval(next, AUTOPLAY_MS);
  ui.auto.textContent = "Pause";
  ui.auto.setAttribute("aria-pressed", "true");
}

function stopAutoplay() {
  clearInterval(timer);
  timer = null;
  ui.auto.textContent = "Autoplay";
  ui.auto.setAttribute("aria-pressed", "false");
}

// Redraw both boards, their scoreboards and move logs.
function render() {
  for (const draft of DRAFTS) {
    const state = states[draft];
    drawBoard($(`board-${draft}`), board, state, { label: `${draft} draft board` });
    renderScores($(`scores-${draft}`), state, board);
    $(`turn-${draft}`).textContent = state.is_over
      ? `Game over. ${resultText(state)}`
      : `Turn ${state.moves.length + 1} of 8: player ${state.current} picks next`;
    const log = $(`log-${draft}`);
    log.replaceChildren(...state.moves.map((m) => {
      const li = document.createElement("li");
      li.textContent = describeMove(m);
      return li;
    }));
  }
  ui.next.disabled = states.snake.is_over;
}

// Wire up the controls, then load the engine and start the first game.
async function init() {
  ui.next.addEventListener("click", () => { stopAutoplay(); next(); });
  ui.auto.addEventListener("click", () => (timer ? stopAutoplay() : startAutoplay()));
  ui.restart.addEventListener("click", start);
  ui.newBoard.addEventListener("click", () => { ui.seed.value = randomSeed(); start(); });
  ui.mode.addEventListener("change", start);
  ui.seedSource.addEventListener("change", start);
  ui.seed.addEventListener("change", start);

  try {
    engine = await loadEngine();
  } catch (error) {
    ui.status.textContent = `The game engine could not load (${error.message}). Check the connection and reload the page.`;
    ui.status.classList.add("status--error");
    return;
  }
  document.querySelectorAll("[data-needs-engine]").forEach((el) => { el.disabled = false; });
  ui.status.hidden = true;
  start();
}

init();
