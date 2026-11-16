import pytest
from webkit import make_client

from geral.games.carreira import regras
from geral.games.carreira.codigo import decodificar
from geral.teams import load_teams

API = "/api/jogos/carreira"
CRAQUE = {"nome": "Zé", "camisa": 10, "posicao": "atacante", "pe": "direito", "clube": "bahia"}


@pytest.fixture
def game(store, mailer, clock):
    return make_client(store, mailer, clock)


def _comeco(game, edicao="geral") -> dict:
    oferta = game.post(f"{API}/{edicao}/oferta", json={})
    assert oferta.status_code == 200
    corpo = oferta.json()
    lendas = corpo["lendas"]
    assert len(lendas) == 9 and all(set(x["notas"]) == set(regras.ATRIBUTOS) for x in lendas)
    roubos = [
        {"lenda": lenda["nome"], "atributo": a}
        for lenda, a in zip(lendas, regras.ATRIBUTOS, strict=False)
    ]
    return {"semente_draft": corpo["semente_draft"], "craque": CRAQUE, "roubos": roubos}


def test_oferta_e_simulacao_ate_o_fim(game) -> None:
    pedido = _comeco(game) | {"escolhas": []}

    for _ in range(10):
        resposta = game.post(f"{API}/geral/simular", json=pedido)
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        pedido["semente"] = corpo["semente"]  # the server drew it on the first call
        if corpo["carreira"]["final"]:
            break
        assert corpo["codigo"] is None
        pedido["escolhas"].append(0)

    final = corpo["carreira"]["final"]
    assert final["rotulo"] and corpo["codigo"]
    assert decodificar(corpo["codigo"]).resumo.rotulo == final["rotulo"]
    assert corpo["carreira"]["temporadas"][0]["clube"] == "Bahia"


def test_mesma_semente_mesma_carreira(game) -> None:
    pedido = _comeco(game) | {"semente": "fixa", "escolhas": []}

    primeira = game.post(f"{API}/geral/simular", json=pedido).json()

    assert game.post(f"{API}/geral/simular", json=pedido).json() == primeira


def test_edicao_desconhecida_e_404(game) -> None:
    assert game.post(f"{API}/xyz/oferta", json={}).status_code == 404
    pedido = _comeco(game) | {"escolhas": []}
    assert game.post(f"{API}/xyz/simular", json=pedido).status_code == 404


def test_edicao_de_time_comeca_na_base_dele(game) -> None:
    pedido = _comeco(game, "vasco") | {"escolhas": []}

    corpo = game.post(f"{API}/vasco/simular", json=pedido).json()

    assert corpo["carreira"]["temporadas"][0]["clube"] == "Vasco"


def test_hidden_team_has_no_career_edition(store, mailer, clock) -> None:
    catalog = load_teams()
    escondido = catalog["vasco"].model_copy(update={"listed": False})
    game = make_client(store, mailer, clock, teams=catalog | {"vasco": escondido})

    assert game.post(f"{API}/vasco/oferta", json={}).status_code == 404


def test_roubo_invalido_escolha_fora_e_escolha_sobrando_sao_422(game) -> None:
    pedido = _comeco(game) | {"semente": "fixa", "escolhas": []}
    ruim = dict(pedido, roubos=[*pedido["roubos"][:7], pedido["roubos"][0]])
    assert game.post(f"{API}/geral/simular", json=ruim).status_code == 422

    escolhas: list[int] = []
    while not (c := game.post(f"{API}/geral/simular", json=pedido | {"escolhas": escolhas}).json())[
        "carreira"
    ]["final"]:
        escolhas.append(0)
    sobrando = game.post(f"{API}/geral/simular", json=pedido | {"escolhas": [*escolhas, 0]})
    assert sobrando.status_code == 422 and "detail" in sobrando.json()
    if escolhas:
        fora = game.post(f"{API}/geral/simular", json=pedido | {"escolhas": [7]})
        assert fora.status_code == 422
    assert c["codigo"]


def test_nome_longo_e_422(game) -> None:
    pedido = _comeco(game) | {"escolhas": []}
    pedido["craque"] = CRAQUE | {"nome": "x" * 25}

    assert game.post(f"{API}/geral/simular", json=pedido).status_code == 422


def _codigo(game) -> tuple[str, dict]:
    pedido = _comeco(game) | {"semente": "fixa", "escolhas": []}
    while not (corpo := game.post(f"{API}/geral/simular", json=pedido).json())["codigo"]:
        pedido["escolhas"].append(0)
    return corpo["codigo"], corpo["carreira"]["final"]


def test_pagina_da_carreira_por_edicao(game) -> None:
    geral = game.get("/jogos/carreira")
    vasco = game.get("/jogos/carreira/vasco")

    assert geral.status_code == vasco.status_code == 200
    assert '"bahia"' in geral.text and '"bahia"' not in vasco.text  # starting clubs: geral only
    assert game.get("/jogos/carreira/xyz").status_code == 404


def test_link_do_card_reabre_a_carreira(game) -> None:
    codigo, final = _codigo(game)

    page = game.get(f"/jogos/carreira/c/{codigo}")

    assert page.status_code == 200
    assert final["rotulo"] in page.text and "Zé" in page.text


def test_link_de_versao_velha_mostra_o_resumo(game) -> None:
    from geral.games.carreira.codigo import codificar

    codigo, final = _codigo(game)
    velho = decodificar(codigo)
    codigo_velho = codificar("00000000", velho.edicao, velho.entrada, velho.resumo)

    page = game.get(f"/jogos/carreira/c/{codigo_velho}")

    assert page.status_code == 200 and final["rotulo"] in page.text and "Jogar a sua" in page.text


def test_link_invalido_e_404(game) -> None:
    assert game.get("/jogos/carreira/c/nao-e-um-codigo").status_code == 404


def test_carreira_aparece_em_jogos_sem_numero_do_dia(game) -> None:
    page = game.get("/jogos")

    assert "Carreira" in page.text and "/jogos/carreira" in page.text
    assert "#None" not in page.text
