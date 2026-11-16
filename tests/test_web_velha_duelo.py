import pytest
from webkit import make_client

from geral.games.velha.base import answers, load
from geral.games.velha.board import parse_board

API = "/api/jogos/velha"


@pytest.fixture
def game(store, mailer, clock):
    return make_client(store, mailer, clock)


def new_board(game):
    found = game.get(f"{API}/tabuleiro").json()
    return found, parse_board(load(), found["codigo"])


def test_duel_page_has_the_board_and_the_clock(game) -> None:
    page = game.get("/jogos/velha/duelo")

    assert page.status_code == 200
    assert page.text.count('class="vcell"') == 9 and 'data-seconds="30"' in page.text
    assert 'id="jd-start"' in page.text  # nothing runs before "Começar"
    assert page.text.count('class="duel-name"') == 2  # a score per player, not per cell
    assert "Jogador 1 é X e começa" in page.text


@pytest.mark.parametrize(
    "path, current", [("/jogos/velha", "Solo do dia"), ("/jogos/velha/duelo", "Duelo")]
)
def test_both_modes_offer_the_choice_between_solo_and_duel(game, path, current) -> None:
    modes = game.get(path).text.split('class="velha-modes"', 1)[1].split("</nav>", 1)[0]

    assert 'href="/jogos/velha"' in modes and 'href="/jogos/velha/duelo"' in modes
    assert f'aria-current="page">{current}<' in modes


def test_new_board_gives_six_labels_and_a_code(game) -> None:
    found, board = new_board(game)

    assert found["linhas"] == [c.label for c in board.rows]
    assert found["colunas"] == [c.label for c in board.cols]


def test_duel_judge_returns_the_state_with_names(game) -> None:
    found, board = new_board(game)
    right = answers(load(), *board.cell(4))[0]

    state = game.post(
        f"{API}/duelo",
        json={"tabuleiro": found["codigo"], "jogadas": [{"casa": 4, "jogador": right.id}]},
    ).json()

    assert state["casas"] == {"4": "X"} and state["vez"] == "O"
    assert state["nomes"] == {right.id: right.nome}


@pytest.mark.parametrize("problem", ["code", "taken", "after"])
def test_duel_judge_rejects_bad_boards_and_moves_with_422(game, problem) -> None:
    found, board = new_board(game)
    first = answers(load(), *board.cell(0))[0].id
    code = found["codigo"]
    moves = [{"casa": 0, "jogador": first}]
    if problem == "code":
        code = "clube:Q1|cor:azul"
    elif problem == "taken":
        moves.append({"casa": 0, "jogador": first})
    else:
        moves = [{"estouro": True}] * 7  # six dry turns end it; the seventh is too late
    response = game.post(f"{API}/duelo", json={"tabuleiro": code, "jogadas": moves})
    assert response.status_code == 422
