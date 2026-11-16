# Carreira — modos Rápida e Completa — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Modo Completa (dia a dia com % por temporada, mercado só com aceite), modo Rápida com "chegou de", edição única e tela nova.

**Architecture:** O motor ganha `modo`; a rotina vira um terceiro tipo de pergunta, consumindo a mesma lista `escolhas` (prefixo estável: o sorteio do resultado acontece depois da resposta). No Completa, `_mercado` vira pergunta em vez de mover. A tela é reescrita sobre os mesmos dados.

**Tech Stack:** Python, pydantic, TOML, JS sem framework, CSS.

**Spec:** `docs/features/carreira-modos.md` (e `docs/features/carreira.md` para o motor)

## Global Constraints

- Commits conventional sem escopo, pt-BR, sem coautoria; portões antes de cada commit.
- Mesma entrada → mesma carreira; resposta nova nunca muda temporada passada.
- Visual mostrado rodando (1280 e 390) antes do commit da tela.

## Review Focus

1. Chance mostrada = chance usada (o bônus de atributo entra nos dois lugares, de uma fonte só).
2. Completa com 30+ respostas: o código compartilhável continua < 2.000 caracteres.
3. Dispensa e volta de empréstimo no Completa sempre com manchete que diz para onde foi.
4. Link antigo (`modo` ausente) continua abrindo como Rápida.
5. Atributo somado não passa de 99 nem fica abaixo de 1.

---

### Task 1: Motor com modos, dia a dia e mercado com aceite
**Files:** `carreira/dados.py`, `carreira/motor.py`, `carreira/rotina.toml` (10 situações para começar), `tests/test_carreira_modos.py`
- [ ] Testes: `test_completa_pergunta_o_dia_a_dia_toda_temporada`, `test_completa_nao_troca_de_clube_sem_aceite`, `test_chance_do_dia_a_dia_bate_com_o_sorteio`, `test_efeito_de_atributo_muda_a_nota_da_temporada_seguinte`, `test_rapida_mostra_de_onde_veio_quem_chegou`, `test_prefixo_estavel_nos_dois_modos`.
- [ ] `Efeito.atributos: dict[str, int]`; `Rotina(id, texto, condicao, opcoes: (OpcaoRotina(texto, chance, bonus, sucesso: Efeito, fracasso: Efeito)))`; `chance_de(opcao, notas) -> int` (0–100, usada pelo motor e pela resposta da API).
- [ ] `Escolha.tipo`, `opcoes_info: list[{chance, efeitos}]`; `Temporada.chegou_de`, `Temporada.rotina`.
- [ ] Commit `feat: modo completo da carreira com dia a dia e mercado com aceite`.

### Task 2: 30+ situações de dia a dia
**Files:** `rotina.toml`, `tests/test_carreira_variedade.py`
- [ ] `test_toda_rotina_e_alcancavel` (inclui sucesso e fracasso de cada opção com chance entre 1 e 99).
- [ ] Commit `feat: situações de dia a dia da carreira`.

### Task 3: Edição única
**Files:** `web/app.py`, `carreira.html.j2`, `tests/test_web_carreira.py`
- [ ] `test_edicao_de_time_redireciona_para_a_unica`; `/api/.../{edição}` aceita só `geral`; `games()` com só `geral`; `modo` no `CarreiraIn`.
- [ ] Commit `feat: carreira com edição única e escolha de modo`.

### Task 4: Tela nova
**Files:** `carreira.html.j2`, `carreira.js`, `jogos.css`
- [ ] Topo fixo, temporada em destaque, linha do tempo, cartões de decisão com barra de chance, Rápida automática (~1,8 s) e Completa por botão.
- [ ] Playwright nos dois modos e tamanhos; mostrar ao dev; commit `feat: tela nova da carreira com os dois modos`.
