"""Real players for the draft, from the jogo da velha base: the curated legends are few and all
great, so most of the offer is made of real players of every level.

Their ratings come from a formula, the same for a player every time (seeded by his id): the level
from his fame (number of Wikipedias), the profile from his position, a little noise.
"""

import math
import random
from functools import cache

from geral.games.carreira.dados import Dados, Lenda
from geral.games.carreira.regras import ATRIBUTOS
from geral.games.velha.base import POSITIONS, Player, load

# Points above or below the player's level, by position (order of ATRIBUTOS).
PERFIS = {
    "atacante": (4, 11, -3, 5, -22, 0, 2, -5),
    "meio-campo": (0, 0, 10, 6, -3, -2, -10, 2),
    "lateral": (8, -11, 2, 2, 3, 2, -8, -5),
    "zagueiro": (-6, -19, -5, -14, 11, 6, 10, 3),
}
FAMA_TOPO = 80  # from here a player is as good as the formula allows


def nivel(fama: int) -> float:
    """Fame 1 ≈ 47, 10 ≈ 59, 80+ ≈ 74 (calibrated: a careful draft lands around 71)."""
    return 42 + 32 * min(1.0, math.log(1 + fama) / math.log(1 + FAMA_TOPO))


def notas_do_jogador(p: Player) -> dict[str, int]:
    rng = random.Random(f"jogador:{p.id}")
    perfil = PERFIS.get(p.posicoes[0], PERFIS["meio-campo"])
    base = nivel(p.fama)
    return {
        a: max(15, min(95, round(base + d + max(-8.0, min(8.0, rng.gauss(0, 4))))))
        for a, d in zip(ATRIBUTOS, perfil, strict=True)
    }


@cache
def _todos(versao: str, nordeste: frozenset[str], curadas: frozenset[str]) -> tuple[Lenda, ...]:
    jogadores = []
    for p in sorted(load().players.values(), key=lambda p: p.id):
        if not p.posicoes or "goleiro" in p.posicoes or p.id in curadas:
            continue
        jogadores.append(
            Lenda(
                nome=p.nome,
                wikidata=p.id,
                edicoes=("base",),
                notas=notas_do_jogador(p),
                regiao="nordeste" if p.clubes & nordeste else "",
                tipo="jogador",
                resumo=f"{POSITIONS[p.posicoes[0]]} · {p.anos}"
                if p.anos
                else POSITIONS[p.posicoes[0]],
            )
        )
    return tuple(jogadores)


def jogadores_da_base(dados: Dados) -> tuple[Lenda, ...]:
    """Every outfield player of the base but the curated legends, as draft entries."""
    nordeste = frozenset(
        c.wikidata for c in dados.clubes.values() if c.wikidata and dados.regiao(c) == "nordeste"
    )
    curadas = frozenset(x.wikidata for x in dados.lendas)
    return _todos(dados.versao, nordeste, curadas)
