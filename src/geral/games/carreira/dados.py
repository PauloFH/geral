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
    regiao: str = ""  # "nordeste": comes more often to whoever starts there


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
    regioes: tuple[str, ...] = ()  # region of the current club (Brazil): nordeste, sudeste…
    classico: bool | None = None  # the current club has a named derby ({classico}, {rival})


@dataclass(frozen=True)
class Efeito:
    nota: int = 0  # added to the rating from the next season on
    saida: float = 0.0  # extra chance of leaving at the end of the season
    jogos: float = 1.0  # share of the season played ("antes" events only)
    selecao: bool = False  # called up this season
    titulo: str = ""  # a trophy this event gives
    atributos: dict[str, int] = field(default_factory=dict, hash=False)  # added to the ratings


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
class OpcaoRotina:
    texto: str
    chance: int = 100  # % of sucesso, before the bonus
    bonus: str = ""  # an attribute that adds (rating - 70) / 2 to the chance
    sucesso: Efeito = Efeito()
    fracasso: Efeito = Efeito()


@dataclass(frozen=True)
class Rotina:
    """A day-to-day situation of the Completa mode: one per season, the result counts next."""

    id: str
    texto: str
    opcoes: tuple[OpcaoRotina, ...]
    peso: float = 1.0
    condicao: Condicao = Condicao()


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
    genero: str = "m"  # "f": a Lazio, da Ponte Preta (the headlines' articles)
    estado: str | None = None  # UF of a Brazilian club: its state cup and region


@dataclass(frozen=True)
class Estado:
    uf: str
    campeonato: str
    regiao: str  # nordeste, sudeste, sul, norte, centro-oeste


@dataclass(frozen=True)
class Classico:
    nome: str
    clubes: tuple[str, str]


@dataclass(frozen=True)
class Dados:
    lendas: tuple[Lenda, ...]
    ligas: dict[str, Liga] = field(hash=False)
    clubes: dict[str, Clube] = field(hash=False)
    versao: str
    eventos: tuple[Evento, ...] = ()
    decisoes: tuple[Decisao, ...] = ()
    finais: tuple[dict, ...] = ()  # read by final.py
    rotinas: tuple[Rotina, ...] = ()
    estados: dict[str, Estado] = field(default_factory=dict, hash=False)
    classicos: tuple[Classico, ...] = ()

    def regiao(self, clube: Clube) -> str | None:
        estado = self.estados.get(clube.estado or "")
        return estado.regiao if estado else None

    def classicos_de(self, clube: Clube) -> list[tuple[str, Clube]]:
        """(name, rival) of every derby this club plays, in file order."""
        return [
            (c.nome, self.clubes[c.clubes[1] if c.clubes[0] == clube.id else c.clubes[0]])
            for c in self.classicos
            if clube.id in c.clubes
        ]

    def classico(self, clube: Clube) -> tuple[str, Clube] | None:
        todos = self.classicos_de(clube)
        return todos[0] if todos else None


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
    regiao = entry.get("regiao", "")
    return Lenda(nome, entry["wikidata"], tuple(entry["edicoes"]), dict(notas), regiao)


def _estados_e_classicos(
    raw: dict, ligas: dict[str, Liga], clubes: dict[str, Clube]
) -> tuple[dict[str, Estado], tuple[Classico, ...]]:
    estados = {e["uf"]: Estado(**e) for e in raw.get("estado", [])}
    if estados:
        for clube in clubes.values():
            if ligas[clube.liga].pais == "Brasil" and clube.estado not in estados:
                raise ValueError(f"mundo.toml: {clube.nome!r} needs an estado with a campeonato")
    classicos = []
    for entry in raw.get("classico", []):
        classico = Classico(entry["nome"], tuple(entry["clubes"]))
        if len(classico.clubes) != 2 or any(c not in clubes for c in classico.clubes):
            raise ValueError(f"mundo.toml: {classico.nome!r} needs two known clubes")
        classicos.append(classico)
    return estados, tuple(classicos)


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
        efeito = _efeito(entry.pop("efeito", {}), onde)
        evento = Evento(condicao=condicao, efeito=efeito, **entry)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None
    if not evento.manchetes or evento.momento not in ("antes", "depois"):
        raise ValueError(f"{onde}: needs manchetes and momento antes/depois")
    return Evento(**{**evento.__dict__, "manchetes": tuple(evento.manchetes)})


def _efeito(raw: dict, onde: str) -> Efeito:
    try:
        efeito = Efeito(**raw)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None
    if set(efeito.atributos) - set(ATRIBUTOS):
        raise ValueError(f"{onde}: unknown atributos {efeito.atributos}")
    return efeito


def _rotina(entry: dict) -> Rotina:
    onde = f"rotina.toml: {entry.get('id')!r}"
    entry = dict(entry)
    condicao = _condicao(entry.pop("condicao", {}), onde)
    opcoes = []
    for raw in entry.pop("opcao", []):
        raw = dict(raw)
        sucesso = _efeito(raw.pop("sucesso", {}), onde)
        fracasso = _efeito(raw.pop("fracasso", {}), onde)
        opcao = OpcaoRotina(sucesso=sucesso, fracasso=fracasso, **raw)
        if not 1 <= opcao.chance <= 100 or opcao.bonus not in ("", *ATRIBUTOS):
            raise ValueError(f"{onde}: chance 1-100 and bonus an attribute")
        opcoes.append(opcao)
    if len(opcoes) < 2:
        raise ValueError(f"{onde}: needs 2+ opcoes")
    try:
        return Rotina(condicao=condicao, opcoes=tuple(opcoes), **entry)
    except TypeError as erro:
        raise ValueError(f"{onde}: {erro}") from None


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
    estados, classicos = _estados_e_classicos(_toml(pasta, "mundo.toml"), ligas, clubes)
    eventos = tuple(_evento(e) for e in _toml(pasta, "eventos.toml").get("evento", []))
    decisoes = tuple(_decisao(e) for e in _toml(pasta, "escolhas.toml").get("escolha", []))
    rotinas = tuple(_rotina(e) for e in _toml(pasta, "rotina.toml").get("rotina", []))
    ids = [e.id for e in eventos] + [d.id for d in decisoes] + [r.id for r in rotinas]
    if len(ids) != len(set(ids)):
        raise ValueError("eventos.toml/escolhas.toml: repeated id")
    finais = tuple(_toml(pasta, "finais.toml").get("final", []))
    return Dados(
        lendas, ligas, clubes, versao, eventos, decisoes, finais, rotinas, estados, classicos
    )
