"""Every game explains its rules in a small dialog (opened by "?"), not in fixed text."""

from datetime import UTC, datetime

import pytest
from webkit import make_client

DAY = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
PAGES = {
    "/jogos/craque-do-dia": "craque-do-dia",
    "/jogos/onde-jogou": "onde-jogou",
    "/jogos/quem-e": "quem-e",
    "/jogos/velha": "velha",
    "/jogos/velha/duelo": "velha-duelo",
}


@pytest.fixture
def game(store, mailer, clock):
    clock.now = DAY
    return make_client(store, mailer, clock)


@pytest.mark.parametrize("path, key", PAGES.items())
def test_rules_live_in_a_dialog_opened_by_a_question_mark(game, path, key) -> None:
    page = game.get(path).text

    assert f'<dialog class="game-dialog rules" id="regras" data-game="{key}"' in page
    assert 'class="rules-open"' in page and "/static/geral/regras.js" in page
    rules = page.split('id="regras"', 1)[1].split("</dialog>", 1)[0]
    assert 3 <= rules.count("<li>") <= 5  # short
    assert 'class="lead"' not in page and "Amanhã tem outro" not in page


def test_a_team_edition_says_its_stints_come_lit(game) -> None:
    rules = game.get("/jogos/onde-jogou/vasco").text.split('id="regras"', 1)[1]
    assert "Vasco" in rules.split("</dialog>", 1)[0]
