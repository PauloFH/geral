# Seções especiais — PR 1 (acervo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** um job abastece, por torcida com `specials`, um acervo de histórias verificadas no site, sem efeito nas edições.

**Architecture:** pacote `geral.specials`: `sources` (trechos da Wikipédia pt, cada um com chave
única), `writer` (Gemini escreve só a partir do trecho), `verifier` (sem LLM) e `job` (abastece pela
API do site). O site guarda as histórias na tabela `stories`. Workflow `acervo.yml` diário (22:00).

**Tech Stack:** Python 3.12, httpx + respx, pydantic, FastAPI + SQLite, Gemini via `LLMClient`.

**Spec:** `docs/features/secoes-especiais.md`

## Global Constraints

- História: 120–180 palavras, pt-BR, título, `summary` de uma linha, `fact_date` (`AAAA-MM-DD`, `AAAA` ou vazio), `kind` ∈ `jogo|idolo|clube`.
- O prompt diz: use só o trecho, sem fatos de fora. O verificador recusa número, ano, data ou nome próprio ausente do trecho.
- Abastecer até **10 não usadas** por torcida; rodar quando houver `< 8` não usadas ou for domingo. No máximo 20 chamadas ao Gemini por torcida por rodada.
- Fonte já vista (aceita ou recusada) não é reusada: chave `"<url>#<seção>"`.
- Wikimedia: `User-Agent` com a URL do repo, uma chamada por vez (`mediawiki.api`).
- Commits `tipo: descrição` em pt-BR, uma linha, sem trailer.

## Review Focus

- Trecho curto demais (seção de 2 linhas) vira história inventada → `test_short_passages_are_skipped` (< 80 palavras não vai ao Gemini).
- Ano por extenso na fonte ("mil novecentos…") ou "1934" na fonte e "34" na história → o verificador compara dígitos; `test_verifier_rejects_a_year_not_in_the_source` e `test_verifier_ignores_case_and_accents`.
- "Ídolo" de outro clube (Garrincha cita o ABC) → `test_idol_needs_idolo_near_the_club_name`.
- Gemini fora do ar no meio da rodada: o que já foi aceito fica gravado, o job sai com 0 e reporta → `test_job_keeps_what_it_wrote_when_the_llm_fails`.
- Site fora do ar: o job não chama o Gemini → `test_job_without_the_page_writes_nothing`.

---

### Task 1: Catálogo
**Files:** `src/geral/teams.py`, `src/geral/teams.toml`; Test `tests/test_teams.py`
**Produces:** `Team.specials: bool = False`, `Team.wikipedia: str | None`, `Team.classics: tuple[str, ...] = ()`, `Team.club_terms: tuple[str, ...] = ()` (termos de proximidade do ídolo).
ABC: `wikipedia = "ABC Futebol Clube"`, `classics = ["Clássico-Rei"]`, `club_terms = ["ABC", "alvinegro"]`.
Náutico: `wikipedia = "Clube Náutico Capibaribe"`, `classics = ["Clássico dos Clássicos", "Clássico das Emoções (Pernambuco)"]`, `club_terms = ["Náutico", "Timbu", "alvirrubro"]`. Ambos `specials = true`.
- [ ] `test_specials_teams_have_a_wikipedia_article` (todo `specials` tem `wikipedia`) → commit `feat: marca no catálogo os times com seções especiais`.

### Task 2: Verificador
**Files:** Create `src/geral/specials/__init__.py`, `src/geral/specials/verifier.py`; Test `tests/test_specials_verifier.py`
**Produces:** `unsupported(story: str, source: str, allowed: Iterable[str] = ()) -> list[str]`: devolve os
números (sequências de dígitos) e nomes próprios (palavra com inicial maiúscula fora do início de
frase, ignorando uma lista curta de palavras comuns: meses, "O", "A", "Em", "No", "Na"…) da história
que não aparecem no trecho, comparando sem caixa e sem acento; `allowed` = nome do time, newsletter, torcida.
- [ ] `test_verifier_accepts_names_and_dates_in_the_source`, `test_verifier_rejects_a_year_not_in_the_source`,
  `test_verifier_rejects_a_name_not_in_the_source`, `test_verifier_ignores_case_and_accents`,
  `test_verifier_allows_the_team_names` → FAIL → implementar → PASS → commit `feat: verifica a história contra a fonte`.

