from test_carreira_variedade import _temporada

from geral.games.carreira.dados import carregar
from geral.games.carreira.final import vereditos


def _anos(clube_id: str, nome: str, de: int, ate: int, **extra):
    return [_temporada(i, nome, clube_id, **extra) for i in range(de, ate)]


def test_traidor_quem_vai_direto_para_o_rival() -> None:
    temporadas = _anos("abc", "ABC", 16, 20) + _anos("america-rn", "América-RN", 20, 30)

    v = vereditos(carregar(), temporadas)

    assert [x.clube for x in v] == ["ABC", "América-RN"]
    assert v[0].veredito == "Traidor" and "ABC" in v[0].frase


def test_idolo_campeao_em_branco_e_respeitado() -> None:
    temporadas = (
        _anos("sport", "Sport", 16, 22, titulos=["Campeonato Pernambucano"])
        + _anos("bahia", "Bahia", 22, 24, titulos=[], jogos=40, gols=3)
        + [_temporada(24, "Getafe", "getafe", jogos=10, titulos=[])]
        + [_temporada(25, "Vasco", "vasco", jogos=20, titulos=["Campeonato Carioca"])]
    )

    v = {x.clube: x for x in vereditos(carregar(), temporadas)}

    assert v["Sport"].veredito == "Ídolo" and v["Sport"].titulos == 6
    assert v["Bahia"].veredito == "Respeitado"
    assert v["Getafe"].veredito == "Passou em branco"
    assert v["Vasco"].veredito == "Campeão"
    assert all(x.frase for x in v.values())
