// board.js: draws the game board as SVG, plus small shared helpers for the pages.
//
// SVG = a drawing made of shapes (polygons, circles, text) that the browser
// keeps sharp at any size. Every shape gets a .board__* class, so all colours
// come from styles.css; only animation timing (delays) is set here.
//
// Positions: vertices sit on the integer lattice from src/board.py.
// One lattice step = sqrt(3)/2 hex sides across and 1/2 hex side down, so with
// a hex side of 34px: x * 29.4, y * 17.
//
// Animations (keyframes in styles.css) play once per new board (tiles ripple in)
// and once per new move (tiles flash, house drops in, neighbours fade to blocked).
// The pages redraw the whole board often, so `memory` keeps when each started and
// a redraw resumes it (negative animation-delay) instead of replaying it.

const SVG_NS = "http://www.w3.org/2000/svg";
const STEP_X = 29.4;
const STEP_Y = 17;
const ANIM_MS = 1500;            // split ring: three 0.5s pulses
const memory = new WeakMap();    // <svg> -> { board, moves, blocked, boardAt, moveAt, newlyBlocked }

// Small helper: make an SVG element with attributes (and optional text).
function svgEl(tag, attrs = {}, text = null) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attrs)) el.setAttribute(name, value);
  if (text !== null) el.textContent = text;
  return el;
}

const pos = (v) => [v.x * STEP_X, v.y * STEP_Y];

// What changed since this <svg> was last drawn: a new board, a new move, or nothing.
// Returns ms since the board / newest move first appeared, and the newly blocked spots.
function timeline(svg, board, state) {
  const now = performance.now();
  const moves = state.moves.length;
  const blocked = new Set(state.blocked);
  const prev = memory.get(svg);
  let t = prev;
  if (!prev || prev.board !== board) {
    t = { board, moves, blocked, boardAt: now, moveAt: -Infinity, newlyBlocked: new Set() };
  } else if (moves > prev.moves) {
    const newlyBlocked = new Set([...blocked].filter((id) => !prev.blocked.has(id)));
    t = { ...prev, moves, blocked, moveAt: now, newlyBlocked };
  } else if (moves < prev.moves) {               // same board, fewer moves: nothing to animate
    t = { ...prev, moves, blocked, moveAt: -Infinity, newlyBlocked: new Set() };
  }
  memory.set(svg, t);
  return { sinceBoard: now - t.boardAt, sinceMove: now - t.moveAt, newlyBlocked: t.newlyBlocked };
}

// Start animation class `cls` (lasting `ms`) on `el`, `delay` ms after the event that
// happened `elapsed` ms ago; skipped once it would already be over.
function play(el, cls, delay, elapsed, ms) {
  if (elapsed > delay + ms) return;
  el.classList.add(cls);
  el.style.animationDelay = `${Math.round(delay - elapsed)}ms`;
}

