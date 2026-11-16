"""The stories collection on the page: the nightly job writes, editions will draw from it."""

from webkit import AUTH

BASE = "/api/teams/nautico/stories"


def story(key: str = "https://pt.wikipedia.org/wiki/Bita", **changes) -> dict:
    return {
        "kind": "idolo",
        "title": "Bita, o artilheiro",
        "body": "Bita marcou 221 gols pelo Timbu.",
        "summary": "O maior artilheiro alvirrubro.",
        "fact_date": "",
        "source_key": key,
        "source_url": "https://pt.wikipedia.org/wiki/Bita",
        "source_title": "Bita",
        "rejected_reason": None,
    } | changes


def test_post_story_then_count(client) -> None:
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 0}

    assert client.post(BASE, json=story(), headers=AUTH).status_code == 204

    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 1}


def test_rejected_story_does_not_count(client) -> None:
    rejected = story(rejected_reason="não está na fonte: 1935")

    assert client.post(BASE, json=rejected, headers=AUTH).status_code == 204
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 0}


def test_same_source_twice_is_409(client) -> None:
    client.post(BASE, json=story(), headers=AUTH)

    assert client.post(BASE, json=story(title="Outra"), headers=AUTH).status_code == 409
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 1}


def test_stories_require_token(client) -> None:
    assert client.post(BASE, json=story()).status_code == 401
    assert client.get(f"{BASE}/count").status_code == 401
    assert client.get(f"{BASE}/sources").status_code == 401
    assert client.get("/api/teams/xyz/stories/count", headers=AUTH).status_code == 404


def test_sources_list_every_key_seen(client) -> None:
    client.post(BASE, json=story("a"), headers=AUTH)
    client.post(BASE, json=story("b", rejected_reason="x"), headers=AUTH)
    client.post("/api/teams/abc/stories", json=story("c"), headers=AUTH)

    assert sorted(client.get(f"{BASE}/sources", headers=AUTH).json()) == ["a", "b"]


def test_story_kind_is_checked(client) -> None:
    assert client.post(BASE, json=story(kind="poema"), headers=AUTH).status_code == 422
