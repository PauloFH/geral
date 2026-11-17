import random
import statistics

from geral.games.carreira import regras
from geral.games.carreira.dados import carregar
from geral.games.carreira.draft import OFERTA, oferta
from geral.games.carreira.jogadores import jogadores_da_base, notas_do_jogador
from geral.games.velha.base import Player


def _player(pid="Q1", posicao="atacante", fama=10) -> Player:
    return Player(pid, "Fulano", "2001–2015", (posicao,), (), fama, frozenset(), False, False)


def test_oferta_tem_tres_lendas_e_sete_jogadores_reais() -> None:
    dados = carregar()
    for i in range(50):
        nomes = oferta(dados, "geral", f"o{i}", "flamengo")
        assert OFERTA == len(nomes) == 10 and len({x.nome for x in nomes}) == 10
        assert sum(x.tipo == "lenda" for x in nomes) == 3
        assert all(x.resumo for x in nomes if x.tipo == "jogador")
    curadas = {x.wikidata for x in dados.lendas}
    assert not curadas & {x.wikidata for x in jogadores_da_base(dados)}


def test_nota_de_jogador_da_base_segue_fama_e_posicao() -> None:
    atacante = notas_do_jogador(_player())
    assert atacante == notas_do_jogador(_player())  # the same player, the same ratings
    assert atacante["finalizacao"] > atacante["marcacao"] + 20
    zagueiro = notas_do_jogador(_player("Q2", "zagueiro"))
    assert zagueiro["marcacao"] > zagueiro["finalizacao"] + 20

    def nivel(fama: int) -> float:
        return statistics.mean(notas_do_jogador(_player(f"Q{fama}", "meio-campo", fama)).values())

    assert nivel(1) < nivel(10) < nivel(80)
    assert all(1 <= v <= 99 for v in notas_do_jogador(_player(fama=185)).values())


def test_quem_comeca_no_nordeste_ve_jogadores_da_regiao() -> None:
    dados = carregar()
    for i in range(50):
        nomes = oferta(dados, "geral", f"n{i}", "abc")
        assert sum(x.regiao == "nordeste" and x.tipo == "lenda" for x in nomes) >= 1
        assert sum(x.regiao == "nordeste" and x.tipo == "jogador" for x in nomes) >= 3


def draft_humano(dados, semente: str, posicao: str, clube: str = "flamengo") -> dict[str, int]:
    """One legend at a time, the next unknown: the best free attribute for the position; the two
    re-rolls go to legends whose best free attribute is poor."""
    nomes = oferta(dados, "geral", semente, clube)
    fila, reservas, livres, notas = nomes[:8], nomes[8:], set(regras.ATRIBUTOS), {}
    for lenda in fila:
        melhor = max(livres, key=lambda a: regras.PESOS[posicao][a] * lenda.notas[a])
        if reservas and lenda.notas[melhor] < 70:
            lenda = reservas.pop(0)
            melhor = max(livres, key=lambda a: regras.PESOS[posicao][a] * lenda.notas[a])
        notas[melhor] = lenda.notas[melhor]
        livres.remove(melhor)
    return notas


def test_draft_humano_tem_mediana_perto_de_70() -> None:
    dados = carregar()
    gerais = sorted(
        regras.geral(draft_humano(dados, f"h{i}", regras.POSICOES[i % 5]), regras.POSICOES[i % 5])
        for i in range(1000)
    )
    assert 66 <= gerais[500] <= 74, (gerais[100], gerais[500], gerais[900])
    random.shuffle(gerais)
