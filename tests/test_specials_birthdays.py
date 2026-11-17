import httpx
import respx

from geral.games import mediawiki
from geral.specials.birthdays import birthdays
from geral.specials.sources import Passage


def idol(title: str, qid: str | None, kind: str = "idolo") -> Passage:
    return Passage(kind=kind, key=title, title=title, url=f"https://w/{title}", text="t", qid=qid)


def born(time: str, precision: int) -> dict:
    return {
        "claims": {
            "P569": [{"mainsnak": {"datavalue": {"value": {"time": time, "precision": precision}}}}]
        }
    }


@respx.mock
def test_birthday_needs_day_precision(monkeypatch) -> None:
    monkeypatch.setattr(mediawiki.time, "sleep", lambda s: None)
    respx.get(mediawiki.WIKIDATA).mock(
        return_value=httpx.Response(
            200,
            json={
                "entities": {
                    "Q1": born("+1941-03-06T00:00:00Z", 11),
                    "Q2": born("+1950-00-00T00:00:00Z", 9),
                    "Q3": {"claims": {}},
                }
            },
        )
    )
    found = [
        idol("Bita (futebolista)", "Q1"),
        idol("Ano Só", "Q2"),
        idol("Sem Data", "Q3"),
        idol("Sem Item", None),
        idol("Mascote", "Q9", kind="clube"),
    ]

    with httpx.Client() as client:
        result = birthdays(client, found)

    assert result == [
        {"name": "Bita", "birth_date": "1941-03-06", "source_url": "https://w/Bita (futebolista)"}
    ]


@respx.mock
def test_a_bad_wikidata_answer_gives_no_birthdays(monkeypatch) -> None:
    monkeypatch.setattr(mediawiki.time, "sleep", lambda s: None)
    respx.get(mediawiki.WIKIDATA).mock(return_value=httpx.Response(200, json={"error": "x"}))

    with httpx.Client() as client:
        assert birthdays(client, [idol("Bita", "Q1")]) == []


@respx.mock
def test_a_redirected_item_is_skipped(monkeypatch) -> None:
    monkeypatch.setattr(mediawiki.time, "sleep", lambda s: None)
    respx.get(mediawiki.WIKIDATA).mock(
        return_value=httpx.Response(
            200, json={"entities": {"Q99": born("+1941-03-06T00:00:00Z", 11)}}
        )
    )

    with httpx.Client() as client:
        assert birthdays(client, [idol("Bita", "Q1")]) == []
