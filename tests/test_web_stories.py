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


def test_fact_date_format_is_checked(client) -> None:
    assert client.post(BASE, json=story(fact_date="ontem"), headers=AUTH).status_code == 422
    assert client.post(BASE, json=story("y", fact_date="1934"), headers=AUTH).status_code == 204


# --- drawing for an edition and "Neste dia" ---------------------------------------------------

DRAW = f"{BASE}/draw"


def test_draw_reserves_an_unused_story(client) -> None:
    client.post(BASE, json=story("a"), headers=AUTH)

    first = client.post(DRAW, json={"label": "Notícias — 23/11/2026"}, headers=AUTH)

    assert first.status_code == 200 and first.json()["title"] == "Bita, o artilheiro"
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 0}
    other = client.post(DRAW, json={"label": "Notícias — 26/11/2026"}, headers=AUTH)
    assert other.status_code == 204


def test_draw_is_idempotent_per_label(client) -> None:
    client.post(BASE, json=story("a"), headers=AUTH)
    client.post(BASE, json=story("b", title="Outra"), headers=AUTH)
    label = {"label": "Notícias — 23/11/2026"}

    first = client.post(DRAW, json=label, headers=AUTH).json()
    again = client.post(DRAW, json=label, headers=AUTH).json()

    assert first["id"] == again["id"]
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 1}


def test_draw_without_reserving_keeps_the_stock(client) -> None:
    client.post(BASE, json=story("a"), headers=AUTH)

    peek = client.post(DRAW, json={"label": "x", "reserve": False}, headers=AUTH)

    assert peek.status_code == 200
    assert client.get(f"{BASE}/count", headers=AUTH).json() == {"unused": 1}


def test_draw_skips_rejected_and_discarded(client, store) -> None:
    client.post(BASE, json=story("a", rejected_reason="x"), headers=AUTH)
    client.post(BASE, json=story("b"), headers=AUTH)
    drawn = client.post(DRAW, json={"label": "L1"}, headers=AUTH).json()
    store.discard_story(drawn["id"])

    assert client.post(DRAW, json={"label": "L1"}, headers=AUTH).status_code == 204


def facts(client, day: str) -> list[dict]:
    return client.get(f"{BASE}/on-this-day", params={"day": day}, headers=AUTH).json()


def test_on_this_day_needs_a_full_date(client) -> None:
    client.post(BASE, json=story("a", fact_date="1934-08-19"), headers=AUTH)
    client.post(BASE, json=story("b", fact_date="1934", title="Ano só"), headers=AUTH)
    client.post(BASE, json=story("c", fact_date="1934-08-30", title="Longe"), headers=AUTH)

    found = facts(client, "2026-08-21")

    assert found == [
        {
            "date": "1934-08-19",
            "title": "Bita, o artilheiro",
            "summary": "O maior artilheiro alvirrubro.",
        }
    ]


def test_on_this_day_window_crosses_the_new_year(client) -> None:
    client.post(BASE, json=story("a", fact_date="1968-01-02"), headers=AUTH)

    assert len(facts(client, "2026-12-30")) == 1
    assert facts(client, "2026-12-26") == []
