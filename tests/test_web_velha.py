from datetime import UTC, datetime, time, timedelta

import pytest
from webkit import make_client

from geral.games import calendario
from geral.games.velha.base import answers, load
from geral.games.velha.diario import LAUNCH, daily_board

DAY = datetime.combine(LAUNCH + timedelta(days=7), time(15, 0), tzinfo=UTC)  # board #8
API = "/api/jogos/velha"


@pytest.fixture
def game(store, mailer, clock):
    clock.now = DAY
    return make_client(store, mailer, clock)


def board(number: int = 8):
    base = load()
    frozen = calendario.answers(calendario.load(), "velha", "geral")
    return base, daily_board(base, number, frozen)


def test_velha_page_shows_the_six_categories(game) -> None:
    _, today = board()

    page = game.get("/jogos/velha").text

    assert 'data-number="8"' in page and 'data-archive="0"' in page
    for cat in (*today.rows, *today.cols):
        assert cat.label in page
    assert page.count('class="cell"') == 9


def test_player_search_finds_by_name_without_accents_and_hides_where_it_fits(game) -> None:
    found = game.get(f"{API}/jogadores", params={"q": "romario"}).json()

    assert found and found[0]["nome"] == "Romário"
    assert set(found[0]) == {"id", "nome", "anos", "posicao"}
    assert found[0]["posicao"] == "Atacante" and found[0]["anos"] == "1985–2009"
    assert game.get(f"{API}/jogadores", params={"q": "r"}).json() == []


def test_solo_api_fills_a_cell_and_names_it(game) -> None:
    base, today = board()
    right = answers(base, *today.cell(4))[0]
    wrong = next(p for p in base.players.values() if p not in answers(base, *today.cell(0)))

    verdict = game.post(
        f"{API}/geral/8",
        json={"chutes": [{"casa": 0, "jogador": wrong.id}, {"casa": 4, "jogador": right.id}]},
    ).json()

    assert verdict["casas"] == {"4": right.id}
    assert verdict["acertos"] == [False, True]
    assert verdict["nomes"][right.id] == right.nome
    assert not verdict["over"] and verdict["revelacao"] is None


def test_solo_api_reveals_at_the_end(game) -> None:
    base, today = board()
    picks = [{"casa": c, "jogador": answers(base, *today.cell(c))[0].id} for c in range(9)]
    # The most famous of a cell may also fit another one already taken: pick distinct players.
    used: set[str] = set()
    for pick in picks:
        pick["jogador"] = next(
            p.id for p in answers(base, *today.cell(pick["casa"])) if p.id not in used
        )
        used.add(pick["jogador"])

    verdict = game.post(f"{API}/geral/8", json={"chutes": picks}).json()

    assert verdict["over"] and len(verdict["revelacao"]) == 9
    top = verdict["revelacao"][0]["top"][0]
    assert verdict["nomes"][top["id"]] == top["nome"]


@pytest.mark.parametrize(
    "chutes",
    [
        [{"casa": 0, "jogador": "Q12897"}, {"casa": 0, "jogador": "Q12897"}],
        [{"casa": 0, "jogador": "Q0"}],
        [{"casa": 9, "jogador": "Q12897"}],
    ],
)
def test_solo_api_rejects_taken_cell_and_unknown_player_with_422(game, chutes) -> None:
    if len(chutes) == 2:  # the first must fill cell 0 for the second to hit a taken cell
        base, today = board()
        chutes[0]["jogador"] = answers(base, *today.cell(0))[0].id
    assert game.post(f"{API}/geral/8", json={"chutes": chutes}).status_code == 422


@pytest.mark.parametrize("number", [0, 9])
def test_solo_api_future_number_is_404(game, number) -> None:
    response = game.post(f"{API}/geral/{number}", json={"chutes": []})
    assert response.status_code == 404


def test_a_past_board_has_its_own_page_and_today_redirects(game) -> None:
    _, past = board(3)

    page = game.get("/jogos/velha/geral/3")
    redirect = game.get("/jogos/velha/geral/8", follow_redirects=False)

    assert page.status_code == 200 and 'data-archive="1"' in page.text
    assert all(cat.label in page.text for cat in (*past.rows, *past.cols))
    assert redirect.status_code == 307 and redirect.headers["location"] == "/jogos/velha"
    assert 'href="/jogos/velha/geral/7"' in game.get("/jogos/velha").text


@pytest.mark.parametrize("path", ["/jogos/velha/vasco", "/jogos/velha/geral/abc"])
def test_velha_has_no_team_edition(game, path) -> None:
    assert game.get(path).status_code == 404


def test_velha_is_listed_with_the_other_games(game) -> None:
    assert 'href="/jogos/velha"' in game.get("/jogos").text
    assert "Jogo da velha" in game.get("/jogos/craque-do-dia").text  # the tabs
