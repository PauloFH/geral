// "Jogo da velha": pick a cell, search a player, the server judges the whole history. The day's
// picks and the streak live in localStorage. No dependencies.
(() => {
  const root = document.getElementById("jv");
  if (!root) return;
  const number = Number(root.dataset.number);
  const archive = root.dataset.archive === "1"; // a past board: its own save, no streak
  const board = root.dataset.board;
  const max = Number(root.dataset.max);
  const $ = (id) => document.getElementById(id);
  const form = $("jv-form");
  const dialog = $("jv-dialog");
  const search = $("jv-search");
  const cells = [...root.querySelectorAll(".vcell")];
  const KEY = archive ? `velha:geral:${number}` : "velha:geral";

  const read = (key, fallback) => {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch {
      return fallback;
    }
  };
  const write = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* private mode: the game still works, it just forgets */
    }
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const save = () => {
    write(KEY, day);
    if (!archive) write(`${KEY}:${number}`, day); // for when it shows up among the past ones
  };
  let day = read(KEY, null);
  if (!day && archive) {
    const daily = read("velha:geral", null); // played on its own day as "today's game"
    if (daily && daily.number === number) day = daily;
  }
  // A new day, or the board changed (a data update): start over.
  if (!day || day.number !== number || day.board !== board) day = { number, board, chutes: [] };
  let verdict = { casas: {}, acertos: [], over: false, revelacao: null, nomes: {} };
  let busy = false;
  let chosen = null; // the cell being filled
  let pending = null; // the search in flight

  const error = (text) => {
    $("jv-error").textContent = text;
    $("jv-error").hidden = !text;
  };

  const used = () => new Set(Object.values(verdict.casas));

  const drawBoard = () => {
    const missed = new Map(); // cell -> wrong guesses on it
    day.chutes.forEach((c, i) => {
      if (verdict.acertos[i] === false) missed.set(c.casa, (missed.get(c.casa) || 0) + 1);
    });
    cells.forEach((cell, casa) => {
      const id = verdict.casas[casa];
      const reveal = verdict.revelacao && verdict.revelacao[casa];
      const name = cell.querySelector(".vcell-name");
      const note = cell.querySelector(".vcell-note");
      cell.className = "vcell";
      if (id) {
        cell.classList.add("filled");
        name.textContent = verdict.nomes[id] || "";
        note.textContent = reveal ? `${reveal.total} valiam` : "";
      } else if (reveal) {
        cell.classList.add("revealed");
        name.textContent = reveal.top[0] ? reveal.top[0].nome : "ninguém";
        note.textContent = `${reveal.total} valiam`;
      } else {
        name.textContent = "";
        note.textContent = missed.has(casa) ? "✕".repeat(Math.min(3, missed.get(casa))) : "";
      }
      if (casa === chosen) cell.classList.add("chosen");
      cell.disabled = Boolean(id) || verdict.over || busy;
    });
    $("jv-left").textContent = Math.max(0, max - day.chutes.length);
  };

  const finish = () => {
    const filled = Object.keys(verdict.casas).length;
    const wrong = verdict.acertos.filter((a) => !a).length;
    $("jv-title").textContent =
      filled === 9 ? (wrong ? `Velha completa com ${wrong} ${wrong === 1 ? "erro" : "erros"}!` : "Velha completa, sem erro!") : `${filled} de 9 casas`;
    if (archive) return; // past boards don't count in the streak
    const stats = read(`${KEY}:stats`, { streak: 0, wins: 0, played: 0, last: 0, counted: 0 });
    if (stats.counted !== number) {
      stats.played += 1;
      if (filled === 9) {
        stats.wins += 1;
        stats.streak = stats.last === number - 1 ? stats.streak + 1 : 1;
        stats.last = number;
      } else {
        stats.streak = 0;
      }
      stats.counted = number;
      write(`${KEY}:stats`, stats);
    }
    $("jv-streak").textContent = stats.streak;
    $("jv-wins").textContent = stats.wins;
    $("jv-played").textContent = stats.played;
  };

  const render = () => {
    if (verdict.over) chosen = null;
    drawBoard();
    if (chosen !== null && !dialog.open) dialog.showModal();
    if (chosen === null && dialog.open) dialog.close();
    $("jv-result").hidden = !verdict.over;
    if (verdict.over) finish();
  };

  const judge = async () => {
    const response = await fetch(`/api/jogos/velha/geral/${number}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chutes: day.chutes }),
    });
    if (!response.ok) {
      const problem = new Error(`HTTP ${response.status}`);
      problem.status = response.status;
      throw problem;
    }
    verdict = await response.json();
  };

  // Saved picks the server no longer accepts (the base changed): start today over.
  const restart = () => {
    day = { number, board, chutes: [] };
    verdict = { casas: {}, acertos: [], over: false, revelacao: null, nomes: {} };
    save();
    error("Os dados mudaram e o jogo de hoje recomeçou.");
  };

  const pick = async (jogador) => {
    if (busy || chosen === null) return;
    busy = true; // one pick in flight at a time
    const casa = chosen;
    day.chutes.push({ casa, jogador });
    drawBoard();
    try {
      await judge();
      save();
      error("");
      const hit = verdict.casas[casa] === jogador;
      if (hit) chosen = null;
      else error(used().has(jogador) ? "Esse jogador já está no tabuleiro." : "Não vale nessa casa.");
      search.value = "";
      $("jv-results").replaceChildren();
    } catch (problem) {
      day.chutes.pop();
      if (problem.status === 422) restart();
      else error("Não deu para conferir agora. Tente de novo.");
    } finally {
      busy = false;
      render();
      if (chosen !== null) search.focus();
    }
  };

  const drawResults = (found) => {
    const taken = used();
    $("jv-results").replaceChildren(
      ...found.map((p) => {
        const li = el("li");
        const button = el("button", "club");
        button.type = "button";
        button.append(el("span", "club-name", p.nome), el("span", "club-country", [p.anos, p.posicao].filter(Boolean).join(" · ")));
        button.disabled = taken.has(p.id) || busy;
        button.addEventListener("click", () => pick(p.id));
        li.append(button);
        return li;
      }),
    );
    if (!found.length && search.value.trim().length >= 2) $("jv-results").append(el("li", "empty", "Nenhum jogador com esse nome."));
  };

  let timer = null;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (pending) pending.abort();
      pending = new AbortController();
      try {
        const response = await fetch(`/api/jogos/velha/jogadores?q=${encodeURIComponent(search.value)}`, { signal: pending.signal });
        if (response.ok) drawResults(await response.json());
      } catch {
        /* a newer search replaced this one */
      }
    }, 250);
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault(); // Enter picks the player when the search leaves only one
    const only = $("jv-results").querySelectorAll("button.club:not(:disabled)");
    if (only.length === 1) only[0].click();
  });

  const heads = { rows: [...root.querySelectorAll(".velha-head.row")], cols: [...root.querySelectorAll(".velha-head.col")] };
  cells.forEach((cell, casa) =>
    cell.addEventListener("click", () => {
      chosen = casa;
      error("");
      $("jv-cell-label").textContent = `${heads.rows[Math.floor(casa / 3)].textContent} × ${heads.cols[casa % 3].textContent}`;
      search.value = "";
      $("jv-results").replaceChildren();
      render();
      search.focus();
    }),
  );
  $("jv-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    chosen = null; // Esc, the ✕ or a right pick
    error("");
    drawBoard();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close(); // a tap on the dimmed board around it
  });

  $("jv-share").addEventListener("click", async () => {
    const filled = Object.keys(verdict.casas).length;
    const grid = [0, 3, 6]
      .map((r) => [0, 1, 2].map((c) => (verdict.casas[r + c] ? "🟩" : "⬜")).join(""))
      .join("\n");
    const text = `Jogo da velha #${number} · ${filled}/9 em ${day.chutes.length} chutes\n${grid}\n${location.href}`;
    try {
      if (navigator.share) await navigator.share({ text });
      else {
        await navigator.clipboard.writeText(text);
        $("jv-copied").textContent = "Copiado!";
      }
    } catch {
      /* the user closed the share sheet */
    }
  });

  render();
  if (day.chutes.length) {
    judge()
      .then(render)
      .catch((problem) => {
        if (problem.status === 422) restart();
        render();
      });
  }
})();
