"""The game's data, curated by hand in TOML next to this file (no names in the code).

`versao` fingerprints every file, so a shared career link knows whether it can be replayed.
"""

import hashlib
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from geral.games.carreira.regras import ATRIBUTOS

PASTA = Path(__file__).parent


@dataclass(frozen=True)
class Lenda:
    nome: str
    wikidata: str
    edicoes: tuple[str, ...]
    notas: dict[str, int] = field(hash=False)


@dataclass(frozen=True)
class Liga:
    id: str
    pais: str
    divisao: int
    forca: int  # 1-100
    campeonato: str = "Campeonato"
    copa: str = ""
    continental: str = ""


FASES = ("inicio", "auge", "fim")  # under 21, 21 to 30, 31 and over
DESTINOS = (
    "ficar",
    "europa",
    "maior",
    "menor",
    "emprestimo",
    "arabia",
    "exotico",
    "casa",
    "aposentar",
    "mais_um",
)
COM_CLUBE = ("europa", "maior", "menor", "emprestimo", "arabia", "exotico", "casa")


@dataclass(frozen=True)
class Condicao:
    """When an event or a question may come up; every field left out matches anything."""

    idade_min: int = 0
    idade_max: int = 99
    nota_min: int = 0
    nota_max: int = 99
    forca_min: int = 0  # of the current league
    forca_max: int = 100
    posicoes: tuple[str, ...] = ()
    fases: tuple[str, ...] = ()
    requer: tuple[str, ...] = ()  # event ids that must have happened before
    exclui: tuple[str, ...] = ()  # event ids that must not
    gols_min: int = 0  # this season (only for events after the season's numbers)
    gols_max: int = 999
    jogos_min: int = 0
    jogos_max: int = 99
    titulo: bool | None = None  # won something this season
    no_clube_inicial: bool | None = None
    selecao: bool | None = None  # called up this season
    copa: bool | None = None  # played a World Cup this season
    mundial: bool | None = None  # won it
    paises: tuple[str, ...] = ()  # country of the current league


@dataclass(frozen=True)
class Efeito:
    nota: int = 0  # added to the rating from the next season on
    saida: float = 0.0  # extra chance of leaving at the end of the season
    jogos: float = 1.0  # share of the season played ("antes" events only)
    selecao: bool = False  # called up this season
    titulo: str = ""  # a trophy this event gives


@dataclass(frozen=True)
class Evento:
    id: str
    manchetes: tuple[str, ...]
    peso: float = 1.0
    unico: bool = True
    momento: str = "depois"  # "antes" of the season's numbers, or "depois"
    condicao: Condicao = Condicao()
    efeito: Efeito = Efeito()


@dataclass(frozen=True)
class Opcao:
    texto: str
    destino: str


@dataclass(frozen=True)
class Decisao:
    id: str
    pergunta: str
    opcoes: tuple[Opcao, ...]
    peso: float = 1.0
    condicao: Condicao = Condicao()


@dataclass(frozen=True)
class Clube:
    id: str
    nome: str
    liga: str
    prestigio: int  # 1-100
    time: str | None = None  # slug of the team edition that starts here
    wikidata: str | None = None  # same id as the jogo da velha base, when there is one


@dataclass(frozen=True)
class Dados:
    lendas: tuple[Lenda, ...]
    ligas: dict[str, Liga] = field(hash=False)
    clubes: dict[str, Clube] = field(hash=False)
    versao: str
    eventos: tuple[Evento, ...] = ()
    decisoes: tuple[Decisao, ...] = ()
    finais: tuple[dict, ...] = ()  # read by final.py


def _toml(pasta: Path, nome: str) -> dict:
    path = pasta / nome
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _lenda(entry: dict) -> Lenda:
    nome = str(entry.get("nome", "?"))
    notas = entry.get("notas", {})
    if set(notas) != set(ATRIBUTOS) or not all(
        isinstance(v, int) and 1 <= v <= 99 for v in notas.values()
    ):
        raise ValueError(f"lendas.toml: {nome!r} needs every attribute rated 1-99: {notas}")
    if not entry.get("edicoes") or not entry.get("wikidata"):
        raise ValueError(f"lendas.toml: {nome!r} needs wikidata and edicoes")
    return Lenda(nome, entry["wikidata"], tuple(entry["edicoes"]), dict(notas))


def _mundo(pasta: Path) -> tuple[dict[str, Liga], dict[str, Clube]]:
    raw = _toml(pasta, "mundo.toml")
    ligas = {e["id"]: Liga(**e) for e in raw.get("liga", [])}
    clubes = {}
    for entry in raw.get("clube", []):
        clube = Clube(**entry)
        if clube.liga not in ligas or not 1 <= clube.prestigio <= 100 or clube.id in clubes:
            raise ValueError(f"mundo.toml: {clube.nome!r} has an unknown liga or bad prestigio")
        clubes[clube.id] = clube
    return ligas, clubes


def _condicao(raw: dict, onde: str) -> Condicao:
    raw = {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}
    try:
        condicao = Condicao(**raw)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None
    if any(f not in FASES for f in condicao.fases):
        raise ValueError(f"{onde}: unknown fase in {condicao.fases}")
    return condicao


def _evento(entry: dict) -> Evento:
    onde = f"eventos.toml: {entry.get('id')!r}"
    entry = dict(entry)
    condicao = _condicao(entry.pop("condicao", {}), onde)
    try:
        efeito = Efeito(**entry.pop("efeito", {}))
        evento = Evento(condicao=condicao, efeito=efeito, **entry)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None
    if not evento.manchetes or evento.momento not in ("antes", "depois"):
        raise ValueError(f"{onde}: needs manchetes and momento antes/depois")
    return Evento(**{**evento.__dict__, "manchetes": tuple(evento.manchetes)})


def _decisao(entry: dict) -> Decisao:
    onde = f"escolhas.toml: {entry.get('id')!r}"
    entry = dict(entry)
    condicao = _condicao(entry.pop("condicao", {}), onde)
    opcoes = tuple(Opcao(**o) for o in entry.pop("opcao", []))
    if len(opcoes) < 2 or any(o.destino not in DESTINOS for o in opcoes):
        raise ValueError(f"{onde}: needs 2+ opcoes with destino in {DESTINOS}")
    try:
        return Decisao(condicao=condicao, opcoes=opcoes, **entry)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None


def _versao(pasta: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(pasta.glob("*.toml")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:8]


def carregar(pasta: Path = PASTA) -> Dados:
    """Every data file in `pasta`, validated; parsed once per content version."""
    return _carregar(pasta, _versao(pasta))


@cache
def _carregar(pasta: Path, versao: str) -> Dados:
    lendas = tuple(_lenda(e) for e in _toml(pasta, "lendas.toml").get("lenda", []))
    ligas, clubes = _mundo(pasta)
    eventos = tuple(_evento(e) for e in _toml(pasta, "eventos.toml").get("evento", []))
    decisoes = tuple(_decisao(e) for e in _toml(pasta, "escolhas.toml").get("escolha", []))
    ids = [e.id for e in eventos] + [d.id for d in decisoes]
    if len(ids) != len(set(ids)):
        raise ValueError("eventos.toml/escolhas.toml: repeated id")
    finais = tuple(_toml(pasta, "finais.toml").get("final", []))
    return Dados(lendas, ligas, clubes, versao, eventos, decisoes, finais)