### Task 3: Fontes
**Files:** Create `src/geral/specials/sources.py`; Test `tests/test_specials_sources.py` (respx, textos curtos de fixture)
**Produces:** `Passage(kind, key, title, url, text)` (pydantic); `passages(client, team) -> list[Passage]`:
- texto puro por `prop=extracts&explaintext=1` (pt.wikipedia), dividido nos títulos `== X ==`/`=== X ===`;
- `clube`: seções do artigo do clube cujo título casa com `Símbolos|Mascote|Estádio|Sede|Torcida|Hino|Uniforme`;
- `jogo`: subseções `===` de `História` do artigo do clube e seções das páginas de `classics` que casam com `jogos? históricos?|goleadas|primeiro jogo|final`;
- `idolo`: artigos de `list=search` com `"ídolo" linksto:"<wikipedia>"` cujo texto tem "ídolo" a até 150 caracteres de um `club_terms`; trecho = introdução + seção `Carreira` (até 600 palavras);
- trechos com menos de 80 palavras ficam de fora; `key = f"{url}#{seção}"`.
- [ ] `test_club_sections_become_clube_passages`, `test_history_subsections_become_jogo_passages`,
  `test_idol_needs_idolo_near_the_club_name`, `test_short_passages_are_skipped` → commit `feat: coleta trechos da Wikipédia para o acervo`.

### Task 4: Escrita
**Files:** Create `src/geral/specials/writer.py`, `src/geral/prompts/story.md`; Test `tests/test_specials_writer.py`
**Produces:** `StoryDraft(title, body, summary, fact_date: str = "")`; `write_story(passage, team, llm) -> StoryDraft`
(prompt com o trecho e as regras globais; `kind` vem do trecho, não do modelo).
- [ ] `test_prompt_carries_only_the_passage_and_the_rules` (FakeLLMClient; prompt contém o trecho e "Use apenas"),
  `test_story_draft_keeps_the_passage_kind_and_source` → commit `feat: escreve a história a partir do trecho`.

### Task 5: Acervo no site
**Files:** `src/geral/web/store.py`, `src/geral/web/app.py`; Test `tests/test_web_stories.py`
**Produces:** tabela `stories(id, team, kind, title, body, summary, fact_date, source_url, source_title, source_key, created_at, rejected_reason, used_label, discarded INTEGER DEFAULT 0, UNIQUE(team, source_key))`.
`POST /api/teams/{team}/stories` (`StoryIn`: campos + `rejected_reason: str | None`) → 204, 409 se a chave já existe;
`GET /api/teams/{team}/stories/sources` → lista de `source_key`; `GET /api/teams/{team}/stories/count` → `{"unused": n}`
(aceitas, não usadas, não descartadas). Token como as demais; time desconhecido → 404.
- [ ] `test_post_story_then_count`, `test_rejected_story_does_not_count`, `test_same_source_twice_is_409`,
  `test_stories_require_token`, `test_sources_list_every_key_seen` → commit `feat: guarda o acervo de histórias no site`.

### Task 6: Job e workflow
**Files:** Create `src/geral/specials/job.py`; Modify `src/geral/send/recipients.py` (cliente da API de histórias), `src/geral/__main__.py` (`geral acervo`), Create `.github/workflows/acervo.yml`; Test `tests/test_specials_job.py`
**Produces:** `top_up(team, settings, llm, client, today: date) -> TopUpReport(accepted, rejected, skipped_reason)`;
`geral acervo --team <slug> | --all` (todos os `specials`). Workflow: `cron: "7 1 * * *"` (22:07 de Brasília), `workflow_dispatch` com `team`; segredos `GEMINI_API_KEY`, `SUBSCRIBERS_API_TOKEN`, var `PUBLIC_URL`.
Ordem das fontes: intercalar tipos (`jogo, idolo, clube, …`), embaralhadas com semente do dia.
- [ ] `test_job_tops_up_to_10_and_skips_used_sources`, `test_job_does_nothing_with_8_or_more_unless_sunday`,
  `test_job_records_rejections_with_the_reason`, `test_job_keeps_what_it_wrote_when_the_llm_fails`,
  `test_job_without_the_page_writes_nothing` → commit `feat: abastece o acervo de histórias toda noite`.

### Task 7: Fechamento
- [ ] portões verdes; rodada real local em `DRY_RUN` para ABC e Náutico (sem gravar), contando aceitas e recusadas; marcar testes na página; revisão final; PR; merge.
