# Revisão das edições — PR 1 (agenda, etapas e rascunho) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cada edição de torcida é montada antes (rascunho no site) e enviada depois, nos horários novos.

**Architecture:** `plan()` passa a dar `build_at` e `send_at` por slot; `due --all` diz a etapa
vencida; `run --stage build` grava o `Newsletter` em JSON na API do site e `run --stage send` o lê,
tira os tópicos marcados e entrega pelo caminho atual. O gatilho da VPS (`~/infra`) repassa a etapa.

**Tech Stack:** Python 3.12, typer, FastAPI + SQLite, httpx + respx, pytest; bash (infra).

**Spec:** `docs/features/revisao-das-edicoes.md`

## Global Constraints

- Notícias e pós-jogo: montagem 08:00, envio 13:00. Pré-jogo: montagem `max(início − 6 h, 08:00)`,
  envio montagem + 2 h; início antes das 11:00 → montagem 18:00 e envio 20:00 da véspera.
- `due --all`: `slug<TAB>kind<TAB>AAAA-MM-DD<TAB>label<TAB>stage`; data = dia do `send_at`.
- `run --stage all` (padrão) mantém o comportamento atual byte a byte.
- Código e logs em inglês; textos ao usuário em pt-BR. Rede só via respx nos testes.
- Commits `tipo: descrição` em pt-BR, uma linha, sem trailer.

## Review Focus

- Rascunho com `MatchStats.statistics` (tuplas) e datas com fuso: o JSON precisa voltar idêntico → `test_newsletter_survives_json_round_trip` (Task 3).
- Tirar todos os tópicos de uma edição sem jogo: `send` não envia e reporta vazio → `test_run_send_all_topics_removed_is_empty` (Task 5).
- API do site fora no `send`: não pode enviar duas vezes nem cair no `all` às cegas → `test_run_send_page_down_sends_nothing` (Task 5).
- Gatilho antigo lendo a 5ª coluna → `test_due_all_stage_is_the_last_column` (Task 2) e deploy do `infra` primeiro (Task 7).
- Reserva de hora em hora no meio da janela de revisão: não pode enviar antes do `send_at` → `test_due_stage_build_window_is_not_send` (Task 2).

---

### Task 1: Horários de montagem e envio na agenda

**Files:** Modify `src/geral/schedule.py`; Test `tests/test_schedule.py`

**Interfaces:** Produces `Slot.build_at: datetime`; `Slot.send_at` = hora do envio. Constantes
`BUILD_TIME = time(8, 0)`, `SEND_TIME = time(13, 0)`, `PRE_GAME_LEAD = timedelta(hours=6)`,
`REVIEW_TIME = timedelta(hours=2)` (pré-jogo), `EARLY_BUILD = time(18, 0)`, `NIGHT_BEFORE = time(20, 0)`.

- [ ] Step 1: testes novos `test_news_and_post_build_at_8_send_at_13`,
  `test_pre_game_builds_6h_before_sends_4h_before` (jogo 21:30 → 15:30/17:30),
  `test_pre_game_build_never_before_8` (jogo 13:00 → 08:00/10:00),
  `test_early_kickoff_pre_game_builds_18h_sends_20h_day_before` (jogo 10:00 → véspera 18:00/20:00).
- [ ] Step 2: atualizar as expectativas dos testes existentes que fixam 08:00 de envio (mudança de
  regra pedida pelo dono, não enfraquecimento); a regra de dias seguidos segue comparando `send_at`.
- [ ] Step 3: `uv run pytest tests/test_schedule.py` → FAIL. Implementar: `_pre_game`/`_post_game`
  devolvem `(build_at, send_at)`; `_nearest_send_time` e `_mondays` usam `SEND_TIME`; notícias e
  pós-jogo têm `build_at = send_at` do mesmo dia às `BUILD_TIME`.
- [ ] Step 4: `uv run pytest` → PASS (inclui `test_edition.py`, `test_due_command.py`). Commit
  `feat: separa a hora de montar da hora de enviar na agenda`.

### Task 2: Etapa vencida e `due --all`

**Files:** Modify `src/geral/schedule.py`, `src/geral/__main__.py` (`due`, `_due_slot`); Test `tests/test_schedule.py`, `tests/test_due_command.py`

**Interfaces:** Produces `Stage = Literal["build", "send"]` e
`due_stage(slots, now, grace=timedelta(hours=3)) -> tuple[Slot, Stage] | None`: entre os eventos
(`build_at`, build) e (`send_at`, send) com `t <= now < t + grace`, o mais recente; empate → send.
`due()` antigo continua para `run --edition auto --stage all`.

- [ ] Step 1: `test_due_stage_build_window_is_not_send` (às 10:00 de uma notícia → build),
  `test_due_stage_send_after_13`, `test_due_all_prints_build_then_send_for_the_same_slot`,
  `test_due_all_stage_is_the_last_column` (`split("\t")[4] == "build"`; edição geral → `all`).
- [ ] Step 2: FAIL → implementar → PASS → commit `feat: diz no due qual etapa da edição venceu`.

### Task 3: Rascunhos no site

**Files:** Modify `src/geral/web/store.py` (SCHEMA + métodos), `src/geral/web/app.py`; Test `tests/test_web_drafts.py`, `tests/test_models.py`