// Draw `board` + `state` (from engine.js) into the <svg> element `svg`.
// options:
//   clickable  - open spots become buttons (Play page, human's turn)
//   onSpot(id) - called when an open spot is clicked or pressed with Enter/Space
//   showValues - write each open spot's value on it
//   split      - the newest move went to a different player on the other board (Watch)
//   label      - accessible name for the whole drawing
export function drawBoard(svg, board, state, options = {}) {
  const { clickable = false, onSpot = null, showValues = false, split = false, label = "Catan board" } = options;
  svg.replaceChildren();
  svg.setAttribute("viewBox", "-200 -175 400 350");
  svg.setAttribute("role", "group");
  svg.setAttribute("aria-label", label);
  svg.classList.add("board");

  const vertices = new Map(board.vertices.map((v) => [v.id, v]));
  const owner = state.owner;                       // {"22": "A", ...}
  const blocked = new Set(state.blocked);
  const newest = state.moves.at(-1);
  const lastMove = newest ? newest.vertex : null;
  const winners = new Set(state.winners);
  const { sinceBoard, sinceMove, newlyBlocked } = timeline(svg, board, state);
  const tilesAt = new Map();                       // spot id -> tile polygons around it

  // Sea: a flat-topped hexagon behind the island.
  const sea = [...Array(6)].map((_, k) => {
    const a = (Math.PI / 3) * k;
    return `${(190 * Math.cos(a)).toFixed(1)},${(190 * Math.sin(a)).toFixed(1)}`;
  });
  svg.append(svgEl("polygon", { class: "board__sea", points: sea.join(" ") }));

  // Hex centre = 2 lattice rows below its top corner. New board: tiles ripple out
  // from the middle of the island, each token popping in just after its tile.
  const centre = (h) => { const top = vertices.get(h.corners[0]); return [top.x * STEP_X, (top.y + 2) * STEP_Y]; };
  const rippleDelay = (h) => Math.hypot(...centre(h)) * 2.2;

  // Land tiles.
  for (const h of board.hexes) {
    const pts = h.corners.map((c) => pos(vertices.get(c)).map((n) => n.toFixed(1)).join(",")).join(" ");
    const tile = svgEl("polygon", { class: "board__tile", points: pts });
    play(tile, "board__tile--in", rippleDelay(h), sinceBoard, 450);
    for (const c of h.corners) tilesAt.set(c, [...(tilesAt.get(c) || []), tile]);
    svg.append(tile);
  }

  // New move: the tiles that pay the new settlement flash in the player's color.
  if (newest) {
    for (const tile of tilesAt.get(lastMove)) {
      tile.style.setProperty("--player", playerColor(newest.player));
      play(tile, "board__tile--flash", 0, sinceMove, 900);
    }
  }

  // Number tokens: disc + number + one pip per way to roll it (out of 36), grouped so they pop in together.
  for (const h of board.hexes) {
    if (h.number === null) continue;                // desert: no token
    const [cx, cy] = centre(h);
    const high = h.number === 6 || h.number === 8;
    const token = svgEl("g", { class: "board__token-group" });
    token.append(svgEl("circle", { class: "board__token", cx, cy, r: 14 }));
    token.append(svgEl("text", {
      class: `board__token-number${high ? " board__token-number--high" : ""}`, x: cx, y: cy + 3,
    }, String(h.number)));
    for (let i = 0; i < h.weight; i++) {
      const px = cx + (i - (h.weight - 1) / 2) * 3.4;
      token.append(svgEl("circle", { class: "board__pip", cx: px.toFixed(1), cy: cy + 8.5, r: 1.1 }));
    }
    play(token, "board__token-group--in", rippleDelay(h) + 180, sinceBoard, 400);
    svg.append(token);
  }

  // Spots: blocked dots, open spots (buttons when clickable), then settlements on top.
  for (const v of board.vertices) {
    if (String(v.id) in owner) continue;
    const [x, y] = pos(v);
    if (blocked.has(v.id)) {
      const dot = svgEl("circle", { class: "board__spot board__spot--blocked", cx: x, cy: y, r: 4.5 });
      if (newlyBlocked.has(v.id)) play(dot, "board__spot--fading", 250, sinceMove, 500);  // open -> blocked
      svg.append(dot);
      continue;
    }
    const r = showValues ? 8.5 : (clickable ? 6.5 : 4.5);
    const spot = svgEl("circle", { class: "board__spot", cx: x, cy: y, r });
    const group = svgEl("g");
    group.append(spot);
    if (showValues) {
      group.append(svgEl("text", { class: "board__spot-value", x, y: y + 3 }, String(v.value)));
    }
    group.append(svgEl("title", {}, `Spot ${v.id}: value ${v.value}`));  // hover tooltip
    if (clickable && onSpot) {
      // Open spot = a real button for mouse, touch and keyboard users. An invisible
      // larger circle underneath gives fingers a bigger target (spots are 34px apart).
      group.prepend(svgEl("circle", { class: "board__hit", cx: x, cy: y, r: 13 }));
      group.setAttribute("class", "board__spot-button");
      group.setAttribute("role", "button");
      group.setAttribute("tabindex", "0");
      group.setAttribute("aria-label", `Spot ${v.id}, value ${v.value}`);
      // Hover/focus lights the tiles this spot would collect from (value = their dice weights).
      const light = (on) => () => tilesAt.get(v.id).forEach((t) => t.classList.toggle("board__tile--lit", on));
      for (const name of ["mouseenter", "focus"]) group.addEventListener(name, light(true));
      for (const name of ["mouseleave", "blur"]) group.addEventListener(name, light(false));
      group.addEventListener("click", () => onSpot(v.id));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();               // Space would otherwise scroll the page
          onSpot(v.id);
        }
      });
    }
    play(group, "board__fade-in", 450, sinceBoard, 350);
    svg.append(group);
  }

  // Settlements: a house shape with the player's letter (letter = second cue besides colour).
  for (const [id, name] of Object.entries(owner)) {
    const [x, y] = pos(vertices.get(Number(id)));
    if (Number(id) === lastMove) {
      // Newest move. pathLength 98 = exactly 14 dash+gap repeats (4 + 3), so the turning ring has no seam.
      svg.append(svgEl("circle", { class: "board__last", cx: x, cy: y, r: 15, pathLength: 98 }));
      if (split && sinceMove < ANIM_MS) {
        const ring = svgEl("circle", { class: "board__split", cx: x, cy: y, r: 15 });
        play(ring, "board__split--on", 0, sinceMove, 1500);
        svg.append(ring);
      }
    }
    const house = [[0, -11], [9, -4], [9, 8], [-9, 8], [-9, -4]]
      .map(([dx, dy]) => `${(x + dx).toFixed(1)},${(y + dy).toFixed(1)}`).join(" ");
    const piece = svgEl("polygon", { class: `board__piece board__piece--${name.toLowerCase()}`, points: house });
    piece.append(svgEl("title", {}, `Player ${name}, spot ${id}`));
    // House + letter in one group so they animate as a unit: the newest drops in (.board__new);
    // at game end the winners' houses sway gently in an inner group (.board__winner).
    const group = svgEl("g");
    const body = winners.has(name) ? svgEl("g", { class: "board__winner" }) : group;
    body.style.setProperty("--player", playerColor(name));
    body.append(piece, svgEl("text", { class: "board__piece-label", x, y: y + 5 }, name));
    if (body !== group) group.append(body);
    if (Number(id) === lastMove) play(group, "board__new", 0, sinceMove, 450);
    svg.append(group);
  }
}

