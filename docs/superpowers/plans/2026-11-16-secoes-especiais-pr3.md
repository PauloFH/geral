# Seções especiais — PR 3 (quinta e aniversários) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** na entressafra, os times com `specials` ganham uma edição de notícias também na quinta; o "Neste dia" passa a trazer o aniversário dos ídolos.

**Spec:** `docs/features/secoes-especiais.md` (PR 1 #52 e PR 2 #53 no ar).

## Global Constraints

- Entressafra = o modo semanal que a agenda já usa (sem jogo em 14 dias, ou depois do último jogo conhecido). Times com `specials`: segunda **e quinta** às 13:00 (montagem 08:00); os demais seguem só segunda.
- Mínimo de 72 h entre edições continua valendo.
- Aniversário: só ídolos que passaram no filtro de ídolo do acervo; data de nascimento do Wikidata (P569) com precisão de dia; linha "Há 74 anos, em 13/07/1952: nascia Osni Lopes." (nome sem o "(futebolista)").
- O job atualiza os aniversários no domingo (e sempre que coleta trechos).
- Commits `tipo: descrição` em pt-BR, sem trailer.

## Review Focus

- Thursday logo depois de um jogo de domingo: o mínimo de 72 h segura → `test_thursday_respects_the_72h_gap`.
- Time sem `specials` não muda → `test_teams_without_specials_keep_mondays_only`.
- Data só com ano no Wikidata não entra → `test_birthday_needs_day_precision`.
- Ídolo sem item no Wikidata → ignorado, sem erro → coberto no mesmo teste.

---

### Task 1: Quinta na agenda
**Files:** `src/geral/schedule.py` (`plan(..., weekdays=(0,))`, `_mondays` → `_weekly`), `src/geral/teams.py` (`Team.news_weekdays`), `src/geral/edition.py`, `src/geral/__main__.py` (todas as chamadas de `plan`); Test `tests/test_schedule.py`, `tests/test_teams.py`
- [ ] `test_specials_get_monday_and_thursday_in_the_offseason`, `test_thursday_respects_the_72h_gap`, `test_teams_without_specials_keep_mondays_only` → commit `feat: edição de quinta na entressafra para times com seções especiais`.

### Task 2: Aniversários
**Files:** `sources.py` (`Passage.qid` via `pageprops`), `src/geral/specials/birthdays.py` (`birthdays(client, passages) -> list[dict]`), `job.py` (domingo: coleta e envia), `recipients.py` (`save_birthdays`), `store.py` + `app.py` (`idol_birthdays`, `PUT /api/teams/{team}/birthdays`, `on_this_day` junta os aniversários); Test `tests/test_specials_birthdays.py`, `tests/test_web_stories.py`, `tests/test_specials_job.py`
- [ ] `test_birthday_needs_day_precision`, `test_on_this_day_includes_idol_birthdays`, `test_job_saves_birthdays_on_sunday` → commit `feat: aniversários dos ídolos no neste dia`.

### Task 3: Fechamento
- [ ] portões; revisão final; PR; merge.
