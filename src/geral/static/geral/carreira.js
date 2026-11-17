// Carreira: build a player in a draft of legends, watch his career season by season, share the card.
// Four steps on one page (player → draft → career → card); the server simulates, this only shows.
(() => {
  const root = document.getElementById("cr");
  if (!root) return;
  const jogo = JSON.parse(document.getElementById("cr-data").textContent);
  const API = `/api/jogos/carreira/${jogo.edicao}`;
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const nomeAtributo = Object.fromEntries(jogo.atributos.map((a) => [a.id, a.nome]));
  // Only vertical: scrollIntoView would also scroll the pitch (.wall hides a wider decoration).
  const rolar = (node, onde = "start") => {
    const r = node.getBoundingClientRect();
    const barra = $("cr-bar").offsetHeight || 0; // the sticky bar must not cover what we scroll to
    const alvo = onde === "center" ? r.top - (innerHeight - r.height) / 2 : r.top - barra - 16;
    window.scrollTo({ top: scrollY + alvo, behavior: "smooth" });
  };
  const show = (step) =>
    ["cr-craque", "cr-draft", "cr-carreira"].forEach((id) => ($(id).hidden = id !== step));

  let estado;
  const novo = () => ({
    craque: null,
    oferta: null,
    vagas: [0, 1, 2, 3, 4, 5, 6, 7], // the offer's legend shown at each of the 8 turns
    trocou: false,
    vez: 0,
    roubos: {}, // atributo -> {lenda, nota}
    semente: null,
    escolhas: [],
    mostradas: 0,
    modo: "rapida",
    temporadas: [],
    corpo: null,
  });

  // -- 1. the player --------------------------------------------------------------------------

  const form = $("cr-craque");
  const pressed = (attr) => form.querySelector(`[data-${attr}][aria-pressed="true"]`).dataset[attr];
  form.querySelectorAll(".cr-choice").forEach((group) =>
    group.addEventListener("click", (event) => {
      const chip = event.target.closest(".chip");
      if (!chip) return;
      group.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
    }),
  );
  const modos = form.querySelector(".cr-modes");
  modos.addEventListener("click", (event) => {
    const botao = event.target.closest(".cr-mode");
    if (!botao) return;
    modos.querySelectorAll(".cr-mode").forEach((m) => m.setAttribute("aria-pressed", String(m === botao)));
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const nome = $("cr-nome").value.trim();
    if (!nome) return $("cr-nome").focus();
    estado = novo();
    estado.craque = {
      nome,
      camisa: Math.min(99, Math.max(1, Number($("cr-camisa").value) || 10)),
      posicao: pressed("posicao"),
      pe: pressed("pe"),
      clube: $("cr-clube").value,
    };
    estado.modo = form.querySelector('.cr-mode[aria-pressed="true"]').dataset.modo;
    const go = form.querySelector(".cr-go");
    go.disabled = true;
    try {
      estado.oferta = await post(`${API}/oferta`, { clube: estado.craque.clube });
      show("cr-draft");
      desenharDraft();
      rolar($("cr-draft"), "start");
    } catch (erro) {
      alert(erro.message);
    } finally {
      go.disabled = false;
    }
  });

  // -- 2. the draft -----------------------------------------------------------------------------

  const pesos = () => jogo.pesos[estado.craque.posicao];
  const destaques = () =>
    Object.entries(pesos())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([a]) => a);

  function geral() {
    const feitos = Object.entries(estado.roubos);
    if (!feitos.length) return "–";
    let soma = 0;
    let peso = 0;
    for (const [atributo, { nota }] of feitos) {
      soma += nota * pesos()[atributo];
      peso += pesos()[atributo];
    }
    return Math.round(soma / peso);
  }

  function desenharDraft() {
    const { craque } = estado;
    $("cr-quem").textContent = `${craque.nome} · #${craque.camisa} · ${craque.posicao}`;
    $("cr-overall").textContent = geral();
    const lista = $("cr-attrs");
    lista.replaceChildren();
    for (const a of jogo.atributos) {
      const roubo = estado.roubos[a.id];
      const li = el("li", roubo ? "cr-attr done" : "cr-attr");
      li.append(el("span", "cr-attr-name", a.nome), el("span", "lamp cr-attr-val", roubo ? roubo.nota : "--"));
      li.append(el("span", "cr-attr-from", roubo ? roubo.lenda : ""));
      lista.append(li);
    }
    if (estado.vez >= 8) return;
    const lenda = estado.oferta.lendas[estado.vagas[estado.vez]];
    $("cr-count").textContent = `Lenda ${estado.vez + 1} de 8`;
    $("cr-legend-name").textContent = lenda.nome;
    $("cr-legend-tag").hidden = lenda.regiao !== "nordeste";
    $("cr-reroll").hidden = estado.trocou;
    const botoes = $("cr-steal");
    botoes.replaceChildren();
    const fortes = destaques();
    for (const a of jogo.atributos) {
      const b = el("button", "cr-stat");
      b.type = "button";
      b.disabled = Boolean(estado.roubos[a.id]);
      if (fortes.includes(a.id)) b.classList.add("key-attr");
      b.append(el("span", "cr-stat-name", a.nome), el("span", "cr-stat-val", lenda.notas[a.id]));
      b.addEventListener("click", () => roubar(lenda, a.id));
      botoes.append(b);
    }
  }

  function roubar(lenda, atributo) {
    estado.roubos[atributo] = { lenda: lenda.nome, nota: lenda.notas[atributo] };
    estado.vez += 1;
    desenharDraft();
    if (estado.vez === 8) comecarCarreira();
  }

  $("cr-reroll").addEventListener("click", () => {
    if (estado.trocou) return;
    estado.trocou = true;
    estado.vagas[estado.vez] = 8; // the spare legend takes this turn
    desenharDraft();
  });

  // -- 3. the career ----------------------------------------------------------------------------

  const AUTO = 1800; // ms per season in the Rápida mode

  const pedido = () => ({
    semente_draft: estado.oferta.semente_draft,
    semente: estado.semente,
    craque: estado.craque,
    modo: estado.modo,
    roubos: Object.entries(estado.roubos).map(([atributo, r]) => ({ lenda: r.lenda, atributo })),
    escolhas: estado.escolhas,
  });

  async function post(url, body) {
    const resposta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const dados = await resposta.json().catch(() => ({}));
    if (!resposta.ok) {
      const detalhe = typeof dados.detail === "string" ? dados.detail : "Algo deu errado. Tente de novo.";
      throw new Error(detalhe);
    }
    return dados;
  }

  const quem = (c) => `${c.nome} · #${c.camisa} · ${c.posicao}`;

  function comecarCarreira() {
    show("cr-carreira");
    $("cr-bar-who").textContent = quem(estado.craque);
    $("cr-bar-nota").textContent = `geral ${geral()}`;
    $("cr-now").replaceChildren();
    delete $("cr-now").dataset.temporada;
    $("cr-timeline").replaceChildren();
    $("cr-shelf").replaceChildren();
    $("cr-cabinet").hidden = true;
    rolar($("cr-carreira"), "start");
    simular();
  }

  async function simular() {
    $("cr-error").hidden = $("cr-retry").hidden = true;
    try {
      const corpo = await post(`${API}/simular`, pedido());
      estado.semente = corpo.semente;
      estado.temporadas = corpo.carreira.temporadas;
      estado.corpo = corpo;
      avancar();
    } catch (erro) {
      $("cr-error").textContent = erro.message || "Sem conexão. Tente de novo.";
      $("cr-error").hidden = $("cr-retry").hidden = false;
    }
  }

  // One season on screen at a time; the earlier ones go to the timeline.
  let relogio = null;
  function avancar() {
    clearTimeout(relogio);
    const { temporadas } = estado;
    if (estado.mostradas < temporadas.length) {
      mostrarTemporada(temporadas[estado.mostradas]);
      estado.mostradas += 1;
      const faltam = estado.mostradas < temporadas.length;
      $("cr-next").hidden = !faltam;
      $("cr-skip").hidden = !faltam || estado.modo === "completa";
      if (faltam && estado.modo === "rapida") relogio = setTimeout(avancar, AUTO);
      if (faltam) return;
    }
    $("cr-next").hidden = $("cr-skip").hidden = true;
    const { pendente, final } = estado.corpo.carreira;
    if (pendente) return perguntar(pendente);
    if (final) fim(final, estado.corpo.codigo);
  }

  $("cr-next").addEventListener("click", avancar);
  $("cr-skip").addEventListener("click", () => {
    clearTimeout(relogio);
    while (estado.mostradas < estado.temporadas.length - 1) {
      mostrarTemporada(estado.temporadas[estado.mostradas]);
      estado.mostradas += 1;
    }
    avancar();
  });
  $("cr-retry").addEventListener("click", () => simular());

  const chip = (texto, cls = "cr-chip") => el("span", cls, texto);

  // Our own trophy drawings, one shape per kind of competition (no photos: the real trophies'
  // designs and pictures have owners). Static markup only: no data goes into it.
  const BASE = '<rect x="15" y="34" width="10" height="5"/><rect x="10" y="39" width="20" height="6" rx="1"/>';
  const DESENHOS = {
    liga: '<path d="M7 5h26v9c0 9-6 15-13 15S7 23 7 14z"/><path d="M7 8H2v4c0 5 3 8 6 8M33 8h5v4c0 5-3 8-6 8" fill="none" stroke="currentColor" stroke-width="2.5"/><rect x="17" y="28" width="6" height="7"/>' + BASE,
    copa: '<path d="M12 3h16v14c0 7-4 11-8 11s-8-4-8-11z"/><path d="M12 7H8v3c0 4 2 6 5 6M28 7h4v3c0 4-2 6-5 6" fill="none" stroke="currentColor" stroke-width="2.2"/><rect x="18" y="27" width="4" height="8"/>' + BASE,
    continental: '<path d="M11 5h18v11c0 7-4 12-9 12s-9-5-9-12z"/><path d="M11 8C3 6 1 14 4 18s7 3 9 1M29 8c8-2 10 6 7 10s-7 3-9 1" fill="none" stroke="currentColor" stroke-width="2.8"/><rect x="17" y="27" width="6" height="8"/>' + BASE,
    mundo: '<circle cx="20" cy="9" r="7"/><path d="M13 14c-1 7 2 12 7 14 5-2 8-7 7-14-2 3-5 4-7 4s-5-1-7-4z"/><rect x="17" y="27" width="6" height="8"/>' + BASE,
    estadual: '<path d="M13 9h14v9c0 6-3 10-7 10s-7-4-7-10z"/><path d="M13 12H9v2c0 3 2 5 4 5M27 12h4v2c0 3-2 5-4 5" fill="none" stroke="currentColor" stroke-width="2"/><rect x="18" y="27" width="4" height="8"/>' + BASE,
    nordeste: '<circle cx="20" cy="6" r="3.5"/><path d="M20 0v1.5M14 2l1.2 1.2M26 2l-1.2 1.2M12.5 6h1.5M26 6h1.5" stroke="currentColor" stroke-width="1.6"/><path d="M11 11h18v8c0 6-4 9-9 9s-9-3-9-9z"/><path d="M11 13H7v2c0 4 3 6 5 6M29 13h4v2c0 4-3 6-5 6" fill="none" stroke="currentColor" stroke-width="2.2"/><rect x="17" y="27" width="6" height="8"/>' + BASE,
  };
  const tipoDaTaca = (nome) => (jogo.tacas || {})[nome] || "copa";
  function taca(nome) {
    const tipo = tipoDaTaca(nome);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 40 46");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("class", `cr-taca ${tipo}`);
    svg.innerHTML = DESENHOS[tipo] || DESENHOS.copa;
    return svg;
  }
  function selo(nome, cls = "cr-trophy") {
    const s = el("span", cls);
    s.append(taca(nome), el("span", "", nome));
    return s;
  }

  function mostrarTemporada(t) {
    const atual = $("cr-now");
    const anterior = atual.dataset.temporada;
    if (anterior) $("cr-timeline").prepend(linhaDoTempo(JSON.parse(anterior)));
    atual.dataset.temporada = JSON.stringify(t);
    atual.replaceChildren();
    atual.classList.remove("enter");
    void atual.offsetWidth; // restart the animation
    atual.classList.add("enter");
    atual.append(el("span", "cr-kicker", `${t.ano} · ${t.idade} anos · ${t.pais}`));
    if (t.chegada) atual.append(chip(t.chegada, "cr-arrival"));
    atual.append(el("h3", "cr-club-big", t.clube));
    const numeros = el("div", "cr-numbers");
    if (t.idade === 16) numeros.append(chip("Categorias de base"));
    else {
      numeros.append(chip(`${t.jogos} jogos`), chip(`${t.gols} gols`), chip(`${t.assistencias} assist.`));
      if (t.selecao) numeros.append(chip(`${t.selecao} pela Seleção`, "cr-chip selecao"));
    }
    atual.append(numeros);
    if (t.titulos.length) {
      const tacas = el("div", "cr-trophies");
      t.titulos.forEach((nome) => tacas.append(selo(nome)));
      atual.append(tacas);
    }
    atual.append(el("p", "cr-headline", t.manchete));
    if (t.rotina) {
      const r = t.rotina;
      const linha = el("p", r.deu_certo ? "cr-routine ok" : "cr-routine bad");
      linha.append(el("b", "", r.deu_certo ? "Deu certo" : "Deu errado"));
      linha.append(document.createTextNode(` · ${r.escolha}${r.efeito ? `: ${r.efeito}` : ""}`));
      atual.append(linha);
    }
    $("cr-bar-nota").textContent = `${t.idade} anos · ${t.clube} · nota ${t.nota}`;
    const vistas = estado ? estado.temporadas.slice(0, estado.mostradas + 1) : [];
    const ate = estado ? vistas : (jogo.compartilhada?.carreira?.temporadas || []);
    $("cr-cabinet").hidden = salaDeTrofeus($("cr-shelf"), ate) === 0;
  }

  const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

  function linhaDoTempo(t) {
    const li = el("li", "cr-line");
    li.append(el("span", "cr-line-age", t.idade));
    const corpo = el("div", "cr-line-body");
    const topo = el("div", "cr-line-top");
    topo.append(el("span", "cr-line-club", t.clube));
    const numeros = t.idade === 16 ? "categorias de base" : `${plural(t.jogos, "jogo", "jogos")} · ${plural(t.gols, "gol", "gols")}`;
    topo.append(el("span", "cr-line-nums", numeros));
    corpo.append(topo);
    if (t.titulos.length) {
      const tacas = el("div", "cr-line-trophies");
      t.titulos.forEach((nome) => tacas.append(selo(nome, "cr-line-trophy")));
      corpo.append(tacas);
    }
    li.append(corpo);
    li.title = t.manchete;
    return li;
  }

  // The trophy room: every title won so far, one shelf item per competition.
  function salaDeTrofeus(lista, temporadas) {
    const contagem = new Map();
    temporadas.forEach((t) => t.titulos.forEach((n) => contagem.set(n, (contagem.get(n) || 0) + 1)));
    lista.replaceChildren();
    const ordem = ["mundo", "continental", "liga", "copa", "nordeste", "estadual"];
    [...contagem.entries()]
      .sort((a, b) => ordem.indexOf(tipoDaTaca(a[0])) - ordem.indexOf(tipoDaTaca(b[0])) || b[1] - a[1])
      .forEach(([nome, vezes]) => {
        const item = el("li", `cr-shelf-item ${tipoDaTaca(nome)}`);
        item.append(taca(nome), el("b", "cr-shelf-n", `${vezes}×`), el("span", "cr-shelf-name", nome));
        lista.append(item);
      });
    return contagem.size;
  }

  const TIPOS = { dia: "Dia a dia", mercado: "Mercado", decisao: "Decisão" };

  function perguntar(pendente) {
    const caixa = $("cr-question");
    caixa.dataset.tipo = pendente.tipo;
    $("cr-q-kind").textContent = TIPOS[pendente.tipo] || "Decisão";
    $("cr-question-text").textContent = pendente.pergunta;
    const opcoes = $("cr-options");
    opcoes.replaceChildren();
    pendente.opcoes.forEach((texto, i) => {
      const info = (pendente.info || [])[i];
      const b = el("button", "cr-option");
      b.type = "button";
      b.append(el("span", "cr-option-text", texto));
      if (info && info.chance !== null && info.chance !== undefined) {
        const barra = el("span", "cr-chance");
        barra.style.setProperty("--chance", `${info.chance}%`);
        barra.append(el("span", "cr-chance-n", `${info.chance}%`));
        b.append(barra);
      }
      if (info && info.efeitos) b.append(el("span", "cr-option-effects", info.efeitos));
      b.addEventListener("click", () => {
        caixa.hidden = true;
        estado.escolhas.push(i);
        simular();
      });
      opcoes.append(b);
    });
    caixa.hidden = false;
    rolar($("cr-now"), "start"); // the season first, its question right below
  }

  // -- 4. the card ------------------------------------------------------------------------------

  let compartilhar = null; // {texto, url, arquivo}

  async function fim(final, codigo) {
    const craque = estado ? estado.craque : jogo.compartilhada.craque;
    const titulos = Object.values(final.titulos).reduce((a, b) => a + b, 0);
    $("cr-end-kicker").textContent = `${craque.nome} · #${craque.camisa} · ${craque.posicao}`;
    $("cr-end-label").textContent = `${final.rotulo} · ${final.nota}`;
    $("cr-end-desc").textContent = `${final.descricao} Sua carreira lembra a de ${final.parecido}.`;
    const todas = estado ? estado.temporadas : jogo.compartilhada.carreira.temporadas;
    $("cr-end-cabinet").hidden = salaDeTrofeus($("cr-end-shelf"), todas) === 0;
    const stats = $("cr-end-stats");
    stats.replaceChildren();
    const linhas = [
      ["Títulos", titulos],
      ["Jogos", final.jogos],
      ["Gols", final.gols],
      ["Clubes", final.clubes.length],
    ];
    if (final.selecao) linhas.push(["Pela Seleção", final.selecao]);
    for (const [rotulo, valor] of linhas) {
      const item = el("div", "cr-stat-item");
      item.append(el("dt", "", rotulo), el("dd", "", valor));
      stats.append(item);
    }
    const url = `${jogo.url || location.origin}/jogos/carreira/c/${codigo}`;
    const canvas = await desenharCard({ craque, final, titulos });
    const png = canvas.toDataURL("image/png");
    $("cr-card").src = png;
    $("cr-download").href = png;
    const blob = await new Promise((ok) => canvas.toBlob(ok, "image/png"));
    compartilhar = {
      texto: `Carreira na Geral: ${craque.nome} virou "${final.rotulo}" (nota ${final.nota}, ${titulos} títulos). E o seu craque?`,
      url,
      arquivo: blob ? new File([blob], "carreira.png", { type: "image/png" }) : null,
    };
    $("cr-end").hidden = false;
    rolar($("cr-end"), "start");
  }

  $("cr-share").addEventListener("click", async () => {
    if (!compartilhar) return;
    const { texto, url, arquivo } = compartilhar;
    try {
      if (arquivo && navigator.canShare && navigator.canShare({ files: [arquivo] })) {
        return await navigator.share({ files: [arquivo], text: `${texto} ${url}` });
      }
      if (navigator.share) return await navigator.share({ text: texto, url });
    } catch (erro) {
      if (erro.name === "AbortError") return;
    }
    try {
      await navigator.clipboard.writeText(`${texto} ${url}`);
      $("cr-copied").textContent = "Copiado! Cole no grupo da torcida.";
    } catch {
      $("cr-copied").textContent = url;
    }
  });

  $("cr-again").addEventListener("click", () => {
    if (jogo.compartilhada) {
      location.href = `/jogos/carreira${jogo.edicao === "geral" ? "" : `/${jogo.edicao}`}`;
      return;
    }
    $("cr-end").hidden = true;
    $("cr-question").hidden = true;
    show("cr-craque");
    rolar(form, "start");
  });

  // The card, drawn like the old scoreboard: lamps on black, a paper plate for the label.
  async function desenharCard({ craque, final, titulos }) {
    const css = getComputedStyle(document.documentElement);
    const cor = (nome) => css.getPropertyValue(nome).trim();
    const fonte = (nome) => css.getPropertyValue(nome).trim();
    const display = fonte("--display");
    const dots = fonte("--dots");
    const body = fonte("--body");
    try {
      await Promise.all([
        document.fonts.load(`900 120px ${display}`),
        document.fonts.load(`900 60px ${dots}`),
        document.fonts.load(`600 30px ${body}`),
      ]);
    } catch {
      /* fallback fonts are fine */
    }
    const W = 1080;
    const H = 1350;
    const canvas = el("canvas");
    canvas.width = W;
    canvas.height = H;
    const g = canvas.getContext("2d");
    g.fillStyle = cor("--board");
    g.fillRect(0, 0, W, H);
    g.fillStyle = cor("--lamp-off");
    for (let y = 8; y < H; y += 14) for (let x = 8; x < W; x += 14) g.fillRect(x, y, 4, 4);
    g.strokeStyle = cor("--turf");
    g.lineWidth = 36;
    g.strokeRect(18, 18, W - 36, H - 36);

    const lamp = cor("--lamp");
    const paper = cor("--paper");
    const brilho = (fn) => {
      g.save();
      g.shadowColor = "rgba(255, 194, 26, .55)";
      g.shadowBlur = 18;
      fn();
      g.restore();
    };
    const caber = (texto, max, peso, familia, tamanho) => {
      let t = tamanho;
      g.font = `${peso} ${t}px ${familia}`;
      while (g.measureText(texto).width > max && t > 20) {
        t -= 4;
        g.font = `${peso} ${t}px ${familia}`;
      }
      return t;
    };
    const X = 84;
    const LARG = W - 2 * X;
    g.textBaseline = "alphabetic";

    g.fillStyle = lamp;
    brilho(() => {
      g.font = `900 34px ${dots}`;
      g.fillText("GERAL · CARREIRA", X, 120);
    });
    const nome = craque.nome.toUpperCase();
    caber(nome, LARG, 900, display, 150);
    g.fillStyle = "#fff";
    g.fillText(nome, X, 270);
    g.fillStyle = paper;
    g.font = `700 36px ${body}`;
    g.fillText(`#${craque.camisa} · ${craque.posicao.toUpperCase()}`, X, 330);

    // the label on a paper plate
    g.fillStyle = paper;
    g.fillRect(X, 380, LARG, 190);
    g.fillStyle = cor("--ink");
    const rotulo = final.rotulo.toUpperCase();
    caber(rotulo, LARG - 60, 900, display, 120);
    g.fillText(rotulo, X + 30, 515);

    g.fillStyle = lamp;
    brilho(() => {
      g.font = `900 46px ${dots}`;
      g.fillText("NOTA", X, 680);
      g.font = `900 ${final.nota >= 100 ? 120 : 170}px ${dots}`; // three digits fit beside the numbers
      g.fillText(String(final.nota), X, 840);
    });
    g.fillStyle = paper;
    g.font = `700 40px ${body}`;
    const numeros = [`${titulos} títulos`, `${final.jogos} jogos`, `${final.gols} gols`];
    if (final.selecao) numeros.push(`${final.selecao} pela Seleção`);
    g.fillText(numeros.slice(0, 3).join(" · "), X + 330, 700);
    if (numeros[3]) g.fillText(numeros[3], X + 330, 760);
    const principais = Object.entries(final.titulos)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([n, q]) => `${q}× ${n}`);
    g.font = `600 32px ${body}`;
    principais.forEach((linha, i) => g.fillText(linha, X + 330, 820 + i * 44));

    // the clubs, wrapped
    g.font = `800 40px ${display}`;
    const palavras = final.clubes.map((c) => c.toUpperCase());
    let linha = "";
    let y = 960;
    for (let i = 0; i < palavras.length && y < 1150; i++) {
      const pedaco = (linha ? `${linha} → ` : "") + palavras[i];
      if (g.measureText(pedaco).width > LARG && linha) {
        g.fillText(linha, X, y);
        y += 52;
        linha = palavras[i];
      } else linha = pedaco;
    }
    if (linha && y < 1150) g.fillText(linha, X, y);

    g.fillStyle = lamp;
    g.font = `600 34px ${body}`;
    if (final.parecido) g.fillText(`Lembra: ${final.parecido}`, X, 1210);
    g.fillStyle = paper;
    g.font = `600 28px ${body}`;
    const site = (jogo.url || location.origin).replace(/^https?:\/\//, "");
    g.fillText(`Monte o seu: ${site}/jogos/carreira`, X, 1270);
    return canvas;
  }

  // A shared link: the last season, the timeline, then the card.
  if (jogo.compartilhada && jogo.compartilhada.carreira) {
    const { carreira, codigo, craque } = jogo.compartilhada;
    show("cr-carreira");
    $("cr-bar-who").textContent = quem(craque);
    carreira.temporadas.forEach(mostrarTemporada);
    fim(carreira.final, codigo);
  } else if (jogo.compartilhada) {
    $("cr-craque").hidden = true;
  }
})();
