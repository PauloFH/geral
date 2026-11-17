# Carreira — PR 2: página, draft, animação e card — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use checkbox (`- [ ]`) syntax.

**Goal:** O torcedor joga a Carreira no navegador: monta o craque, faz o draft, vê as temporadas uma a uma, responde as escolhas e recebe um card para compartilhar.

**Architecture:** Uma página por edição (`carreira.html.j2`) com os dados fixos em JSON embutido (atributos, pesos, clubes brasileiros); `carreira.js` é uma máquina de estados (craque → draft → carreira → card) sobre as duas rotas do PR 1. O card é desenhado em `<canvas>` e vai pelo Web Share (arquivo) com reserva de baixar a imagem e copiar o texto. `GET /jogos/carreira/c/{codigo}` reabre uma carreira: mesma versão dos dados → a carreira inteira já resolvida no servidor; versão velha → só o card pelo resumo.

**Tech Stack:** Jinja2, JS sem framework (como os outros joguinhos), CSS em `jogos.css`.

**Spec:** `docs/features/carreira.md`

## Global Constraints

- Estética da Geral: placar (lâmpadas amarelas em fundo escuro), papel, gramado; mesmos componentes dos outros jogos (`game-tabs`, `editions`, `stage`, `board match`, `result`, `_regras`).
- Mostrar rodando (desktop e celular) ao dev antes de commitar o visual.
- O nome do craque só entra no HTML escapado (Jinja autoescape; no JS só `textContent`).
- Commits conventional sem escopo, pt-BR, sem coautoria; portões antes de cada commit.

## Review Focus

1. Recarregar a página no meio da carreira não pode quebrar: começa do zero (sem estado guardado) — aceitável no modo livre.
2. Rede falhando no `/simular`: mensagem e botão "tentar de novo", sem perder o que já apareceu.
3. Nome com `<script>` ou emoji: aparece literal na tela e no card.
4. Celular estreito (360 px): draft e temporadas cabem sem rolagem horizontal.
5. Código inválido em `c/{codigo}`: página 404 da Geral, não 500.

---

### Task 1: Rotas da página, link do card e cartão em `/jogos`

**Files:** Modify `src/geral/web/app.py`, `src/geral/web/templates/jogos.html.j2`; Create `src/geral/web/templates/carreira.html.j2` (esqueleto); Test `tests/test_web_carreira.py`

- [ ] Testes: `test_pagina_da_carreira_por_edicao` (geral e vasco 200, com os clubes brasileiros só na geral; xyz 404); `test_link_do_card_reabre_a_carreira` (código do `/simular` → 200 com o rótulo e o nome); `test_link_de_versao_velha_mostra_o_resumo` (código com versão `00000000` → 200 com rótulo do resumo e "Jogar a sua"); `test_link_invalido_e_404`; `test_carreira_aparece_em_jogos_sem_numero_do_dia` (`/jogos` lista "Carreira" e "Jogar →", sem "#None").
- [ ] `games()` ganha a Carreira (`number: None`, edições de `carreira_edicoes()`); o hub mostra "Livre" e "Jogar →" quando `number` é `None`; as abas entre jogos passam a incluir a Carreira.
- [ ] Commit `feat: página e link compartilhável da carreira`.

### Task 2: A tela do jogo (template, CSS, JS)

**Files:** `carreira.html.j2`, `src/geral/static/geral/carreira.js`, `jogos.css`

- [ ] Craque: nome (24), camisa, posição e pé em botões; clube de partida (só na geral, select). Botão "Começar o draft".
- [ ] Draft: placar com os 8 atributos (vazios → nota roubada + nome da lenda) e a nota geral ao vivo pela posição (`PESOS` do JSON); a lenda da vez em cartão com as 8 notas como botões (atributo já preenchido desabilitado); "Sortear outra lenda" uma vez (troca pela reserva). "Lenda 3 de 8".
- [ ] Carreira: temporadas entram uma a uma (~0,6 s; botão "Pular" mostra todas): idade, clube, jogos/gols, 🏆 títulos, manchete. Escolha pendente: painel com a pergunta e os botões; a resposta chama `/simular` e a animação continua da temporada seguinte. Erro de rede: mensagem + "Tentar de novo".
- [ ] Card: canvas 1080×1350 no estilo placar (nome, camisa, posição, rótulo, nota, títulos, clubes, "lembra"), "Compartilhar" (Web Share com arquivo; reserva: baixar PNG e copiar texto `Carreira · {rótulo} {nota} 🏆×{n}` + link), "Jogar de novo".
- [ ] Rodar local + capturas Playwright (desktop 1280 e celular 390) de cada tela; mostrar ao dev; ajustar.
- [ ] Commit `feat: tela da carreira com draft, temporadas e card`.
