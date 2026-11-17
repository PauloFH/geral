from pathlib import Path

import pytest

from geral.games.carreira import regras
from geral.games.carreira.dados import PASTA, carregar
from geral.games.carreira.draft import JogadaInvalida, Roubo, edicoes, montar, oferta


def _dados_com_vasco(tmp_path: Path):
    real = (PASTA / "lendas.toml").read_text(encoding="utf-8")
    notas = ", ".join(f"{a} = 70" for a in regras.ATRIBUTOS)
    proprias = "".join(
        f'[[lenda]]\nnome = "{n}"\nwikidata = "Q{i}"\nedicoes = ["vasco"]\nnotas = {{{notas}}}\n'
        for i, n in enumerate(["Cria Um", "Cria Dois"])
    )
    sem_vasco = real.replace('"geral", "vasco"', '"geral"').replace(', "vasco"', "")
    (tmp_path / "lendas.toml").write_text(sem_vasco + proprias, encoding="utf-8")
    (tmp_path / "mundo.toml").write_text((PASTA / "mundo.toml").read_text(encoding="utf-8"))
    return carregar(tmp_path)


def _roubos(ofertadas, de=range(8)) -> list[Roubo]:
    return [
        Roubo(lenda=ofertadas[i].nome, atributo=a)
        for i, a in zip(de, regras.ATRIBUTOS, strict=True)
    ]


def test_oferta_e_estavel_e_tem_dez_sem_repetir() -> None:
    dados = carregar()

    primeira = oferta(dados, "geral", "abc")

    assert primeira == oferta(dados, "geral", "abc")
    assert len(primeira) == 10 and len({lenda.nome for lenda in primeira}) == 10
    assert primeira != oferta(dados, "geral", "xyz")


def test_edicoes_so_times_com_lenda_propria(tmp_path) -> None:
    assert edicoes(_dados_com_vasco(tmp_path), ["xyz", "vasco"]) == ["geral", "vasco"]


def test_montar_devolve_as_notas_roubadas() -> None:
    ofertadas = oferta(carregar(), "geral", "abc")

    notas = montar(ofertadas, _roubos(ofertadas))

    assert notas == {a: ofertadas[i].notas[a] for i, a in enumerate(regras.ATRIBUTOS)}


def test_a_reserva_pode_substituir_uma_lenda() -> None:
    ofertadas = oferta(carregar(), "geral", "abc")

    notas = montar(ofertadas, _roubos(ofertadas, de=[8, 1, 2, 3, 4, 5, 6, 7]))

    assert notas["velocidade"] == ofertadas[8].notas["velocidade"]


@pytest.mark.parametrize(
    "estraga",
    [
        lambda r, o: [Roubo(lenda="Ninguém", atributo="passe"), *r[1:]],  # fora da oferta
        lambda r, o: [*r[:7], Roubo(lenda=r[7].lenda, atributo=r[0].atributo)],  # atributo 2x
        lambda r, o: r[:7],  # faltando
        lambda r, o: [*r, Roubo(lenda=o[8].nome, atributo="passe")],  # nove
        lambda r, o: [*r[:7], Roubo(lenda=o[0].nome, atributo=r[7].atributo)],  # lenda 2x
        lambda r, o: [*r[:7], Roubo(lenda=r[7].lenda, atributo="carisma")],  # atributo inexistente
    ],
)
def test_steal_outside_offer_or_repeated_attribute_is_invalid(estraga) -> None:
    ofertadas = oferta(carregar(), "geral", "abc")

    with pytest.raises(JogadaInvalida):
        montar(ofertadas, estraga(_roubos(ofertadas), ofertadas))
