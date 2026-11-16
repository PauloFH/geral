import base64
import zlib

import pytest
from test_carreira_motor import ate_o_fim, entrada

from geral.games.carreira.codigo import (
    CodigoInvalido,
    Resumo,
    codificar,
    decodificar,
    resumir,
)
from geral.games.carreira.dados import carregar
from geral.games.carreira.motor import simular


def test_career_code_reopens_the_exact_career() -> None:
    dados = carregar()
    carreira, e = ate_o_fim(entrada("k1"))

    codigo = codificar(dados.versao, "geral", e, resumir(e, carreira))
    aberto = decodificar(codigo)

    assert aberto.versao == dados.versao and aberto.edicao == "geral"
    assert simular(dados, "geral", aberto.entrada) == carreira
    assert len(codigo) < 2000 and "=" not in codigo


def test_old_code_after_data_change_shows_the_card_summary() -> None:
    carreira, e = ate_o_fim(entrada("k2"))
    resumo = resumir(e, carreira)

    aberto = decodificar(codificar("00000000", "geral", e, resumo))

    assert aberto.versao != carregar().versao
    assert (
        aberto.resumo
        == resumo
        == Resumo(
            nome="Zé",
            posicao="atacante",
            rotulo=carreira.final.rotulo,
            nota=carreira.final.nota,
            titulos=sum(carreira.final.titulos.values()),
            clubes=carreira.final.clubes,
        )
    )


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.mark.parametrize(
    "codigo",
    [
        "",
        "%%%não é base64%%%",
        _b64(b"lixo sem zlib"),
        _b64(zlib.compress(b'{"v": "1", "e": ')),  # JSON truncado
        _b64(zlib.compress(b'{"v": "1"}')),  # campos faltando
        "A" * 2001,
    ],
)
def test_codigo_adulterado_e_codigo_invalido(codigo) -> None:
    with pytest.raises(CodigoInvalido):
        decodificar(codigo)
