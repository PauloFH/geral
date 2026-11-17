# Carreira — realismo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline).

**Goal:** Draft com 3 lendas + 7 jogadores reais e 2 sorteios; carreira que pode não decolar (distribuição equilibrada).
**Spec:** `docs/features/carreira-realismo.md`

## Global Constraints
- Commits conventional sem escopo, pt-BR, sem coautoria; portões antes de cada commit.
- Nota dos jogadores da base: fórmula determinística pelo id (nada sorteado por carreira).
- Calibrar por teste de distribuição, nunca afrouxando os limites do desenho.

## Review Focus
1. Jogador da base com nome igual a uma lenda curada (mesmo wikidata) não aparece duas vezes.
2. Base sem jogadores da posição/região pedida: a oferta completa com outros, nunca quebra.
3. Códigos antigos (versão antiga) seguem abrindo pelo resumo.

### Task 1: Draft com jogadores reais e 2 sorteios
- [ ] Testes de oferta, nota por fama/posição, Nordeste, mediana do draft humano; `jogadores.py`; `oferta` com 10; tela com 2 sorteios e selo lenda/jogador.
- [ ] Commit `feat: draft da carreira com lendas e jogadores reais e dois sorteios`.

### Task 2: Realização, forma, lesão e risco
- [ ] Testes de distribuição, temporada ruim, lesão; motor; calibrar.
- [ ] Commit `feat: carreiras que podem não decolar`.
