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


def _carreiras(clube: str, n: int, prefixo: str):
    from test_carreira_modos import jogar
    from test_carreira_motor import entrada

    for i in range(n):
        yield jogar(entrada(f"{prefixo}{i}", clube=clube))[0]


def test_estadual_favorece_o_grande_do_estado() -> None:
    def taxa(clube: str) -> float:
        temporadas = [
            t
            for c in _carreiras(clube, 120, clube)
            for t in c.temporadas
            if t.clube_id == clube and t.jogos >= 10
        ]
        return sum("Campeonato Potiguar" in t.titulos for t in temporadas) / len(temporadas)

    assert taxa("abc") > 2 * taxa("globo") > 0


def test_um_estadual_por_temporada_e_so_do_proprio_estado() -> None:
    dados = carregar()
    nomes = {e.campeonato: uf for uf, e in dados.estados.items()}
    for c in _carreiras("abc", 80, "e"):
        for t in c.temporadas:
            estaduais = [x for x in t.titulos if x in nomes]
            assert len(estaduais) <= 1
            if estaduais:
                assert dados.clubes[t.clube_id].estado == nomes[estaduais[0]]


def test_copa_do_nordeste_so_para_nordestinos() -> None:
    dados = carregar()
    vistas = 0
    for clube in ("sport", "flamengo", "bahia"):
        for c in _carreiras(clube, 80, f"n{clube}"):
            for t in c.temporadas:
                if "Copa do Nordeste" in t.titulos:
                    vistas += 1
                    assert dados.regiao(dados.clubes[t.clube_id]) == "nordeste"
    assert vistas > 0


def test_classico_aparece_com_nome_na_manchete() -> None:
    manchetes = [t.manchete for c in _carreiras("abc", 120, "k") for t in c.temporadas]

    assert any("Clássico-Rei" in m for m in manchetes)
    assert not any("{" in m for m in manchetes)
