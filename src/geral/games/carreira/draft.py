"""The draft: nine legends on offer (eight plus one spare for the single re-roll), one stolen
attribute from each of eight of them."""

import random
from collections.abc import Iterable

from pydantic import BaseModel, Field

from geral.games.carreira.dados import Dados, Lenda
from geral.games.carreira.regras import ATRIBUTOS

OFERTA = 9
ROUBOS = len(ATRIBUTOS)


class JogadaInvalida(ValueError):
    """The fan sent something the game never offered; the message is shown to them."""


class Roubo(BaseModel):
    lenda: str = Field(max_length=60)
    atributo: str = Field(max_length=20)


def edicoes(dados: Dados, times: Iterable[str]) -> list[str]:
    """'geral' plus each of `times` with at least one legend of its own, in the given order."""
    proprias = {e for lenda in dados.lendas for e in lenda.edicoes}
    return ["geral", *(t for t in times if t != "geral" and t in proprias)]


MIN_REGIONAIS = 2  # legends of the region of the starting club, when it has any


def oferta(dados: Dados, edicao: str, semente_draft: str, clube: str | None = None) -> list[Lenda]:
    """The draft's nine legends; same seed, same offer. Starting in a Northeast club brings at
    least two idols of the region (the others keep their places)."""
    escolhidas = _oferta(dados, edicao, semente_draft)
    inicio = dados.clubes.get(clube or "")
    regiao = dados.regiao(inicio) if inicio else None
    if regiao != "nordeste":
        return escolhidas
    rng = random.Random(f"draft-regiao:{semente_draft}")
    faltam = MIN_REGIONAIS - sum(x.regiao == regiao for x in escolhidas)
    fora = sorted(
        (x for x in dados.lendas if x.regiao == regiao and x not in escolhidas),
        key=lambda x: x.nome,
    )
    trocaveis = [i for i, x in enumerate(escolhidas) if x.regiao != regiao]
    faltam = min(faltam, len(fora), len(trocaveis))  # a world with few regional idols
    for i, lenda in zip(
        rng.sample(trocaveis, max(0, faltam)), rng.sample(fora, max(0, faltam)), strict=True
    ):
        escolhidas[i] = lenda
    return escolhidas


def _oferta(dados: Dados, edicao: str, semente_draft: str) -> list[Lenda]:
    rng = random.Random(f"draft:{edicao}:{semente_draft}")
    proprias = sorted(
        (lenda for lenda in dados.lendas if edicao in lenda.edicoes), key=lambda x: x.nome
    )
    if edicao == "geral":
        return rng.sample(proprias, OFERTA)
    escolhidas = rng.sample(proprias, min(len(proprias), OFERTA))
    resto = sorted(
        (x for x in dados.lendas if "geral" in x.edicoes and x not in escolhidas),
        key=lambda x: x.nome,
    )
    escolhidas += rng.sample(resto, OFERTA - len(escolhidas))
    rng.shuffle(escolhidas)
    return escolhidas


def montar(ofertadas: list[Lenda], roubos: list[Roubo]) -> dict[str, int]:
    """The player's ratings: each attribute taken from a different legend of the offer."""
    por_nome = {lenda.nome: lenda for lenda in ofertadas}
    if len(roubos) != ROUBOS:
        raise JogadaInvalida(f"são {ROUBOS} roubos, um por atributo")
    if {r.atributo for r in roubos} != set(ATRIBUTOS):
        raise JogadaInvalida("cada atributo é roubado uma vez só")
    if len({r.lenda for r in roubos}) != ROUBOS:
        raise JogadaInvalida("de cada lenda se rouba um atributo só")
    if any(r.lenda not in por_nome for r in roubos):
        raise JogadaInvalida("essa lenda não estava no seu draft")
    return {r.atributo: por_nome[r.lenda].notas[r.atributo] for r in roubos}
