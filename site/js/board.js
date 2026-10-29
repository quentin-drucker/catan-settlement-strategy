// board.js: draws the game board as SVG, plus small shared helpers for the pages.
//
// SVG = a drawing made of shapes (polygons, circles, text) that the browser
// keeps sharp at any size. Every shape gets a .board__* class, so all colours
// come from styles.css; nothing is styled here.
//
// Positions: vertices sit on the integer lattice from src/board.py.
// One lattice step = sqrt(3)/2 hex sides across and 1/2 hex side down, so with
// a hex side of 34px: x * 29.4, y * 17.

const SVG_NS = "http://www.w3.org/2000/svg";
const STEP_X = 29.4;
const STEP_Y = 17;

// Small helper: make an SVG element with attributes (and optional text).
function svgEl(tag, attrs = {}, text = null) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attrs)) el.setAttribute(name, value);
  if (text !== null) el.textContent = text;
  return el;
}

const pos = (v) => [v.x * STEP_X, v.y * STEP_Y];

// Draw `board` + `state` (from engine.js) into the <svg> element `svg`.
// options:
//   clickable  - open spots become buttons (Play page, human's turn)
//   onSpot(id) - called when an open spot is clicked or pressed with Enter/Space
//   showValues - write each open spot's value on it
//   label      - accessible name for the whole drawing
export function drawBoard(svg, board, state, options = {}) {
  const { clickable = false, onSpot = null, showValues = false, label = "Catan board" } = options;
  svg.replaceChildren();
  svg.setAttribute("viewBox", "-200 -175 400 350");
  svg.setAttribute("role", "group");
  svg.setAttribute("aria-label", label);
  svg.classList.add("board");

  const vertices = new Map(board.vertices.map((v) => [v.id, v]));
  const owner = state.owner;                       // {"22": "A", ...}
  const blocked = new Set(state.blocked);
  const lastMove = state.moves.length ? state.moves[state.moves.length - 1].vertex : null;

  // Sea: a flat-topped hexagon behind the island.
  const sea = [...Array(6)].map((_, k) => {
    const a = (Math.PI / 3) * k;
    return `${(190 * Math.cos(a)).toFixed(1)},${(190 * Math.sin(a)).toFixed(1)}`;
  });
  svg.append(svgEl("polygon", { class: "board__sea", points: sea.join(" ") }));

  // Land tiles.
  for (const h of board.hexes) {
    const pts = h.corners.map((c) => pos(vertices.get(c)).map((n) => n.toFixed(1)).join(",")).join(" ");
    svg.append(svgEl("polygon", { class: "board__tile", points: pts }));
  }

  // Number tokens: disc + number + one pip per way to roll it (out of 36).
  for (const h of board.hexes) {
    if (h.number === null) continue;                // desert: no token
    const top = vertices.get(h.corners[0]);         // hex centre = 2 lattice rows below its top corner
    const cx = top.x * STEP_X;
    const cy = (top.y + 2) * STEP_Y;
    const high = h.number === 6 || h.number === 8;
    svg.append(svgEl("circle", { class: "board__token", cx, cy, r: 14 }));
    svg.append(svgEl("text", {
      class: `board__token-number${high ? " board__token-number--high" : ""}`, x: cx, y: cy + 3,
    }, String(h.number)));
    for (let i = 0; i < h.weight; i++) {
      const px = cx + (i - (h.weight - 1) / 2) * 3.4;
      svg.append(svgEl("circle", { class: "board__pip", cx: px.toFixed(1), cy: cy + 8.5, r: 1.1 }));
    }
  }

  // Spots: blocked dots, open spots (buttons when clickable), then settlements on top.
  for (const v of board.vertices) {
    if (String(v.id) in owner) continue;
    const [x, y] = pos(v);
    if (blocked.has(v.id)) {
      svg.append(svgEl("circle", { class: "board__spot board__spot--blocked", cx: x, cy: y, r: 4.5 }));
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
      group.addEventListener("click", () => onSpot(v.id));
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();               // Space would otherwise scroll the page
          onSpot(v.id);
        }
      });
    }
    svg.append(group);
  }

  // Settlements: a house shape with the player's letter (letter = second cue besides colour).
  for (const [id, name] of Object.entries(owner)) {
    const [x, y] = pos(vertices.get(Number(id)));
    if (Number(id) === lastMove) {
      svg.append(svgEl("circle", { class: "board__last", cx: x, cy: y, r: 15 }));  // newest move
    }
    const house = [[0, -11], [9, -4], [9, 8], [-9, 8], [-9, -4]]
      .map(([dx, dy]) => `${(x + dx).toFixed(1)},${(y + dy).toFixed(1)}`).join(" ");
    const piece = svgEl("polygon", { class: `board__piece board__piece--${name.toLowerCase()}`, points: house });
    piece.append(svgEl("title", {}, `Player ${name}, spot ${id}`));
    // House + letter in one group so the newest one can animate as a unit (.board__new).
    const group = svgEl("g", Number(id) === lastMove ? { class: "board__new" } : {});
    group.append(piece, svgEl("text", { class: "board__piece-label", x, y: y + 5 }, name));
    svg.append(group);
  }
}

// The seat letter on its player color (same colors as the pieces), as HTML.
// `active` adds a soft pulse for the player whose turn it is.
export const playerChip = (name, active = false) =>
  `<span class="player-chip player-chip--${name.toLowerCase()}${active ? " player-chip--active" : ""}">${name}</span>`;

// CSS value for a player's color, e.g. "var(--player-b)".
export const playerColor = (name) => `var(--player-${name.toLowerCase()})`;

// Scoreboard rows: one per player with a coloured chip, settlements and payoff.
// The row of the player whose turn it is gets tinted in their color.
export function renderScores(tbody, state, board) {
  const values = new Map(board.vertices.map((v) => [v.id, v.value]));
  tbody.replaceChildren();
  for (const p of state.players) {
    const row = document.createElement("tr");
    const spots = p.settlements.map((s) => `${s} (${values.get(s)})`).join(" + ") || "none yet";
    const winner = state.winners.includes(p.name);
    if (p.name === state.current) {                // null once the game is over
      row.className = "score-row--current";
      row.style.setProperty("--player", playerColor(p.name));
    }
    row.innerHTML = `
      <th scope="row">${playerChip(p.name)}</th>
      <td>${p.kind}</td>
      <td>${spots}</td>
      <td class="num">${p.payoff}${winner ? " &#9733;" : ""}</td>`;
    tbody.append(row);
  }
}

// "Turn 3: [A] takes spot 22 (value 12)" for one move, as HTML (the letter is a chip).
export const describeMove = (m) => `Turn ${m.turn}: ${playerChip(m.player)} takes spot ${m.vertex} (value ${m.value})`;

// Winner line once a game is over.
export function resultText(state) {
  if (!state.is_over) return "";
  const w = state.winners;
  return w.length === 1 ? `Winner: player ${w[0]}` : `Tie for first: players ${w.join(", ")}`;
}
