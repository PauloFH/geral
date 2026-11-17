"""Every number and proper name of a story must be in its source passage (no model involved).

A story is written by the model from one passage; anything it adds from memory (a year, a score,
a crowd, a player) is exactly what this check refuses. Case and accents are ignored.

- numbers are compared whole ("10.000", "1,56", "48º"); a score ("2 a 1") needs the same pair;
- numbers written out in the story ("seis", "trinta mil", "hexacampeão") are checked too, and a
  digit from 3 to 12 may stand for the word in the source;
- capitalized words are names, except right at the start of a sentence (after . ! ? or a new
  line): an opener like "Embalou" is not a name. A name invented only there is not caught.
"""

import re
import unicodedata
from collections.abc import Iterable

NUMBER = re.compile(r"\d+(?:[.,]\d+)*[ºª°]?")
SCORE = re.compile(r"\b(\d{1,2})\s*(?:a|x|×|–|-)\s*(\d{1,2})\b")
MAX_SCORE = 30  # "de 1932 a 1941" is a period, not a score
WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
SENTENCE_START = re.compile(r"(?:^|[.!?]\s+|\n\s*)$")
# Capitalized words that are not names even mid-sentence.
COMMON = {"o", "a", "os", "as", "um", "uma", "e", "em", "no", "na", "de", "do", "da"}
VALUES = {
    "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8,
    "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
    "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
    "noventa": 90, "cem": 100, "cento": 100, "mil": 1000,
}  # fmt: skip
TITLES = {"bi": 2, "tri": 3, "tetra": 4, "penta": 5, "hexa": 6, "hepta": 7, "octa": 8, "deca": 10}


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in folded if not unicodedata.combining(c))


def _words(text: str) -> set[str]:
    found = WORD.findall(text)
    return {_plain(w) for w in found} | {_plain(p) for w in found for p in w.split("-")}


def _number(token: str) -> str:
    """ "35.000" -> "35000", "48º" -> "48"; decimals keep their comma ("1,56")."""
    token = token.rstrip("ºª°")
    return token.replace(".", "") if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token) else token


def _scores(text: str) -> set[tuple[str, str]]:
    return {(a, b) for a, b in SCORE.findall(text) if int(a) <= MAX_SCORE and int(b) <= MAX_SCORE}


def _title(word: str) -> int | None:
    """ "hexacampeão" -> 6."""
    return next((n for p, n in TITLES.items() if word.startswith(f"{p}campe")), None)


def _written(value: int, words: set[str], numbers: set[str]) -> bool:
    """The source has `value` as a word, as a title count or as digits."""
    return (
        str(value) in numbers
        or any(VALUES.get(w) == value for w in words)
        or any(_title(w) == value for w in words)
    )


def _names(story: str) -> list[str]:
    names = []
    for match in WORD.finditer(story):
        word = match.group(0)
        if not word[0].isupper() or SENTENCE_START.search(story[: match.start()]):
            continue
        if _plain(word) not in COMMON:
            names.append(word)
    return names


def unsupported(story: str, source: str, allowed: Iterable[str] = ()) -> list[str]:
    """Numbers and proper names of `story` missing from `source`, in order, once each.

    `allowed`: names that may always appear (the team, its newsletter, its fans).
    """
    numbers = {_number(n) for n in NUMBER.findall(source)}
    words = _words(source)
    known = words | {w for name in allowed for w in _words(name)}
    source_scores = _scores(source)
    missing: list[str] = []

    def miss(token: str) -> None:
        if token not in missing:
            missing.append(token)

    in_scores = []
    for m in SCORE.finditer(story):
        a, b = m.groups()
        if int(a) > MAX_SCORE or int(b) > MAX_SCORE:
            continue
        in_scores.append(m.span())
        if (a, b) not in source_scores and (b, a) not in source_scores:
            miss(f"{a} a {b}")
    for m in NUMBER.finditer(story):
        if any(start <= m.start() < end for start, end in in_scores):
            continue
        token = _number(m.group(0))
        spelled = token.isdigit() and 3 <= int(token) <= 12 and _written(int(token), words, set())
        if token not in numbers and not spelled:
            miss(m.group(0))
    for m in WORD.finditer(story):
        word = _plain(m.group(0))
        value = VALUES.get(word) or _title(word)
        if value is None:
            continue
        thousands = word == "mil" and any(n.isdigit() and int(n) >= 1000 for n in numbers)
        if word not in words and not thousands and not _written(value, words, numbers):
            miss(m.group(0))
    for name in _names(story):
        if _plain(name) not in known:
            miss(name)
    return missing
