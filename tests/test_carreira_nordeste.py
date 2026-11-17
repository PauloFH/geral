from pathlib import Path

import pytest

from geral.games.carreira.dados import PASTA, carregar


def test_todo_clube_brasileiro_tem_estado_e_estadual() -> None:
    dados = carregar()
    brasileiros = [c for c in dados.clubes.values() if dados.ligas[c.liga].pais == "Brasil"]

    assert all(c.estado in dados.estados for c in brasileiros), [
        c.id for c in brasileiros if c.estado not in dados.estados
    ]
    assert dados.estados["RN"].campeonato == "Campeonato Potiguar"
    assert dados.regiao(dados.clubes["abc"]) == "nordeste"
    assert dados.regiao(dados.clubes["flamengo"]) == "sudeste"
    assert {"america-rn", "treze", "sampaio-correa", "ferroviario"} <= set(dados.clubes)
    assert dados.clubes["america-rn"].liga == "bra-d"


def test_classicos_com_nome() -> None:
    dados = carregar()

    assert dados.classico(dados.clubes["abc"]) == ("Clássico-Rei", dados.clubes["america-rn"])
    assert dados.classico(dados.clubes["nautico"])[0] == "Clássico dos Clássicos"
    assert dados.classico(dados.clubes["real-madrid"]) is None


def _copia(tmp_path: Path, troca: str) -> Path:
    for f in PASTA.glob("*.toml"):
        texto = f.read_text(encoding="utf-8")
        if f.name == "mundo.toml":
            texto += troca
        (tmp_path / f.name).write_text(texto, encoding="utf-8")
    return tmp_path


def test_classico_com_clube_desconhecido_e_erro(tmp_path) -> None:
    with pytest.raises(ValueError, match="Clássico Fantasma"):
        carregar(
            _copia(tmp_path, '\n[[classico]]\nnome = "Clássico Fantasma"\nclubes = ["abc", "x"]\n')
        )