// The seat letter on its player color (same colors as the pieces), as HTML.
// `active` adds a soft pulse for the player whose turn it is.
export const playerChip = (name, active = false) =>
  `<span class="player-chip player-chip--${name.toLowerCase()}${active ? " player-chip--active" : ""}">${name}</span>`;

// CSS value for a player's color, e.g. "var(--player-b)".
export const playerColor = (name) => `var(--player-${name.toLowerCase()})`;

// Payoff count-up: a payoff that rises ticks up to its new value over COUNT_MS.
// Like the board, the start of each count is remembered per <tbody> so a redraw
// carries on counting instead of starting over.
const COUNT_MS = 600;
const counts = new WeakMap();    // <tbody> -> { A: { from, to, at }, ... }
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function countUp(el, { from, to, at }) {
  const tick = (now) => {
    const t = Math.min(1, (now - at) / COUNT_MS);
    el.textContent = Math.round(from + (to - from) * (1 - (1 - t) ** 3));   // ease-out
    if (t < 1 && el.isConnected) requestAnimationFrame(tick);
  };
  tick(performance.now());
}

// Scoreboard rows: one per player with a colored chip, settlements and payoff.
// The row of the player whose turn it is gets tinted in their color; at the end,
// every player tied for the best payoff (the starred rows) glows instead.
export function renderScores(tbody, state, board) {
  const values = new Map(board.vertices.map((v) => [v.id, v.value]));
  const now = performance.now();
  const before = counts.get(tbody) || {};
  const after = {};
  tbody.replaceChildren();
  for (const p of state.players) {
    const old = before[p.name];
    after[p.name] = old && p.payoff === old.to ? old
      : old && p.payoff > old.to ? { from: old.to, to: p.payoff, at: now }
      : { from: p.payoff, to: p.payoff, at: -Infinity };          // first draw or a new game
    const row = document.createElement("tr");
    const spots = p.settlements.map((s) => `${s} (${values.get(s)})`).join(" + ") || "none yet";
    const winner = state.winners.includes(p.name);
    if (p.name === state.current || winner) {      // current is null once the game is over
      row.className = winner ? "score-row--winner" : "score-row--current";
      row.style.setProperty("--player", playerColor(p.name));
    }
    row.innerHTML = `
      <th scope="row">${playerChip(p.name)}</th>
      <td>${p.kind}</td>
      <td>${spots}</td>
      <td class="num"><span>${p.payoff}</span>${winner ? " &#9733;" : ""}</td>`;
    tbody.append(row);
    if (now - after[p.name].at < COUNT_MS && !reduceMotion()) countUp(row.querySelector(".num span"), after[p.name]);
  }
  counts.set(tbody, after);
}

// "Turn 3: [A] takes spot 22 (value 12)" for one move, as HTML (the letter is a chip).
export const describeMove = (m) => `Turn ${m.turn}: ${playerChip(m.player)} takes spot ${m.vertex} (value ${m.value})`;

// Winner line once a game is over.
export function resultText(state) {
  if (!state.is_over) return "";
  const w = state.winners;
  return w.length === 1 ? `Winner: player ${w[0]}` : `Tie for first: players ${w.join(", ")}`;
}
