# Jogo da velha — PR 3 (duelo no mesmo PC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Two people play X against O on the same screen: a fresh board, 30 s per turn, three in
a row wins.

**Architecture:** The duel rules live in Python (`geral/games/velha/duelo.py`), a pure replay of
the moves like the solo judge, so PR 4 (duel by link) reuses them with a server clock. The page
`/jogos/velha/duelo` keeps the moves and runs the 30 s clock in the browser and asks the server
to judge the whole history after each move.

**Tech Stack:** FastAPI, Jinja2, vanilla JS, pytest + TestClient.

**Spec:** `docs/features/jogo-da-velha.md` ("Duelo no mesmo PC" and the duel rules under "Duelo
por link"). Stacked on PR 2 (`feat/velha-solo`).

## Global Constraints

- No account, no server state for this mode; no change to `store.py`, bolão, Urubu.
- Same look as the solo page (cards, plates, search dialog); screenshots desktop/phone to the dev
  before committing the page.
- Commits `tipo: descrição`, one line, no trailers; tests never hit the network.

## Decisions

- **Rules on the server (deviation from the spec's `confere`):** instead of
  `POST /api/jogos/velha/confere {linha, coluna, jogador, usados} → {vale}` with turn, clock and
  score in the browser, `POST /api/jogos/velha/duelo {tabuleiro, jogadas}` replays the whole history
  and returns the state. Reason: one tested judge for PR 3 and PR 4; the browser only keeps the
  moves and the clock. A move is `{casa, jogador}` or `{estouro: true}` (the 30 s ran out).
- **Rules (from the spec):** X starts; a wrong player, a player already on the board (by anyone) or
  a timeout passes the turn; a right one takes the cell. Three in a row wins at once. The game also
  ends on a full board or after 6 turns in a row without a cell taken (misses and timeouts count);
  then most cells wins, same count = empate. Taken cell, unknown player, move after the end → 422.
- **Fresh board:** `GET /api/jogos/velha/tabuleiro` → `{codigo, linhas: [label…], colunas: […]}`
  from `make_board(base, random.Random())` (not the daily one). The page asks for one on load and
  on "Nova partida"; the code goes back with every judge call (`parse_board`, bad code → 422).
- **Clock:** 30 s per turn in the browser (`DUEL_SECONDS = 30` passed to the page); at 0 the page
  sends `{estouro: true}`. Paused while the search dialog is closed? No: the clock runs during the
  turn, dialog open or not (the duel is about speed).

## Review Focus

- A player used by X cannot be used by O (and vice versa) (Task 1).
- Three in a row that also fills the board is a win, not a count of cells (Task 1).
- The 6th turn in a row without a cell ends the game; a cell taken resets the count (Task 1).
- `/jogos/velha/duelo` must not be read as an edition named "duelo" (route order) (Task 2).
- A tampered board code or a 7th+ move after the end → 422, never 500 (Task 2).

### Task 1: duel judge (`velha/duelo.py`)
- **Produces:** `Move(casa: int | None = None, jogador: str | None = None, estouro: bool = False)`;
  `DuelState(casas: dict[int, Literal["X","O"]], jogadores: dict[int, str], vez: Literal["X","O"],
  acertos: list[bool], sem_casa: int, over: bool, vencedor: Literal["X","O","empate"] | None,
  linha: list[int] | None)`; `judge_duel(base, board, jogadas: list[Move]) -> DuelState`;
  `MAX_DRY_TURNS = 6`.
- [ ] Tests: `test_duel_x_starts_and_a_right_answer_takes_the_cell`,
      `test_duel_wrong_answer_or_timeout_passes_the_turn`, `test_duel_player_used_by_the_other_is_a_miss`,
      `test_duel_three_in_a_row_wins_and_later_moves_are_rejected`,
      `test_duel_full_board_without_a_line_goes_to_most_cells_or_empate`,
      `test_duel_ends_after_six_turns_without_a_cell_and_most_cells_wins`,
      `test_duel_rejects_taken_cell_unknown_player_and_move_without_cell`. Implement on top of
      `fits` and `GuessError` from `judge.py`. Commit `feat: judge the jogo da velha duel`.

### Task 2: routes
- [ ] `tests/test_web_velha_duelo.py`: board endpoint gives 6 labels and a code that parses;
      judge endpoint returns the state with `nomes`; tampered code and taken cell → 422;
      `/jogos/velha/duelo` is 200 with 9 cells and the clock seconds. Routes declared before
      `/jogos/velha/{edition}`. Commit `feat: jogo da velha duel routes`.

### Task 3: page and script
- [ ] `velha_duelo.html.j2` (tabs, title, scoreboard "X 2 × 1 O" with whose turn and the clock,
      the board with X/O stamps and names, the same search dialog, result with "Nova partida"),
      `velha-duelo.js` (moves in memory only; clock with `requestAnimationFrame`/`setInterval`,
      sends `estouro` at 0; one move in flight at a time; the dialog closes on a right pick).
      Link "Duelo" from the solo page and the `/jogos` card. Screenshots → dev → commit
      `feat: play the jogo da velha duel on one screen`.

## Verification

`uv run ruff check . && uv run ruff format --check . && uv run pytest`; Playwright: a duel to a
win, one miss and one timeout; desktop and phone screenshots; fresh-context review; PR on PR 2.
