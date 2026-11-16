# Revisão das edições — PR 2 (página de revisão) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** o dono recebe um e-mail por rascunho e, numa página com link assinado, segura/solta a
edição e tira/devolve tópicos; solto depois do horário, ela sai em até 10 min.

**Spec:** `docs/features/revisao-das-edicoes.md` (PR 1 no ar: #50).

## Global Constraints

- Link `REVIEW_PURPOSE = "review"`, assinado para `NOTIFY_EMAIL`, vale 7 dias; sem `NOTIFY_EMAIL`, 404.
- Rascunho enviado (`sent_at`): toda ação → 409 "já saiu". Segurado e vencido: tudo permitido.
- Soltar depois de `send_at` → `due --all` lista `…<TAB>release` (sem limite de 3 h), uma vez por
  soltura; não vale se já saiu edição mais nova da torcida (409 ao soltar).
- Banco em produção já tem `drafts`: coluna nova `released_at` entra por `ALTER TABLE` idempotente.
- Textos ao dono em pt-BR; commits `tipo: descrição` em pt-BR, sem trailer.

## Review Focus

- Token de outra finalidade (pedidos, descadastro) não abre a revisão → `test_review_page_rejects_token_of_other_purpose`.
- Banco antigo sem `released_at` → `test_store_adds_released_at_to_an_old_drafts_table`.
- Tirar tópico por índice fora da lista → 404, sem gravar → `test_remove_unknown_topic_is_404`.
- Soltar depois que saiu edição mais nova → 409 → `test_release_after_a_newer_edition_is_409`.
- E-mail ao dono falhando não derruba o PUT do rascunho → `test_draft_saved_even_if_the_notice_fails`.

---

### Task 1: Ações no banco
**Files:** `src/geral/web/store.py`; Test `tests/test_web_drafts.py`
**Produces:** `Draft.released_at`; `pending_drafts() -> list[Draft]` (não enviados, por `send_at`);
`draft_by_id(id)`; `set_held(id, held: bool, now) -> Draft | None` (soltar grava `released_at`);
`set_topic_removed(id, n, removed: bool) -> Draft | None`; `released_due(now) -> list[Draft]`
(solto, não enviado, `released_at >= send_at`, `send_at <= now`).
- [ ] testes `test_hold_then_release_records_released_at`, `test_remove_and_restore_topic`,
  `test_released_due_lists_only_late_releases`, `test_store_adds_released_at_to_an_old_drafts_table`
  → FAIL → implementar → PASS → commit `feat: guarda as decisões da revisão no rascunho`.

### Task 2: Página `/revisao`
**Files:** `src/geral/web/app.py`, `src/geral/web/templates/revisao.html.j2`, `revisao_previa` via render; Test `tests/test_web_revisao.py`
**Produces:** `GET /revisao?t=`; `GET /revisao/{id}/previa?t=` (HTML do e-mail sem os tópicos tirados,
sem card do bolão); `POST /revisao/{id}/segurar|soltar`, `POST /revisao/{id}/topicos/{n}/tirar|voltar`
com `t` no formulário → 303 `/revisao?t=`. `no-store` e `no-referrer`.
- [ ] testes `test_review_page_lists_pending_drafts`, `test_review_page_rejects_token_of_other_purpose`,
  `test_review_page_rejects_expired_token`, `test_hold_and_release_from_the_page`,
  `test_remove_topic_from_the_page_hides_it_in_the_preview`, `test_remove_topic_after_sent_is_409`,
  `test_remove_unknown_topic_is_404`, `test_release_after_a_newer_edition_is_409`
  → FAIL → implementar → PASS → commit `feat: abre a página de revisão das edições`.

### Task 3: E-mail ao dono
**Files:** `src/geral/web/app.py` (no `PUT …/drafts`); Test `tests/test_web_revisao.py`
- [ ] `test_saving_a_draft_emails_the_owner_the_review_link` (assunto "Revisar: <newsletter> — <label>, sai às HH:MM",
  link `/revisao?t=` válido), `test_draft_saved_even_if_the_notice_fails` → commit `feat: avisa o dono de cada rascunho`.

### Task 4: Soltar depois do horário e janela
**Files:** `src/geral/__main__.py`, `.github/workflows/newsletter.yml`; Test `tests/test_due_command.py`, `tests/test_run_stages.py`
**Produces:** `due --all` imprime `released_due` como `slug<TAB>kind<TAB>day<TAB>label<TAB>release`;
`run --stage release` = `send` com a edição tirada do próprio rascunho (`--edition kind --date day`);
workflow aceita `release`. Janela: `edition.start = min(start, _built_before(último envio real))`.
- [ ] `test_released_draft_after_send_at_is_due_for_send`, `test_run_release_sends_the_draft_of_that_day`,
  `test_next_window_starts_at_last_real_send` → commit `feat: envia a edição solta depois do horário`.

### Task 5: Fechamento
- [ ] portões verdes; marcar na página os testes; revisão final da branch; PR; merge.
