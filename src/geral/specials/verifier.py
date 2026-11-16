"""Every number and proper name of a story must be in its source passage (no model involved).

A story is written by the model from one passage; anything it adds from memory (a year, a score,
a player) is exactly what this check refuses. Case and accents are ignored.
"""

import re
import unicodedata
from collections.abc import Iterable

NUMBER = re.compile(r"\d+")
WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
# A capitalized word right after the start or the end of a sentence is not taken as a name.
SENTENCE_START = re.compile(r"(?:^|[.!?:;]\s+|[\"“«(]\s*)$")
# Capitalized words that are not names even mid-sentence.
COMMON = {"o", "a", "os", "as", "um", "uma", "e", "em", "no", "na", "de", "do", "da"}
# A digit may stand for a number written out in the source (or a title count: "hexacampeão").
SPELLED = {
    "1": ("um", "uma", "primeiro", "primeira"),
    "2": ("dois", "duas", "bi"),
    "3": ("tres", "tri"),
    "4": ("quatro", "tetra"),
    "5": ("cinco", "penta"),
    "6": ("seis", "hexa"),
    "7": ("sete", "hepta"),
    "8": ("oito", "octa"),
    "9": ("nove",),
    "10": ("dez", "deca"),
    "11": ("onze",),
    "12": ("doze",),
}


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in folded if not unicodedata.combining(c))


def _words(text: str) -> set[str]:
    return {_plain(w) for w in WORD.findall(text)} | {
        _plain(part) for w in WORD.findall(text) for part in w.split("-")
    }


def _names(story: str) -> list[str]:
    """Capitalized words mid-sentence (an opener like "Embalou" is not a name)."""
    names = []
    for match in WORD.finditer(story):
        word = match.group(0)
        if not word[0].isupper() or SENTENCE_START.search(story[: match.start()]):
            continue
        if _plain(word) not in COMMON:
            names.append(word)
    return names


def _spelled_out(number: str, words: set[str]) -> bool:
    """The number as a word ("seis") or a title count ("hexacampeão", "bicampeonato")."""
    return any(w == s or w.startswith(f"{s}campe") for s in SPELLED.get(number, ()) for w in words)


def unsupported(story: str, source: str, allowed: Iterable[str] = ()) -> list[str]:
    """Numbers and proper names of `story` missing from `source`, in order, once each.

    `allowed`: names that may always appear (the team, its newsletter, its fans).
    """
    numbers = set(NUMBER.findall(source))
    known = _words(source) | {w for name in allowed for w in _words(name)}
    missing: list[str] = []
    for token in NUMBER.findall(story):
        if token in numbers or token in missing or _spelled_out(token, known):
            continue
        missing.append(token)
    for name in _names(story):
        if _plain(name) not in known and name not in missing:
            missing.append(name)
    return missing