**Interfaces:** tabela `drafts(id INTEGER PK, team, kind, day, label, newsletter_json, build_at,
send_at, held INTEGER DEFAULT 0, removed_topics TEXT DEFAULT '[]', sent_at, UNIQUE(team, kind, day))`.
`SubscriberStore.save_draft(team, kind, day, label, newsletter_json, build_at, send_at) -> bool`
(False se já existe), `.draft(team, kind, day) -> Draft | None`, `.mark_draft_sent(team, kind, day, now)`.
`Draft` dataclass com os campos da tabela (`removed_topics: list[int]`). Rotas da spec, com
`DraftIn(label, newsletter: dict, build_at, send_at)` e `DraftOut(label, newsletter, held, removed_topics, sent_at)`.

- [ ] Step 1: `test_newsletter_survives_json_round_trip` (Newsletter com `last_match.statistics`
  e `edition` com fuso: `model_validate_json(n.model_dump_json()) == n`),
  `test_put_draft_then_get`, `test_put_draft_twice_is_409_and_keeps_first`,
  `test_get_unknown_draft_is_404`, `test_drafts_require_token` (401 sem Bearer),
  `test_unknown_team_is_404`, `test_mark_sent_sets_sent_at`.
- [ ] Step 2: FAIL → implementar → PASS → commit `feat: guarda o rascunho de cada edição no site`.

### Task 4: Cliente da API de rascunhos

**Files:** Modify `src/geral/send/recipients.py`; Test `tests/test_recipients.py`

**Interfaces:** `save_draft(settings, team, edition: Edition, newsletter: Newsletter, build_at, send_at) -> bool`
(False no 409), `fetch_draft(settings, team, kind, day: date) -> DraftOut | None` (None no 404),
`mark_draft_sent(settings, team, kind, day)`. Levantam `httpx.HTTPError` como `latest_edition`.

- [ ] Step 1: testes respx para os três, incluindo 409 → False e 404 → None. FAIL → implementar →
  PASS → commit `feat: fala com a API de rascunhos no envio`.

### Task 5: `run --stage build|send|all`

**Files:** Modify `src/geral/__main__.py` (`run` vira `_build_newsletter` + `_deliver`); Test `tests/test_run_command.py`

**Interfaces:** consome Tasks 2–4. `--stage` aceita `auto|build|send|all` (padrão `all`; `auto` usa
`due_stage`). `_deliver(newsletter, club, settings, report, note)` = trecho atual de `_bolao` em
diante. `build`: sem token → erro como `--publish-only`; já enviada ou rascunho existente → sai 0
sem coletar; senão monta e `save_draft`. `send`: já enviada → sai 0; `fetch_draft`: `HTTPError`
→ sai 2 sem enviar; None → `all` com relatório "sem revisão (rascunho ausente)"; `held` → sai 0,
relatório "segurada na revisão"; senão remove os índices de `removed_topics`, `is_empty` → sai 1,
`_deliver`, `mark_draft_sent`.

- [ ] Step 1: testes `test_run_build_saves_draft_and_sends_nothing` (nenhuma chamada ao Resend),
  `test_run_build_twice_keeps_first_draft` (segunda vez sem LLM), `test_run_send_drops_removed_topics_and_subject_follows_first_kept_topic`,
  `test_run_send_without_draft_builds_and_sends`, `test_run_send_held_draft_sends_nothing`,
  `test_run_send_all_topics_removed_is_empty`, `test_run_send_page_down_sends_nothing`,
  `test_run_send_registers_bolao_only_at_send` (PUT do bolão só no send), `test_send_twice_sends_once`.
- [ ] Step 2: FAIL → refatorar `run` sem mudar os testes atuais → PASS (`uv run pytest`) → commit
  `feat: separa a montagem do envio da edição`.

### Task 6: Workflow

**Files:** Modify `.github/workflows/newsletter.yml`

- [ ] Step 1: input `stage` (choice `all|build|send`, padrão `all`), env `STAGE`; agendado usa
  `auto`; `args+=(--stage "$STAGE")` só no ramo de torcida. Edição geral intocada.
- [ ] Step 2: `uv run ruff check . && uv run pytest` → PASS; commit `ci: repassa a etapa da edição no workflow`.

### Task 7: Gatilho da VPS (repo `~/infra`, branch e PR próprios, sobe antes)

**Files:** Modify `ansible/roles/geral_trigger/files/geral-trigger`; Test `tests/test_geral_trigger.py`

- [ ] Step 1: testes `test_stage_column_is_dispatched`, `test_build_and_send_of_same_label_both_dispatched`
  (chave `team|label|stage`), `test_four_columns_still_dispatch_as_all` (sem 5ª coluna → sem `stage`).
- [ ] Step 2: `read -r -u 3 team kind day label stage`; `stage` vazio não entra no corpo; FAIL → implementar →
  `python -m unittest tests/test_geral_trigger.py` PASS → commit `feat: repassa a etapa da edição no gatilho da geral`.

### Task 8: Fechamento

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pytest`; marcar na página os
  testes do PR 1; PR da Geral cita que o `infra` sobe antes. Aviso de horário novo: dispatch manual
  com `note` na primeira edição de cada torcida (fora do código).
