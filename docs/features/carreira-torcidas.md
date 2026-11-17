# Carreira: o veredito das torcidas e a fábrica de craques

- **Data:** 2026-11-16
- **Status:** proposta
- **ADRs:** —
- **Projeto 3 de 5** (base → Nordeste → **veredito das torcidas** → capa da Geral → desafio).

## Objetivo

Duas coisas que só a Geral, feita de torcidas, faz: no fim da carreira **cada clube por onde o
craque passou dá um veredito** (ídolo, campeão, passou em branco, traidor…), e toda carreira
terminada conta para o **clube que a formou** num placar público, a **Fábrica de craques**: quem
começa no ABC joga pelo ABC, e o ABC sobe no placar ao lado de Flamengo e Palmeiras.

## Fora de escopo

- Conta, login ou nome do torcedor no placar; ranking de jogadores; prêmio.
- Integrar com o placar das torcidas da página inicial (assinaturas): é outro número.

## Contratos

- **Veredito** (`final.py`, `vereditos(dados, temporadas) -> list[Veredito]`, um por clube na
  ordem da carreira; `Final.vereditos`). Regras, a primeira que casar:
  1. **Traidor**: saiu dele direto para o rival de clássico (`dados.classicos`).
  2. **Ídolo**: ≥ 5 temporadas e (≥ 2 títulos ou ≥ 60 gols) — ou ≥ 3 títulos.
  3. **Campeão**: ≥ 1 título.
  4. **Passou em branco**: < 25 jogos no total.
  5. **Respeitado**: o resto.
  `Veredito(clube, temporadas, jogos, gols, titulos: int, veredito, frase)`; a frase é da torcida
  ("A torcida do ABC nunca vai esquecer", "No América-RN, esse nome não se fala").
- **Fábrica de craques** (`web/carreira_placar.py`, tabela própria no mesmo SQLite, como o duelo
  do jogo da velha; não toca no `store.py`):
  `carreira_placar(codigo_hash TEXT PRIMARY KEY, clube TEXT, nota INT, lenda INT, criada_em TEXT)`.
  - Conta quando o `/simular` devolve um `final`: `codigo_hash` = sha256 do código compartilhável,
    então repetir a mesma carreira não conta duas vezes. Limite por rede (o `RateLimiter` e o
    `network()` que já existem): no máximo 60 carreiras contadas por hora por rede; acima disso
    a carreira funciona, só não conta.
  - **Lenda** = nota final ≥ 85.
  - Ordem do placar: **carreiras formadas** (quantas vezes a torcida jogou pelo clube), com nota
    média e lendas ao lado. Só clubes com ≥ 1 carreira.
  - `GET /api/jogos/carreira/placar` → `[{clube, nome, carreiras, media, lendas, posicao}]` (top
    20) e a resposta do `/simular` com `final` ganha `placar: {clube, carreiras, posicao}` do clube
    de partida ("+1 craque formado pelo ABC · 14º lugar").
- **Tela**: no fim, os vereditos como cartões por clube (selo colorido: ídolo dourado, campeão
  verde, traidor vermelho, em branco cinza) e a linha "+1 craque formado pelo ABC — 14º na
  Fábrica de craques"; abaixo do jogo, a seção **Fábrica de craques** (top 10, com o clube do
  torcedor destacado se ele acabou de jogar).

## Critérios de aceite (como testes)

- [ ] `test_traidor_quem_vai_direto_para_o_rival` (ABC → América-RN).
- [ ] `test_idolo_campeao_em_branco_e_respeitado`.
- [ ] `test_carreira_terminada_conta_uma_vez_para_o_clube_de_base` (a mesma carreira duas vezes = 1).
- [ ] `test_placar_ordena_por_carreiras_com_media_e_lendas`.
- [ ] `test_limite_por_rede_nao_quebra_a_carreira` (61ª da hora: 200, não conta).
- [ ] `test_resposta_final_traz_a_posicao_do_clube`.

## Verificação ponta a ponta

Servidor local: 3 carreiras no ABC e 1 no Flamengo pela tela; a seção mostra ABC 3 × 1 Flamengo;
fotos (1280 e 390) do fim com os vereditos e da Fábrica de craques, para o dev aprovar o visual.
