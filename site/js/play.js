// play.js: the Play page. One human seat against three greedy computer players.
//
// Key parts:
//   newGame()   - start a game with the chosen seat, draft and board type
//                 ("Catan: Classic Scenario" = rulebook token spiral; the seed only places the desert)
//   runCpus()   - play CPU turns one by one with a short pause, until it's the human's turn
//   pick(spot)  - the human's move (validated by the Python engine)
//   render()    - board (open spots clickable on the human's turn), scores, log, status
//
// "generation" guards against an old CPU loop continuing after "New Game" was pressed.

import { loadEngine, randomSeed } from "./engine.js";
import { drawBoard, renderScores, describeMove, resultText } from "./board.js";

const KEY = "play";
const CPU_PAUSE_MS = 700;   // pause before each CPU move so it can be followed

const $ = (id) => document.getElementById(id);
const ui = {
  status: $("play-status"),
  seat: $("play-seat"),
  draft: $("play-draft"),
  mode: $("play-board"),
  seedSource: $("play-seed-source"),
  seed: $("play-seed"),
  values: $("play-values"),
  newGame: $("play-new"),
  board: $("play-board-svg"),
  scores: $("play-scores"),
  log: $("play-log"),
  turn: $("play-turn"),
};

let engine = null;
let board = null;
let state = null;
let settings = null;      // seat/draft/mode/seed of the running game
let generation = 0;
let busy = false;         // true while CPUs are moving (clicks ignored)

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function setStatus(text, kind = "") {
  ui.status.textContent = text;
  ui.status.className = `status wide${kind ? ` status--${kind}` : ""}`;
}

// Start a game: the seed box is used if filled in, otherwise a random seed.
function newGame() {
  generation += 1;
  ui.seed.value = ui.seed.value.trim() === "" ? randomSeed() : Math.max(0, parseInt(ui.seed.value, 10) || 0);
  const classic = ui.seedSource.value === "classic";
  ui.mode.disabled = classic;             // the classic layout is fixed, so board type doesn't apply
  settings = { seat: ui.seat.value, draft: ui.draft.value, mode: classic ? "classic" : ui.mode.value, seed: Number(ui.seed.value) };
  const data = engine.newGame(KEY, settings.seed, settings.mode, settings.draft, settings.seat);
  board = data.board;
  state = data.state;
  render();
  runCpus(generation);
}

// CPU turns until it's the human's turn or the game ends.
async function runCpus(gen) {
  busy = true;
  render();
  while (!state.is_over && !state.current_is_human) {
    setStatus(`Player ${state.current} (computer) is choosing...`);
    await sleep(CPU_PAUSE_MS);
    if (gen !== generation) return;           // a new game started meanwhile
    state = engine.step(KEY).state;
    render();
  }
  busy = false;
  if (state.is_over) {
    finish();
  } else {
    setStatus(`Your turn (player ${settings.seat}): pick one of the gold-ringed spots.`, "turn");
  }
  render();
}

// The human picks a spot. The engine checks the rules; a bad pick explains why.
function pick(spot) {
  if (busy || state.is_over || !state.current_is_human) return;
  const result = engine.place(KEY, spot);
  state = result.state;
  if (result.error) {
    setStatus(`Not allowed: ${result.error}. Pick a gold-ringed spot.`, "error");
    render();
    return;
  }
  // The board redraws after every move; keep keyboard focus on it so Tab leads
  // straight back to the open spots on the next turn (tabindex="-1" in the HTML).
  ui.board.focus({ preventScroll: true });
  runCpus(generation);
}

// End of game: your score vs what a greedy player would have scored in your seat.
function finish() {
  const you = state.players.find((p) => p.name === settings.seat).payoff;
  const greedy = engine.greedyPayoff(settings.seed, settings.mode, settings.draft, settings.seat);
  const compare = you > greedy ? "You beat it."
    : you === greedy ? "You matched it." : "Greedy would have done better here.";
  setStatus(`Game over. ${resultText(state)}. You scored ${you}; a greedy player in seat ${settings.seat} `
    + `would have scored ${greedy} on this board. ${compare}`);
}

function render() {
  const humanTurn = !busy && !state.is_over && state.current_is_human;
  drawBoard(ui.board, board, state, {
    clickable: humanTurn,
    onSpot: pick,
    showValues: ui.values.checked,
    label: humanTurn ? "Board: pick an open spot" : "Board",
  });
  renderScores(ui.scores, state, board);
  ui.turn.textContent = state.is_over
    ? `Seed ${settings.seed}, ${settings.draft} draft, ${settings.mode} board. Game over.`
    : `Seed ${settings.seed}, ${settings.draft} draft. Turn ${state.moves.length + 1} of 8: player ${state.current}`
      + (state.current_is_human ? " (you)" : "");
  ui.log.replaceChildren(...state.moves.map((m) => {
    const li = document.createElement("li");
    li.textContent = describeMove(m) + (m.player === settings.seat ? " (you)" : "");
    return li;
  }));
}

async function init() {
  ui.newGame.addEventListener("click", () => { ui.seed.value = ""; newGame(); });
  ui.values.addEventListener("change", () => state && render());
  for (const el of [ui.seat, ui.draft, ui.mode, ui.seedSource]) el.addEventListener("change", newGame);
  ui.seed.addEventListener("change", newGame);

  try {
    engine = await loadEngine();
  } catch (error) {
    setStatus(`The game engine could not load (${error.message}). Check the connection and reload the page.`, "error");
    return;
  }
  document.querySelectorAll("[data-needs-engine]").forEach((el) => { el.disabled = false; });
  newGame();
}

init();
