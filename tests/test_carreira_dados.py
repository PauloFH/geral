from pathlib import Path

import pytest

from geral.games.carreira import regras
from geral.games.carreira.dados import PASTA, carregar

FORTE_NO_ATAQUE = {a: 1 for a in regras.ATRIBUTOS} | {"finalizacao": 99}


def test_pesos_somam_um_por_posicao() -> None:
    assert set(regras.PESOS) == set(regras.POSICOES)
    for posicao, pesos in regras.PESOS.items():
        assert set(pesos) == set(regras.ATRIBUTOS), posicao
        assert sum(pesos.values()) == pytest.approx(1)


def test_geral_pondera_pela_posicao() -> None:
    assert regras.geral(FORTE_NO_ATAQUE, "atacante") > regras.geral(FORTE_NO_ATAQUE, "zagueiro")
    assert regras.geral({a: 99 for a in regras.ATRIBUTOS}, "meia") == 99


def test_carregar_le_os_arquivos_reais() -> None:
    dados = carregar()

    assert len([lenda for lenda in dados.lendas if "geral" in lenda.edicoes]) >= 40
    assert len(dados.ligas) >= 15 and len(dados.clubes) >= 150
    assert len([c for c in dados.clubes.values() if c.liga == "bra-a"]) >= 20
    assert all(c.liga in dados.ligas for c in dados.clubes.values())


def _pasta(tmp_path: Path, lendas: str, mundo: str | None = None) -> Path:
    (tmp_path / "lendas.toml").write_text(lendas, encoding="utf-8")
    real = (PASTA / "mundo.toml").read_text(encoding="utf-8")
    (tmp_path / "mundo.toml").write_text(mundo or real, encoding="utf-8")
    return tmp_path


NOTAS_OK = ", ".join(f"{a} = 50" for a in regras.ATRIBUTOS)


def _lenda(nome: str, notas: str) -> str:
    cabeca = f'[[lenda]]\nnome = "{nome}"\nwikidata = "Q1"\nedicoes = ["geral"]\n'
    return cabeca + f"notas = {{{notas}}}\n"


@pytest.mark.parametrize(
    "notas",
    [NOTAS_OK.replace("velocidade = 50", "velocidade = 100"), NOTAS_OK + ", carisma = 50"],
)
def test_nota_fora_de_1_a_99_ou_atributo_desconhecido_e_erro(tmp_path, notas) -> None:
    lendas = (
        f'[[lenda]]\nnome = "Fulano"\nwikidata = "Q1"\nedicoes = ["geral"]\nnotas = {{{notas}}}\n'
    )

    with pytest.raises(ValueError, match="Fulano"):
        carregar(_pasta(tmp_path, lendas))


def test_clube_com_liga_desconhecida_e_erro(tmp_path) -> None:
    mundo = (
        '[[liga]]\nid = "bra-a"\npais = "Brasil"\ndivisao = 1\nforca = 70\n'
        '[[clube]]\nid = "x"\nnome = "Xis"\nliga = "marte"\nprestigio = 50\n'
    )

    with pytest.raises(ValueError, match="Xis"):
        carregar(_pasta(tmp_path, "", mundo))


def test_versao_muda_quando_um_toml_muda(tmp_path) -> None:
    lendas = _lenda("Fulano", NOTAS_OK)
    antes = carregar(_pasta(tmp_path, lendas)).versao

    depois = carregar(_pasta(tmp_path, lendas.replace("Fulano", "Beltrano"))).versao

    assert antes != depois and len(antes) == 8
