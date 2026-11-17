import pytest
from webkit import make_client

from geral.games.carreira import regras
from geral.games.carreira.codigo import decodificar

API = "/api/jogos/carreira"
CRAQUE = {"nome": "Zé", "camisa": 10, "posicao": "atacante", "pe": "direito", "clube": "bahia"}


@pytest.fixture
def game(store, mailer, clock):
    return make_client(store, mailer, clock)


def _comeco(game, edicao="geral") -> dict:
    oferta = game.post(f"{API}/{edicao}/oferta", json={"clube": CRAQUE["clube"]})
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


@pytest.mark.parametrize("edicao", ["xyz", "vasco"])  # one edition only: geral
def test_edicao_desconhecida_e_404(game, edicao) -> None:
    assert game.post(f"{API}/{edicao}/oferta", json={}).status_code == 404
    pedido = _comeco(game) | {"escolhas": []}
    assert game.post(f"{API}/{edicao}/simular", json=pedido).status_code == 404


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


def test_pagina_unica_com_todos_os_clubes_brasileiros(game) -> None:
    page = game.get("/jogos/carreira")

    assert page.status_code == 200
    assert '"bahia"' in page.text and '"abc"' in page.text and '"vasco"' in page.text


@pytest.mark.parametrize("edicao", ["vasco", "abc", "xyz"])
def test_edicao_de_time_redireciona_para_a_unica(game, edicao) -> None:
    page = game.get(f"/jogos/carreira/{edicao}", follow_redirects=False)

    assert page.status_code in (301, 308) and page.headers["location"] == "/jogos/carreira"


def test_modo_completo_comeca_com_o_dia_a_dia(game) -> None:
    pedido = _comeco(game) | {"semente": "fixa", "escolhas": [], "modo": "completa"}

    corpo = game.post(f"{API}/geral/simular", json=pedido).json()

    pendente = corpo["carreira"]["pendente"]
    assert pendente["tipo"] == "dia" and pendente["info"]
    assert decodificar_ok(game, pedido)


def decodificar_ok(game, pedido) -> bool:
    """A Completa career replays from its share code (the mode goes in the code)."""
    escolhas: list[int] = []
    while not (c := game.post(f"{API}/geral/simular", json=pedido | {"escolhas": escolhas}).json())[
        "codigo"
    ]:
        escolhas.append(0)
    aberto = decodificar(c["codigo"])
    return aberto.entrada.modo == "completa" and len(c["codigo"]) < 2000


def test_oferta_de_quem_comeca_no_abc_traz_idolos_do_nordeste(game) -> None:
    corpo = game.post(f"{API}/geral/oferta", json={"clube": "abc"}).json()

    assert sum(x["regiao"] == "nordeste" for x in corpo["lendas"]) >= 2


def test_pagina_sabe_o_tipo_de_cada_taca(game) -> None:
    import json
    import re

    page = game.get("/jogos/carreira").text
    jogo = json.loads(re.search(r'id="cr-data">(.*?)</script>', page, re.S).group(1))

    assert jogo["tacas"]["Brasileirão"] == "liga"
    assert jogo["tacas"]["Copa do Brasil"] == "copa"
    assert jogo["tacas"]["Libertadores"] == "continental"
    assert jogo["tacas"]["Campeonato Potiguar"] == "estadual"
    assert jogo["tacas"]["Copa do Nordeste"] == "nordeste"
    assert jogo["tacas"]["Copa do Mundo"] == "mundo"
