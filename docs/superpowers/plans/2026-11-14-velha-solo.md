# Jogo da velha — PR 2 (solo diário) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Play the daily jogo da velha solo on the portal: one board per day, the same for everyone,
with player search, past games, share grid and streak, like the other daily games.

**Architecture:** Pure logic in `geral/games/velha/` (`diario.py` for the daily board and its
calendar freeze, `busca.py` for the search) over PR 1's `base.py`/`board.py`/`judge.py`; stateless
routes in `web/app.py` reusing `which_puzzle`, `game_tabs` and `games()`; Jinja page
`velha.html.j2`, vanilla `static/geral/velha.js`, styles in `jogos.css`.

**Tech Stack:** FastAPI, Jinja2, vanilla JS, pytest + TestClient (`tests/webkit.py`).

**Spec:** `docs/features/jogo-da-velha.md` (section "Solo"). Stacked on PR 1 (#45, `feat/velha-base`).

## Global Constraints

- No change to `store.py`, the bolão or the Urubu migration; no club names in `src/geral` code.
- No per-team edition: the only edition is `geral` (no edition nav on the page).
- Stateless server: the browser sends the whole history each time; picks and streak live in
  `localStorage` per game (as the other games).
- Visual: same "placar" language as the other games (yellow lamps on black, concrete); show the page
  running (desktop 1280 px and phone 390 px screenshots) to the dev **before** committing Task 4.
- Commits `tipo: descrição`, one line, no trailers; tests never hit the network.

## Decisions

- **Address:** the site's pattern, not the spec's `/jogos/velha[/{n}]`: `/jogos/velha`,
  `/jogos/velha/geral` and `/jogos/velha/geral/{n}`; API `POST /api/jogos/velha/geral/{n}`. Reason:
  `which_puzzle`, `game_tabs`, `/jogos` and the past-games tests all assume `/{jogo}/{edição}/{n}`.
- **Daily board:** #n is the frozen code `calendario.json["velha"]["geral"][n-1]` when there is one,
  else `make_board(base, random.Random(f"velha:{n}"))`. `congelar_calendario.py` also freezes velha.
  `LAUNCH = date(2026, 11, 14)`: set to the deploy day when merging (no later, or two days share #1).
- **Countries stay:** `scripts/import_base.py` keeps every country of the previous `base.json`
  (append-only `paises`), so a frozen board with a country never stops parsing (PR 1 review).
- **Search:** `GET /api/jogos/velha/jogadores?q=` → up to 10 `{id, nome, anos, posicao}`; matches
  every word of `q` (accents and case ignored) as the start of a word of `nome` or `completo`; most
  famous first; `q` under 2 letters → `[]`. Never says where a player fits.
- **Answer of the API:** `SoloVerdict` plus `nomes: {id: nome}` for the players on the board and in
  the reveal (the page shows names, the judge works with ids). `GuessError` → 422.
- **Share:** `Jogo da velha #n · 7/9 em 10 chutes` then the 3×3 grid of 🟩 (filled) and ⬜.

## Review Focus

- Today's board must not change mid-day when `base.json` changes (frozen until tomorrow) (Task 1).
- A frozen board whose category left `clubes.toml`/`paises` must not 500 the page (Task 1).
- Search with "joao" must find "João"; with a registered name ("Edson Arantes") must find Pelé (Task 2).
- A number in the future or 0 → 404, today's number → redirect, like the other games (Task 3).
- A history with a guess on a taken cell or an unknown id → 422, never 500 (Task 3).

### Task 1: daily board and calendar (`velha/diario.py`, `calendario.py`, `import_base.py`)
- **Produces:** `LAUNCH`, `puzzle_number(day) -> int`, `daily_board(base, number, frozen:
  list[str]) -> Board`; `calendario.freeze_velha(path, base, until)`.
- [ ] `test_daily_board_follows_the_frozen_calendar` (frozen code for #3 on the synthetic base;
      `daily_board(other_base, 3, frozen)` is still that board), `test_daily_board_without_freeze_is_the_seeded_one`,
      `test_frozen_board_with_a_vanished_category_falls_back_to_the_seeded_one`,
      `test_freeze_velha_keeps_numbers_already_frozen` (tmp calendar), `test_import_keeps_the_countries_of_the_previous_base`
      (`importacao.keep_countries(old: dict, new: dict) -> dict`).
- [ ] Implement; `congelar_calendario.freeze_until_tomorrow` calls `freeze_velha(…, velha.load(), until)`.
      Commit `feat: daily jogo da velha board frozen in the calendar`.

### Task 2: player search (`velha/busca.py`)
- **Produces:** `search(base, q: str, limit: int = 10) -> list[Player]`.
- [ ] `test_search_ignores_accents_and_case`, `test_search_matches_word_starts_in_nome_or_completo`
      ("edson ara" → Pelé via `completo`; "ele" does not find Pelé), `test_search_puts_the_famous_first_and_stops_at_ten`,
      `test_search_needs_two_letters`. Implement with `onde_jogou.normalize`. Commit
      `feat: search the jogo da velha players by name`.

### Task 3: routes (`web/app.py`)
- [ ] `tests/test_web_velha.py` (clock at `LAUNCH + 7 days` → #8):
      `test_player_search_finds_by_name_without_accents_and_hides_where_it_fits` (keys exactly
      `id, nome, anos, posicao`), `test_solo_api_fills_a_cell_and_names_it`,
      `test_solo_api_rejects_taken_cell_and_unknown_player_with_422`,
      `test_solo_api_future_number_is_404`, `test_velha_page_shows_the_six_categories`;
      `test_web_jogos_anteriores.GAMES` gains `"velha"` (skip the `vasco` redirect case for it:
      no team edition → its own test that `/jogos/velha/vasco` is 404).
- [ ] Routes: `velha_editions()` = `{"geral": base}` (lazy, like `career_state`), `velha_number()`,
      the page (3 routes), the search and the judge; `games()` gains
      `{"path": "velha", "name": "Jogo da velha", "desc": "Três linhas, três colunas: ache um jogador para cada cruzamento em até 12 chutes."}`.
      Commit `feat: jogo da velha routes`.

### Task 4: page, script and portal card
- [ ] `test_intervalo_cards_share_one_layout` expects 5 cards; `/jogos` lists "Jogo da velha".
- [ ] `velha.html.j2` (tabs, archive note, board: corner + 3 column heads + 3 row heads as lamps,
      9 cells as buttons; picker with search box and results; result box with share and stats;
      past games; credit Wikipédia/Wikidata), `velha.js` (state per number in `localStorage`, debounce
      250 ms on search, POST the whole `chutes` on each pick, mark hits/misses, reveal at the end),
      `jogos.css` for the 4×4 grid (cells square, same size; phone: grid fits 390 px).
- [ ] Run locally, screenshots 1280/390 (start, mid-game, end with reveal) → show the dev, adjust,
      then commit `feat: play the daily jogo da velha on the portal`.

## Verification

`uv run ruff check . && uv run ruff format --check . && uv run pytest`; local play to the end on
desktop and phone width; one fresh-context review of the branch; PR stacked on #45.
