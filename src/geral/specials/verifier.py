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
# Words that often open a sentence: not taken as names there.
OPENERS = COMMON | set(
    "nos nas dos das ao aos pelo pela pelos pelas com para por sem sob sobre entre contra até "
    "desde durante após antes depois quando enquanto como mas nem ou se então logo assim ainda "
    "já hoje ali lá aqui também nunca sempre mais muito foi era eram foram seria naquele "
    "naquela naqueles naquelas nesse nessa neste nesta ele ela eles elas seu sua seus suas "
    "este esta esse essa aquele aquela isso isto cada todo toda todos todas outro outra "
    "nenhum nenhuma anos dias meses tudo nada alguns algumas muitos muitas poucos".split()
)


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in folded if not unicodedata.combining(c))


def _words(text: str) -> set[str]:
    return {_plain(w) for w in WORD.findall(text)} | {
        _plain(part) for w in WORD.findall(text) for part in w.split("-")
    }


def _names(story: str, lowercase: set[str]) -> list[str]:
    """Capitalized words taken as names. At the start of a sentence a word is a name only when
    it is not a usual opener and is never written in lowercase (in the story or the source)."""
    names = []
    for match in WORD.finditer(story):
        word = match.group(0)
        if not word[0].isupper():
            continue
        plain = _plain(word)
        if SENTENCE_START.search(story[: match.start()]):
            if plain in OPENERS or plain in lowercase:
                continue
        elif plain in COMMON:
            continue
        names.append(word)
    return names


def unsupported(story: str, source: str, allowed: Iterable[str] = ()) -> list[str]:
    """Numbers and proper names of `story` missing from `source`, in order, once each.

    `allowed`: names that may always appear (the team, its newsletter, its fans).
    """
    numbers = set(NUMBER.findall(source))
    known = _words(source) | {w for name in allowed for w in _words(name)}
    missing: list[str] = []
    for token in NUMBER.findall(story):
        if token not in numbers and token not in missing:
            missing.append(token)
    lowercase = {_plain(w) for w in WORD.findall(f"{story} {source}") if w[0].islower()}
    for name in _names(story, lowercase):
        if _plain(name) not in known and name not in missing:
            missing.append(name)
    return missing
