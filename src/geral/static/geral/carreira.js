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
  const PASSO = 650; // ms between seasons
  // Only vertical: scrollIntoView would also scroll the pitch (.wall hides a wider decoration).
  const rolar = (node, onde = "start") => {
    const r = node.getBoundingClientRect();
    const alvo = onde === "center" ? r.top - (innerHeight - r.height) / 2 : r.top - 12;
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
    rapido: false,
    resposta: null,
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
      clube: $("cr-clube") ? $("cr-clube").value : null,
    };
    const go = form.querySelector(".cr-go");
    go.disabled = true;
    try {
      estado.oferta = await post(`${API}/oferta`, {});
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

  const pedido = () => ({
    semente_draft: estado.oferta.semente_draft,
    semente: estado.semente,
    craque: estado.craque,
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

  function comecarCarreira() {
    show("cr-carreira");
    $("cr-header").textContent = `${estado.craque.nome} · #${estado.craque.camisa} · ${estado.craque.posicao} · geral ${geral()}`;
    $("cr-seasons").replaceChildren();
    rolar($("cr-carreira"), "start");
    simular();
  }

  async function simular() {
    $("cr-error").hidden = $("cr-retry").hidden = true;
    $("cr-skip").hidden = false;
    try {
      const corpo = await post(`${API}/simular`, pedido());
      estado.semente = corpo.semente;
      estado.resposta = corpo;
      await animar(corpo.carreira.temporadas);
      depois(corpo);
    } catch (erro) {
      $("cr-error").textContent = erro.message || "Sem conexão. Tente de novo.";
      $("cr-error").hidden = $("cr-retry").hidden = false;
    }
  }

  const espera = (ms) => new Promise((ok) => setTimeout(ok, ms));

  function linhaTemporada(t) {
    const li = el("li", "cr-season");
    const top = el("div", "cr-season-top");
    top.append(el("span", "cr-age", `${t.idade}`), el("span", "cr-club", t.clube));
    const numeros = t.idade === 16 ? "base" : `${t.jogos}j ${t.gols}g`;
    top.append(el("span", "cr-nums", numeros));
    li.append(top);
    if (t.titulos.length) li.append(el("span", "cr-titles", `🏆 ${t.titulos.join(" · ")}`));
    li.append(el("p", "cr-headline", t.manchete));
    return li;
  }

  async function animar(temporadas) {
    const lista = $("cr-seasons");
    while (estado.mostradas < temporadas.length) {
      const li = linhaTemporada(temporadas[estado.mostradas]);
      lista.append(li);
      estado.mostradas += 1;
      if (!estado.rapido) {
        li.classList.add("enter");
        const quadro = lista.parentElement;
        quadro.scrollTop = quadro.scrollHeight;
        await espera(PASSO);
      }
    }
  }

  $("cr-skip").addEventListener("click", () => (estado.rapido = true));
  $("cr-retry").addEventListener("click", () => simular());

  function depois(corpo) {
    const { pendente, final } = corpo.carreira;
    $("cr-skip").hidden = Boolean(final) || Boolean(pendente);
    if (pendente) return perguntar(pendente);
    if (final) fim(final, corpo.codigo);
  }

  function perguntar(pendente) {
    const caixa = $("cr-question");
    $("cr-question-text").textContent = pendente.pergunta;
    const opcoes = $("cr-options");
    opcoes.replaceChildren();
    pendente.opcoes.forEach((texto, i) => {
      const b = el("button", "btn cr-option", texto);
      b.type = "button";
      b.addEventListener("click", () => {
        caixa.hidden = true;
        estado.escolhas.push(i);
        estado.rapido = false;
        simular();
      });
      opcoes.append(b);
    });
    caixa.hidden = false;
    rolar(caixa, "center");
  }

  // -- 4. the card ------------------------------------------------------------------------------

  let compartilhar = null; // {texto, url, arquivo}

  async function fim(final, codigo) {
    const craque = estado ? estado.craque : jogo.compartilhada.craque;
    const titulos = Object.values(final.titulos).reduce((a, b) => a + b, 0);
    $("cr-end-kicker").textContent = `${craque.nome} · #${craque.camisa} · ${craque.posicao}`;
    $("cr-end-label").textContent = `${final.rotulo} · ${final.nota}`;
    $("cr-end-desc").textContent = `${final.descricao} Sua carreira lembra a de ${final.parecido}.`;
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

  // A shared link: the whole career at once, then the card.
  if (jogo.compartilhada && jogo.compartilhada.carreira) {
    const { carreira, codigo } = jogo.compartilhada;
    show("cr-carreira");
    $("cr-skip").hidden = true;
    const c = jogo.compartilhada.craque;
    $("cr-header").textContent = `${c.nome} · #${c.camisa} · ${c.posicao}`;
    $("cr-seasons").replaceChildren(...carreira.temporadas.map(linhaTemporada));
    fim(carreira.final, codigo);
  } else if (jogo.compartilhada) {
    $("cr-craque").hidden = true;
  }
})();
