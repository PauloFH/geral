"""Birth dates of the idols found by the collection, from Wikidata (day precision only)."""

import re

import httpx

from geral.games import mediawiki
from geral.specials.sources import Passage

DAY = 11  # Wikidata time precision: 11 = day, 10 = month, 9 = year


def _name(title: str) -> str:
    return re.sub(r"\s*\([^)]*\)$", "", title)  # "Kuki (futebolista)" -> "Kuki"


def birthdays(client: httpx.Client, passages: list[Passage]) -> list[dict]:
    idols = {p.qid: p for p in passages if p.kind == "idolo" and p.qid}
    if not idols:
        return []
    found = []
    for qid, entity in mediawiki.entities(client, list(idols), "claims").items():
        for claim in entity.get("claims", {}).get("P569", [])[:1]:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if value.get("precision") != DAY or not value.get("time"):
                continue
            passage = idols[qid]
            found.append(
                {
                    "name": _name(passage.title),
                    "birth_date": value["time"].lstrip("+")[:10],
                    "source_url": passage.url,
                }
            )
    return found
