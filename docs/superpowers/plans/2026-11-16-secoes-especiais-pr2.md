# Seções especiais — PR 2 (seções na edição) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** as edições dos times com `specials` trazem uma história do acervo e o "Neste dia", por sorteio, e o dono pode tirá-las na revisão.

**Spec:** `docs/features/secoes-especiais.md` (PR 1 no ar: #52).

## Global Constraints

- História só na edição de **notícias**; "Neste dia" em todas as edições do time.
- Sorteio com semente = rótulo da edição + time (montar de novo dá o mesmo resultado): história com chance 0,8; "Neste dia" com chance 0,7 quando há fato. Sem notícia e sem jogo, a história entra sempre.
- Com seção especial, as notícias vão a no máximo **6** tópicos (hoje 8).
- A história é **reservada** na montagem (`used_label` = rótulo da edição); montar de novo devolve a mesma. Tirada na revisão: `discarded`, nunca volta.
- "Neste dia": fatos com data completa (`AAAA-MM-DD`) das histórias aceitas e não descartadas cujo dia/mês cai entre 3 dias antes e 3 dias depois do envio; texto por template, sem LLM: "Há 92 anos, em 19/08/1934: <summary>".
- Commits `tipo: descrição` em pt-BR, sem trailer.

## Review Focus

- Acervo vazio ou site fora do ar na montagem → a edição sai sem seção, sem erro → `test_build_without_stories_or_page_has_no_section`.
- Montar duas vezes a mesma edição não gasta duas histórias → `test_draw_is_idempotent_per_label`.
- Data sem dia (`1934`) nunca entra no "Neste dia" → `test_on_this_day_needs_a_full_date`.
- Virada de ano (envio em 30/12, fato em 02/01) → `test_on_this_day_window_crosses_the_new_year`.
- Tirar a história na revisão some do e-mail enviado → `test_removed_story_is_not_sent`.

---

### Task 1: Sorteio e "Neste dia" no site
**Files:** `src/geral/web/store.py`, `src/geral/web/app.py`; Test `tests/test_web_stories.py`
**Produces:** `SubscriberStore.draw_story(team, label) -> dict | None`; `on_this_day(team, day: date) -> list[dict]`; `discard_story(story_id)`.
`POST /api/teams/{team}/stories/draw` (`{"label": str}`) → 200 história (`id, kind, title, body, summary, fact_date, source_title, source_url`) ou 204; `GET /api/teams/{team}/stories/on-this-day?day=AAAA-MM-DD` → lista `{date, title, summary}`.
- [ ] testes: `test_draw_reserves_an_unused_story`, `test_draw_is_idempotent_per_label`, `test_draw_skips_rejected_and_discarded`, `test_on_this_day_needs_a_full_date`, `test_on_this_day_window_crosses_the_new_year` → commit `feat: sorteia a história e o neste dia no site`.

### Task 2: Seções na montagem
**Files:** `src/geral/models.py` (`Story`, `Newsletter.story`, `Newsletter.on_this_day: list[str]`), `src/geral/send/recipients.py` (`draw_story`, `on_this_day`), `src/geral/specials/sections.py` (`pick_sections`), `src/geral/pipeline.py`; Test `tests/test_specials_sections.py`
**Produces:** `pick_sections(edition, team, settings, *, draw, facts) -> Sections(story, on_this_day, max_topics)`; `build_newsletter` chama antes de resumir quando `team.specials` e há token; segunda chance de história se não sobrar notícia nem jogo.
- [ ] testes: `test_news_edition_gets_a_story_and_caps_topics_at_6`, `test_pre_and_post_get_only_on_this_day`, `test_draw_is_seeded_by_the_label`, `test_story_is_forced_when_there_is_no_news`, `test_build_without_stories_or_page_has_no_section`, `test_on_this_day_lines_count_the_years` → commit `feat: coloca a história e o neste dia na edição`.

### Task 3: E-mail
**Files:** `src/geral/render/templates/newsletter.html.j2`, `.txt.j2`; Test `tests/test_renderer.py`
Seção "📜 História" depois das notícias (título, texto, "Fonte: <título> (Wikipédia)" com link) e "Neste dia" (lista).
- [ ] `test_story_and_on_this_day_are_rendered` (html e txt) → commit `feat: mostra a história e o neste dia no e-mail`.

### Task 4: Revisão
**Files:** `src/geral/web/app.py`, `templates/revisao.html.j2`; Test `tests/test_web_revisao.py`
`POST /revisao/{id}/historia/tirar` (descarta a história e a tira do rascunho) e `/revisao/{id}/neste-dia/tirar`.
- [ ] `test_review_lists_the_story`, `test_removed_story_is_discarded_and_not_sent` (o `newsletter_json` do rascunho fica sem história), `test_remove_on_this_day` → commit `feat: deixa tirar a história e o neste dia na revisão`.

### Task 5: Fechamento
- [ ] portões; prévia real (`run --stage build` em DRY_RUN para o ABC com o acervo de produção somente leitura); revisão final; PR; merge.
