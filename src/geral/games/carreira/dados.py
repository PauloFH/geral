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
    return Dados(lendas=lendas, ligas=ligas, clubes=clubes, versao=versao)
