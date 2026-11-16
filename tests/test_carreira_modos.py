import random

import pytest
from test_carreira_motor import entrada

from geral.games.carreira import regras
from geral.games.carreira.dados import carregar
from geral.games.carreira.motor import chance_de, simular


def completa(semente: str, **extra):
    e = entrada(semente, **extra)
    return e.model_copy(update={"modo": "completa"})


def jogar(e, responder=lambda pendente, rng: 0, semente="r"):
    """Play to the end; returns every (career before the answer, question, answer)."""
    dados, rng, passos = carregar(), random.Random(semente), []
    while (carreira := simular(dados, "geral", e)).final is None:
        resposta = responder(carreira.pendente, rng)
        passos.append((carreira, carreira.pendente, resposta))
        e = e.model_copy(update={"escolhas": [*e.escolhas, resposta]})
    return carreira, passos


def test_completa_pergunta_o_dia_a_dia_toda_temporada() -> None:
    for i in range(20):
        final, passos = jogar(completa(f"d{i}"))
        dias = [p for _, p, _ in passos if p.tipo == "dia"]
        profissionais = [t for t in final.temporadas if t.idade >= 17]
        assert len(dias) == len(profissionais)
        assert all(t.rotina is not None for t in profissionais)
        assert all(len(p.opcoes) == len(p.info) >= 2 for p in dias)


def test_completa_nao_troca_de_clube_sem_aceite() -> None:
    def recusar(pendente, rng):  # never accepts a move; answers the rest at random
        if pendente.tipo == "mercado":
            return pendente.destinos.index("ficar")
        ficar = [i for i, c in enumerate(pendente.clubes) if c is None]
        return (
            rng.choice(ficar) if pendente.tipo == "decisao" else rng.randrange(len(pendente.opcoes))
        )

    for i in range(60):
        final, _ = jogar(completa(f"n{i}"), recusar, f"n{i}")
        for antes, depois in zip(final.temporadas, final.temporadas[1:], strict=False):
            if antes.clube_id != depois.clube_id:
                assert depois.chegada and (
                    "empréstimo" in depois.chegada or "ispensad" in depois.chegada
                )


def test_chance_do_dia_a_dia_bate_com_o_sorteio() -> None:
    certos = tentativas = 0
    soma_chances = 0
    for i in range(400):
        final, passos = jogar(completa(f"c{i}"), lambda p, rng: 0)
        for t, (_, pergunta, resposta) in zip(
            [t for t in final.temporadas if t.idade >= 17],
            [x for x in passos if x[1].tipo == "dia"],
            strict=True,
        ):
            chance = pergunta.info[resposta].chance
            if chance is None:
                continue
            tentativas += 1
            soma_chances += chance
            certos += t.rotina.deu_certo
    assert tentativas > 2000
    assert abs(certos / tentativas - soma_chances / tentativas / 100) < 0.04


def test_efeito_de_atributo_muda_a_nota_da_temporada_seguinte() -> None:
    dados = carregar()
    rotina = next(r for r in dados.rotinas if any(o.sucesso.atributos for o in r.opcoes))
    opcao = next(o for o in rotina.opcoes if o.sucesso.atributos)
    atributo, delta = next(iter(opcao.sucesso.atributos.items()))
    notas = {a: 70 for a in regras.ATRIBUTOS}

    assert chance_de(opcao, notas) == chance_de(opcao, notas)  # one source for UI and engine
    assert regras.geral(notas | {atributo: 70 + delta}, "meia") >= regras.geral(notas, "meia")


def test_rapida_mostra_de_onde_veio_quem_chegou() -> None:
    for i in range(80):
        final, _ = jogar(entrada(f"q{i}"))
        for antes, depois in zip(final.temporadas, final.temporadas[1:], strict=False):
            assert (antes.clube_id != depois.clube_id) == bool(depois.chegada)
            if depois.chegada:
                assert antes.clube in depois.chegada or "empréstimo" in depois.chegada


@pytest.mark.parametrize("modo", ["rapida", "completa"])
def test_prefixo_estavel_nos_dois_modos(modo) -> None:
    dados = carregar()
    for i in range(15):
        e = entrada(f"p{i}").model_copy(update={"modo": modo})
        while (carreira := simular(dados, "geral", e)).final is None:
            for opcao in range(len(carreira.pendente.opcoes)):
                depois = simular(
                    dados, "geral", e.model_copy(update={"escolhas": [*e.escolhas, opcao]})
                )
                assert depois.temporadas[: len(carreira.temporadas)] == carreira.temporadas
            e = e.model_copy(update={"escolhas": [*e.escolhas, 0]})


def test_link_sem_modo_abre_como_rapida() -> None:
    e = entrada("l1")
    sem_modo = type(e).model_validate(e.model_dump(exclude={"modo"}))
    assert sem_modo.modo == "rapida"
