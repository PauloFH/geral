# Carreira — veredito das torcidas e fábrica de craques — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Veredito por clube no fim da carreira e placar público "Fábrica de craques" por clube de base.

**Architecture:** `final.vereditos` é puro (motor); `web/carreira_placar.py` guarda uma linha por carreira terminada (chave = sha256 do código) numa tabela própria do SQLite do site; o `/simular` registra ao devolver um `final`, com o `RateLimiter` por rede.

**Tech Stack:** Python, sqlite3, FastAPI, JS.

**Spec:** `docs/features/carreira-torcidas.md`

## Global Constraints

- Não tocar em `store.py`; tabela própria como `velha_partidas`.
- Registrar nunca derruba a carreira (erro de banco → loga e segue).
- Commits conventional sem escopo, pt-BR, sem coautoria; visual mostrado antes do commit.

## Review Focus

1. Mesma carreira enviada de novo (retentativa da rede, link reaberto) conta uma vez.
2. Link compartilhado `c/{codigo}` não conta (só o `/simular`).
3. Clube de base fora do Brasil não existe (sempre brasileiro), mas um id desconhecido no placar
   não quebra a listagem.
4. Placar vazio: a seção aparece com um convite, não some nem quebra.

---

### Task 1: Vereditos
- [ ] Testes `test_traidor_quem_vai_direto_para_o_rival`, `test_idolo_campeao_em_branco_e_respeitado`; `Veredito` e `Final.vereditos`.
- [ ] Commit `feat: veredito de cada torcida no fim da carreira`.

### Task 2: Fábrica de craques (banco e API)
- [ ] Testes `test_carreira_terminada_conta_uma_vez_para_o_clube_de_base`, `test_placar_ordena_por_carreiras_com_media_e_lendas`, `test_limite_por_rede_nao_quebra_a_carreira`, `test_resposta_final_traz_a_posicao_do_clube`, `test_link_compartilhado_nao_conta`.
- [ ] `PlacarStore(path).registrar(codigo, clube, nota) -> bool`, `.ranking(limite) -> list[Linha]`, `.posicao(clube) -> (carreiras, posicao)`; `GET /api/jogos/carreira/placar`; `placar` na resposta final.
- [ ] Commit `feat: fábrica de craques da carreira`.

### Task 3: Tela
- [ ] Cartões de veredito no fim, linha "+1 craque formado…", seção Fábrica de craques abaixo do jogo; fotos 1280/390; commit `feat: vereditos e fábrica de craques na tela da carreira`.
